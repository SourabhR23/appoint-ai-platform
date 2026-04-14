"""
agents/notification_agent.py

Dispatches appointment notifications via the configured channel.
Actual sends are done asynchronously via Celery (R8) — this agent
only enqueues the Celery task and returns immediately.

Never blocks the main booking flow waiting for delivery.
cost_weight = 1.0
"""

import logging
import uuid

from backend.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class NotificationAgent(BaseAgent):
    name = "notification_agent"
    display_name = "Notification Agent"
    cost_weight = 1.0

    async def run(self, state: dict) -> dict:
        tenant_id_str = state.get("tenant_id", "")
        appointment_id_str = state.get("appointment_id")
        channel = state.get("channel", "webchat")
        patient_phone = state.get("patient_phone")
        patient_email = state.get("patient_email")
        confirmed_slot = state.get("confirmed_slot")
        intent = state.get("intent", "book")

        if not appointment_id_str:
            # Nothing to notify about — this shouldn't happen in a valid graph
            logger.warning(
                "notification_agent_no_appointment",
                extra={"tenant_id": tenant_id_str, "session_id": state.get("session_id")},
            )
            return {**state, "notification_status": "skipped", "next_node": "__end__"}

        try:
            # Map intent to template key
            template_map = {
                "book": "booking_confirmation",
                "reschedule": "reschedule_confirmation",
                "cancel": "cancellation",
            }
            template_key = template_map.get(intent, "booking_confirmation")

            # Determine recipient and channel for notification
            # WhatsApp/SMS use phone; email uses email
            if channel in ("whatsapp", "sms") and patient_phone:
                recipient = patient_phone
            elif patient_email:
                recipient = patient_email
                channel = "email"
            elif patient_phone:
                recipient = patient_phone
                channel = "sms"
            else:
                logger.warning(
                    "notification_agent_no_recipient",
                    extra={"appointment_id": appointment_id_str},
                )
                return {**state, "notification_status": "skipped", "next_node": "__end__"}

            # ── Enqueue Celery task (R8: async, non-blocking) ──────────────────
            # Import here to avoid circular deps with celery app
            from backend.workers.notification_worker import send_notification_task

            send_notification_task.delay(
                tenant_id=tenant_id_str,
                appointment_id=appointment_id_str,
                channel=channel,
                recipient=recipient,
                template_key=template_key,
                context={
                    "name": state.get("patient_name", "Customer"),
                    "slot": confirmed_slot,
                },
            )

            logger.info(
                "notification_queued",
                extra={
                    "tenant_id": tenant_id_str,
                    "appointment_id": appointment_id_str,
                    "channel": channel,
                    "template_key": template_key,
                },
            )

            return {
                **state,
                "notification_status": "queued",
                "next_node": "__end__",
            }

        except Exception as exc:
            # Notification failure must NOT fail the booking (R8)
            logger.error(
                "notification_queue_error",
                extra={
                    "tenant_id": tenant_id_str,
                    "appointment_id": appointment_id_str,
                    "error": str(exc),
                },
            )
            # Still mark as completed — booking succeeded even if notification failed
            return {
                **state,
                "notification_status": "failed",
                "next_node": "__end__",
            }
