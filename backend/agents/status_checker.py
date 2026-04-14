"""
agents/status_checker.py

Looks up a patient's appointment by phone number or appointment ID.
Returns appointment details in a human-readable format.
cost_weight = 0.5
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.models.appointment import Appointment

logger = logging.getLogger(__name__)


class StatusCheckerAgent(BaseAgent):
    name = "status_checker"
    display_name = "Status Checker Agent"
    cost_weight = 0.5

    async def run(self, state: dict) -> dict:
        db = state.get("db")
        tenant_id_str = state.get("tenant_id", "")

        if not db or not tenant_id_str:
            return self._error_state(state, "Status lookup unavailable.", None)

        tenant_id = uuid.UUID(tenant_id_str)
        appointment_id_str = state.get("appointment_id")
        patient_phone = state.get("patient_phone") or state.get("sender_identifier")

        try:
            appointment = None

            # ── Try by appointment ID first ────────────────────────────────────
            if appointment_id_str:
                result = await db.execute(
                    select(Appointment).where(
                        Appointment.id == uuid.UUID(appointment_id_str),
                        Appointment.tenant_id == tenant_id,
                        Appointment.deleted_at.is_(None),
                    )
                )
                appointment = result.scalar_one_or_none()

            # ── Fallback: most recent by phone number ──────────────────────────
            if not appointment and patient_phone:
                result = await db.execute(
                    select(Appointment)
                    .where(
                        Appointment.tenant_id == tenant_id,
                        Appointment.patient_phone == patient_phone,
                        Appointment.deleted_at.is_(None),
                        Appointment.status.in_(["pending", "confirmed"]),
                    )
                    .order_by(Appointment.slot_datetime.asc())
                    .limit(1)
                )
                appointment = result.scalar_one_or_none()

            if not appointment:
                return {
                    **state,
                    "response": (
                        "I couldn't find any upcoming appointments for you. "
                        "Would you like to book a new appointment?"
                    ),
                    "next_node": "__end__",
                }

            slot_str = appointment.slot_datetime.strftime("%d %b %Y at %I:%M %p UTC")

            logger.info(
                "status_checked",
                extra={
                    "tenant_id": tenant_id_str,
                    "appointment_id": str(appointment.id),
                },
            )

            return {
                **state,
                "appointment_id": str(appointment.id),
                "confirmed_slot": appointment.slot_datetime.isoformat(),
                "patient_name": appointment.patient_name,
                "response": (
                    f"I found your appointment:\n"
                    f"  Date: {slot_str}\n"
                    f"  Status: {appointment.status.title()}\n"
                    f"  Ref: {str(appointment.id)[:8].upper()}\n\n"
                    "Would you like to reschedule or cancel it?"
                ),
                "next_node": "__end__",
            }

        except Exception as exc:
            return self._error_state(
                state,
                "I was unable to look up your appointment. Please try again.",
                exc,
            )
