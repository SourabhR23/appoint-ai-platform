"""
agents/cancellation_agent.py

Handles appointment cancellation requests.
Enforces soft-delete only — never hard deletes (R2).
Checks cancellation window policy from tenant config (BR2).
cost_weight = 1.0
"""

import logging
import uuid
from datetime import datetime, timezone

from backend.agents.base import BaseAgent
from backend.repositories.appointment_repo import (
    get_appointment_by_id,
    soft_cancel_appointment,
)

logger = logging.getLogger(__name__)


class CancellationAgent(BaseAgent):
    name = "cancellation_agent"
    display_name = "Cancellation Agent"
    cost_weight = 1.0

    async def run(self, state: dict) -> dict:
        db = state.get("db")
        tenant_id_str = state.get("tenant_id", "")
        appointment_id_str = state.get("appointment_id")
        tenant_config = state.get("tenant_config", {})

        if not db or not tenant_id_str:
            return self._error_state(state, "Cancellation system unavailable.", None)

        if not appointment_id_str:
            return {
                **state,
                "response": (
                    "I couldn't find your appointment. "
                    "Could you provide your phone number so I can look it up?"
                ),
                "next_node": "status_checker",
            }

        try:
            tenant_id = uuid.UUID(tenant_id_str)
            appointment_id = uuid.UUID(appointment_id_str)

            appointment = await get_appointment_by_id(db, tenant_id, appointment_id)

            if not appointment:
                return {
                    **state,
                    "response": "I couldn't find that appointment. Please check the details and try again.",
                    "next_node": "__end__",
                }

            if appointment.status == "cancelled":
                return {
                    **state,
                    "response": "This appointment has already been cancelled.",
                    "next_node": "__end__",
                }

            # ── Cancellation window policy (BR2) ──────────────────────────────
            cancellation_hours = tenant_config.get("cancellation_hours", 24)
            now_utc = datetime.now(timezone.utc)
            hours_until_appt = (
                appointment.slot_datetime - now_utc
            ).total_seconds() / 3600

            late_cancellation = hours_until_appt < cancellation_hours

            # Soft cancel — set deleted_at, update status (R2)
            await soft_cancel_appointment(
                db,
                appointment,
                reason=state.get("cancellation_reason"),
                cancelled_by="patient",
            )
            await db.flush()

            late_notice = ""
            if late_cancellation:
                late_notice = (
                    f" Note: This is a late cancellation (less than {cancellation_hours}h notice). "
                    "The business may apply their cancellation policy."
                )

            logger.info(
                "cancellation_completed",
                extra={
                    "tenant_id": tenant_id_str,
                    "appointment_id": appointment_id_str,
                    "late_cancellation": late_cancellation,
                },
            )

            return {
                **state,
                "response": (
                    f"Your appointment has been cancelled successfully.{late_notice} "
                    "You'll receive a cancellation confirmation shortly."
                ),
                "next_node": "notification_agent",
            }

        except Exception as exc:
            return self._error_state(
                state,
                "I was unable to cancel the appointment. Please contact us directly.",
                exc,
            )
