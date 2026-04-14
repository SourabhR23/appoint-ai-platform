"""
workers/notification_worker.py

Celery tasks for sending notifications.
Called by NotificationAgent (which only enqueues — never blocks on delivery).

Retry policy (R8):
- 3 retries with exponential backoff: 30s, 60s, 120s
- After 3 failures: mark notification_log as "failed", alert tenant
"""

import logging
import uuid
from datetime import datetime, timezone

from celery import shared_task

from backend.services.notification_templates import render_template
from backend.services.twilio_service import send_sms, send_whatsapp
from backend.services.sendgrid_service import send_email

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="backend.workers.notification_worker.send_notification_task",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
)
def send_notification_task(
    self,
    tenant_id: str,
    appointment_id: str,
    channel: str,
    recipient: str,
    template_key: str,
    context: dict,
    tenant_templates: dict | None = None,
    service_name: str = "your service",
) -> dict:
    """
    Send a single notification via the specified channel.
    Automatically retried up to 3 times on failure (R8).
    Logs result to notification_logs table via a sync DB call.

    Returns dict with status and provider_message_id.
    """
    # Render the message body from template
    full_context = {**context, "service": service_name}
    body = render_template(template_key, full_context, tenant_templates)

    subject_map = {
        "booking_confirmation": "Appointment Confirmed",
        "reschedule_confirmation": "Appointment Rescheduled",
        "reminder_24h": "Appointment Reminder — Tomorrow",
        "reminder_1h": "Appointment Reminder — 1 Hour",
        "cancellation": "Appointment Cancelled",
        "no_show": "Missed Appointment",
    }
    subject = subject_map.get(template_key, "Appointment Update")

    provider_message_id = None

    try:
        if channel == "sms":
            provider_message_id = send_sms(to=recipient, body=body)
        elif channel == "whatsapp":
            provider_message_id = send_whatsapp(to=recipient, body=body)
        elif channel == "email":
            provider_message_id = send_email(
                to_email=recipient, subject=subject, body_text=body
            )
        else:
            raise ValueError(f"Unsupported notification channel: {channel}")

        logger.info(
            "notification_sent",
            extra={
                "tenant_id": tenant_id,
                "appointment_id": appointment_id,
                "channel": channel,
                "template_key": template_key,
                "provider_message_id": provider_message_id,
            },
        )

        _log_notification(
            tenant_id=tenant_id,
            appointment_id=appointment_id,
            channel=channel,
            recipient=recipient,
            template_key=template_key,
            status="sent",
            provider_message_id=provider_message_id,
            attempts=self.request.retries + 1,
        )

        return {"status": "sent", "provider_message_id": provider_message_id}

    except Exception as exc:
        attempts = self.request.retries + 1

        logger.error(
            "notification_send_failed",
            extra={
                "tenant_id": tenant_id,
                "appointment_id": appointment_id,
                "channel": channel,
                "attempt": attempts,
                "error": str(exc),
            },
        )

        if attempts >= self.max_retries:
            # All retries exhausted — mark as failed
            _log_notification(
                tenant_id=tenant_id,
                appointment_id=appointment_id,
                channel=channel,
                recipient=recipient,
                template_key=template_key,
                status="failed",
                error_message=str(exc),
                attempts=attempts,
            )

        raise


def _log_notification(
    tenant_id: str,
    appointment_id: str,
    channel: str,
    recipient: str,
    template_key: str,
    status: str,
    error_message: str | None = None,
    provider_message_id: str | None = None,
    attempts: int = 1,
) -> None:
    """
    Write a NotificationLog row via a synchronous SQLAlchemy session.
    Workers are sync Celery tasks — they use a sync session, not async.

    Note: this uses psycopg2 (sync) driver, not asyncpg.
    """
    import sqlalchemy as sa
    from sqlalchemy.orm import Session

    # Sync DB URL (replace asyncpg with psycopg2 for Celery workers)
    from backend.core.config import settings
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = sa.create_engine(sync_url, pool_pre_ping=True)

    from backend.models.notification_log import NotificationLog

    with Session(engine) as session:
        log = NotificationLog(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            appointment_id=uuid.UUID(appointment_id) if appointment_id else None,
            channel=channel,
            recipient=recipient,
            template_key=template_key,
            status=status,
            error_message=error_message,
            provider_message_id=provider_message_id,
            attempts=attempts,
        )
        session.add(log)
        session.commit()
