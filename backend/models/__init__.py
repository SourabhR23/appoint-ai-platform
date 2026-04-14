"""
models/__init__.py

Import all models here so Alembic can discover them during autogenerate.
If a model is not imported here, Alembic will not generate its migration.
"""

from backend.models.tenant import Tenant
from backend.models.user import User
from backend.models.staff import Staff
from backend.models.service import Service
from backend.models.appointment import Appointment
from backend.models.graph import Graph, GraphVersion
from backend.models.notification_log import NotificationLog
from backend.models.billing_event import BillingEvent

__all__ = [
    "Tenant",
    "User",
    "Staff",
    "Service",
    "Appointment",
    "Graph",
    "GraphVersion",
    "NotificationLog",
    "BillingEvent",
]
