"""
workers/reminder_worker.py

Celery Beat scheduled tasks:
1. dispatch_upcoming_reminders — runs every minute, sends 24h and 1h reminders.
2. mark_no_show_appointments — runs every 15 minutes, marks no-shows (BR3).

These use synchronous SQLAlchemy (psycopg2) since Celery workers are sync.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from celery import shared_task
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.appointment import Appointment
from backend.workers.notification_worker import send_notification_task

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = sa.create_engine(sync_url, pool_pre_ping=True)
    return Session(engine)


@shared_task(name="backend.workers.reminder_worker.dispatch_upcoming_reminders")
def dispatch_upcoming_reminders() -> dict:
    """
    Finds appointments that need a 24h or 1h reminder and dispatches notifications.

    24h window: slot is between 23h and 25h from now (run every minute → covers the gap).
    1h window: slot is between 55min and 65min from now.
    """
    now = datetime.now(timezone.utc)

    windows = [
        ("reminder_24h", now + timedelta(hours=23), now + timedelta(hours=25)),
        ("reminder_1h", now + timedelta(minutes=55), now + timedelta(minutes=65)),
    ]

    dispatched = 0

    with _get_sync_session() as session:
        for template_key, window_start, window_end in windows:
            appointments = session.execute(
                sa.select(Appointment).where(
                    Appointment.status == "confirmed",
                    Appointment.deleted_at.is_(None),
                    Appointment.slot_datetime >= window_start,
                    Appointment.slot_datetime <= window_end,
                )
            ).scalars().all()

            for appt in appointments:
                # Determine channel — default to sms if no email
                channel = "sms"
                recipient = appt.patient_phone

                if appt.patient_email:
                    channel = "email"
                    recipient = appt.patient_email

                send_notification_task.delay(
                    tenant_id=str(appt.tenant_id),
                    appointment_id=str(appt.id),
                    channel=channel,
                    recipient=recipient,
                    template_key=template_key,
                    context={"name": appt.patient_name, "slot": appt.slot_datetime.isoformat()},
                )
                dispatched += 1

    logger.info("reminders_dispatched", extra={"count": dispatched, "run_at": now.isoformat()})
    return {"dispatched": dispatched}


@shared_task(name="backend.workers.reminder_worker.mark_no_show_appointments")
def mark_no_show_appointments() -> dict:
    """
    Auto-marks appointments as no_show if 15 minutes have passed since slot_datetime
    and the appointment is still in 'confirmed' status (BR3).
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=15)
    marked = 0

    with _get_sync_session() as session:
        appointments = session.execute(
            sa.select(Appointment).where(
                Appointment.status == "confirmed",
                Appointment.deleted_at.is_(None),
                Appointment.slot_datetime <= cutoff,
            )
        ).scalars().all()

        for appt in appointments:
            appt.status = "no_show"
            appt.status_changed_at = now
            marked += 1

            logger.info(
                "appointment_marked_no_show",
                extra={
                    "tenant_id": str(appt.tenant_id),
                    "appointment_id": str(appt.id),
                },
            )

        session.commit()

    logger.info("no_shows_marked", extra={"count": marked, "run_at": now.isoformat()})
    return {"marked": marked}
