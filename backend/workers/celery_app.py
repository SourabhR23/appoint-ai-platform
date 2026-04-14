"""
workers/celery_app.py

Celery application factory.
All async task definitions import from this module.

Broker: Redis (CELERY_BROKER_URL)
Backend: Redis (CELERY_RESULT_BACKEND) — stores task results

Beat schedule: reminder tasks run every minute to check for upcoming appointments.
"""

from celery import Celery
from celery.schedules import crontab

from backend.core.config import settings

celery_app = Celery(
    "appointment_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.workers.notification_worker",
        "backend.workers.reminder_worker",
    ],
)

# Serialisation
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry configuration
    task_acks_late=True,             # acknowledge after execution, not before
    task_reject_on_worker_lost=True, # re-queue if worker dies mid-task
    task_max_retries=3,
    task_default_retry_delay=30,     # seconds before first retry
)

# ── Beat (Scheduled Tasks) ────────────────────────────────────────────────────
# Reminder check runs every minute — the task itself filters by timing window.
celery_app.conf.beat_schedule = {
    "check-upcoming-reminders": {
        "task": "backend.workers.reminder_worker.dispatch_upcoming_reminders",
        "schedule": crontab(minute="*"),  # every minute
    },
    "mark-no-show-appointments": {
        "task": "backend.workers.reminder_worker.mark_no_show_appointments",
        "schedule": crontab(minute="*/15"),  # every 15 minutes
    },
}
