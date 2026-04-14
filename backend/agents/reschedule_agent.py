"""
agents/reschedule_agent.py

Handles rescheduling an existing appointment to a new time slot.
1. Loads the existing appointment.
2. Validates the new slot (conflict check, booking window).
3. Updates slot_datetime and slot_end_datetime.
4. Routes to notification_agent to send updated confirmation.

cost_weight = 1.5
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from backend.agents.base import BaseAgent
from backend.repositories.appointment_repo import (
    check_slot_conflict,
    get_appointment_by_id,
)

logger = logging.getLogger(__name__)


class RescheduleAgent(BaseAgent):
    name = "reschedule_agent"
    display_name = "Reschedule Agent"
    cost_weight = 1.5

    async def run(self, state: dict) -> dict:
        db = state.get("db")
        tenant_id_str = state.get("tenant_id", "")
        appointment_id_str = state.get("appointment_id")
        new_slot_str = state.get("requested_datetime")
        tenant_config = state.get("tenant_config", {})

        if not db or not tenant_id_str:
            return self._error_state(state, "Reschedule system unavailable.", None)

        if not appointment_id_str:
            return {
                **state,
                "response": (
                    "Please provide your appointment reference or phone number "
                    "so I can find your booking."
                ),
                "next_node": "status_checker",
            }

        if not new_slot_str:
            return {
                **state,
                "response": "What new date and time would you prefer for your appointment?",
                "next_node": "__end__",
            }

        try:
            tenant_id = uuid.UUID(tenant_id_str)
            appointment_id = uuid.UUID(appointment_id_str)
            new_slot = datetime.fromisoformat(new_slot_str).astimezone(timezone.utc)

            appointment = await get_appointment_by_id(db, tenant_id, appointment_id)

            if not appointment:
                return {
                    **state,
                    "response": "I couldn't find that appointment. Please verify the details.",
                    "next_node": "__end__",
                }

            if appointment.status in ("cancelled", "completed", "no_show"):
                return {
                    **state,
                    "response": (
                        f"This appointment cannot be rescheduled because it is {appointment.status}."
                    ),
                    "next_node": "__end__",
                }

            # ── Booking window validation (BR1) ────────────────────────────────
            min_hours = tenant_config.get("booking_window_min_hours", 24)
            max_days = tenant_config.get("booking_window_max_days", 60)
            now_utc = datetime.now(timezone.utc)

            if new_slot < now_utc + timedelta(hours=min_hours):
                return {
                    **state,
                    "response": (
                        f"Appointments must be booked at least {min_hours} hours in advance. "
                        "Please choose a later time."
                    ),
                    "next_node": "__end__",
                }

            if new_slot > now_utc + timedelta(days=max_days):
                return {
                    **state,
                    "response": (
                        f"Appointments can only be scheduled up to {max_days} days in advance."
                    ),
                    "next_node": "__end__",
                }

            # ── Slot conflict check (excluding current appointment) ────────────
            buffer_minutes = tenant_config.get("slot_buffer_minutes", 15)
            duration = int(
                (appointment.slot_end_datetime - appointment.slot_datetime).total_seconds() / 60
            )
            new_slot_end = new_slot + timedelta(minutes=duration + buffer_minutes)

            has_conflict = await check_slot_conflict(
                db,
                tenant_id,
                appointment.staff_id,
                new_slot,
                new_slot_end,
                exclude_appointment_id=appointment_id,
            )

            if has_conflict:
                return {
                    **state,
                    "response": (
                        "That time slot is already taken. "
                        "Would you like to see the next available slots?"
                    ),
                    "next_node": "slot_checker",
                }

            # ── Update the appointment ─────────────────────────────────────────
            old_slot = appointment.slot_datetime
            appointment.slot_datetime = new_slot
            appointment.slot_end_datetime = new_slot_end
            appointment.status = "confirmed"
            appointment.status_changed_at = datetime.now(timezone.utc)
            await db.flush()

            logger.info(
                "appointment_rescheduled",
                extra={
                    "tenant_id": tenant_id_str,
                    "appointment_id": appointment_id_str,
                    "old_slot": old_slot.isoformat(),
                    "new_slot": new_slot.isoformat(),
                },
            )

            return {
                **state,
                "confirmed_slot": new_slot.isoformat(),
                "response": (
                    f"Your appointment has been rescheduled to "
                    f"{new_slot.strftime('%d %b %Y at %I:%M %p UTC')}. "
                    "A confirmation will be sent shortly."
                ),
                "next_node": "notification_agent",
            }

        except Exception as exc:
            return self._error_state(
                state,
                "I was unable to reschedule your appointment. Please try again.",
                exc,
            )
