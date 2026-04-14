"""
agents/booking_agent.py

Handles the full appointment booking flow:
1. Extract patient details and preferred slot from conversation.
2. Check slot availability + buffer (R4 slot buffer from tenant config).
3. Check idempotency — return existing if already booked (R7).
4. Create appointment in DB.
5. Set state for notification_agent to send confirmation.

cost_weight = 1.5 (most expensive agent — does DB read + write + LLM call).
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base import BaseAgent
from backend.core.config import settings
from backend.repositories.appointment_repo import (
    check_duplicate_booking,
    check_slot_conflict,
    create_appointment,
)
from backend.repositories.staff_repo import get_staff_by_id
from backend.schemas.appointment import AppointmentCreate

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an appointment booking assistant.
Extract booking details from the conversation.

Return ONLY a JSON object with these fields (use null for missing fields):
{
  "patient_name": "string or null",
  "patient_phone": "string or null (digits only, include country code)",
  "patient_email": "string or null",
  "service_name": "string or null",
  "requested_datetime": "ISO 8601 string or null (e.g. 2026-04-10T14:30:00+05:30)",
  "missing_fields": ["list of fields still needed from user"]
}

Today's date context: {today}
Tenant timezone: {timezone}
"""


class BookingAgent(BaseAgent):
    name = "booking_agent"
    display_name = "Appointment Booking Agent"
    cost_weight = 1.5

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0,
            max_tokens=500,
        )

    async def run(self, state: dict) -> dict:
        """
        Full booking flow. Requires a DB session in state["db"].
        db is injected by the graph executor before running.
        """
        db: AsyncSession | None = state.get("db")
        tenant_id_str: str = state.get("tenant_id", "")
        tenant_config: dict = state.get("tenant_config", {})

        if not db or not tenant_id_str:
            return self._error_state(
                state, "Booking system unavailable. Please try again.", None
            )

        tenant_id = uuid.UUID(tenant_id_str)
        timezone_str = tenant_config.get("timezone", "Asia/Kolkata")
        buffer_minutes = tenant_config.get("slot_buffer_minutes", 15)

        try:
            # ── Step 1: Extract booking details from conversation ──────────────
            extract_prompt = EXTRACTION_PROMPT.format(
                today=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                timezone=timezone_str,
            )
            messages = [
                SystemMessage(content=extract_prompt),
                HumanMessage(content=state.get("user_input", "")),
            ]
            ai_response = await self._llm.ainvoke(messages)
            extracted = json.loads(ai_response.content.strip())

            # ── Step 2: Check for missing required fields ──────────────────────
            missing = extracted.get("missing_fields", [])
            if missing:
                return {
                    **state,
                    "response": (
                        f"I need a few more details to complete your booking. "
                        f"Could you please provide: {', '.join(missing)}?"
                    ),
                    "next_node": "__end__",
                }

            # ── Step 3: Parse datetime ─────────────────────────────────────────
            requested_dt_str = extracted.get("requested_datetime")
            if not requested_dt_str:
                return {
                    **state,
                    "response": "What date and time works best for your appointment?",
                    "next_node": "__end__",
                }

            requested_dt = datetime.fromisoformat(requested_dt_str).astimezone(timezone.utc)

            # Use staff_id from state (set by slot_checker or directly)
            staff_id_str = state.get("staff_id")
            service_id_str = state.get("service_id")
            service_duration = int(state.get("service_duration_minutes", 30))

            if not staff_id_str or not service_id_str:
                return {
                    **state,
                    "response": "Please select a service and staff member to proceed.",
                    "next_node": "__end__",
                }

            staff_id = uuid.UUID(staff_id_str)
            service_id = uuid.UUID(service_id_str)
            slot_end = requested_dt + timedelta(minutes=service_duration + buffer_minutes)

            # ── Step 4: Check slot availability ───────────────────────────────
            has_conflict = await check_slot_conflict(
                db, tenant_id, staff_id, requested_dt, slot_end
            )
            if has_conflict:
                return {
                    **state,
                    "response": (
                        "That time slot is not available. "
                        "Would you like me to suggest the next available slots?"
                    ),
                    "next_node": "slot_checker",
                }

            # ── Step 5: Build create schema ───────────────────────────────────
            create_data = AppointmentCreate(
                patient_name=extracted["patient_name"],
                patient_phone=extracted["patient_phone"],
                patient_email=extracted.get("patient_email"),
                service_id=service_id,
                staff_id=staff_id,
                slot_datetime=requested_dt,
                channel=state.get("channel", "webchat"),
                notes=None,
            )

            # ── Step 6: Idempotency check ──────────────────────────────────────
            from backend.repositories.appointment_repo import _build_idempotency_key
            idem_key = _build_idempotency_key(
                tenant_id, create_data.patient_phone, requested_dt, staff_id
            )
            existing = await check_duplicate_booking(db, idem_key)
            if existing:
                logger.info(
                    "duplicate_booking_detected",
                    extra={"appointment_id": str(existing.id), "tenant_id": tenant_id_str},
                )
                return {
                    **state,
                    "appointment_id": str(existing.id),
                    "confirmed_slot": existing.slot_datetime.isoformat(),
                    "response": (
                        f"You already have an appointment on "
                        f"{existing.slot_datetime.strftime('%d %b %Y at %I:%M %p UTC')}. "
                        "Would you like to reschedule or cancel it?"
                    ),
                    "next_node": "notification_agent",
                }

            # ── Step 7: Create appointment ────────────────────────────────────
            appointment = await create_appointment(db, tenant_id, create_data, slot_end)
            await db.flush()

            logger.info(
                "booking_completed",
                extra={
                    "tenant_id": tenant_id_str,
                    "appointment_id": str(appointment.id),
                    "channel": state.get("channel"),
                },
            )

            return {
                **state,
                "appointment_id": str(appointment.id),
                "confirmed_slot": appointment.slot_datetime.isoformat(),
                "patient_name": create_data.patient_name,
                "patient_phone": create_data.patient_phone,
                "response": (
                    f"Your appointment has been confirmed for "
                    f"{appointment.slot_datetime.strftime('%d %b %Y at %I:%M %p UTC')}. "
                    "You'll receive a confirmation shortly."
                ),
                "next_node": "notification_agent",
            }

        except Exception as exc:
            return self._error_state(
                state,
                "I was unable to complete the booking. Please try again or contact us directly.",
                exc,
            )
