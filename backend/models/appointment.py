"""
models/appointment.py

Core booking record.

Rules enforced here:
- Soft deletes only: never DELETE from this table; set deleted_at instead (R2).
- All datetimes in UTC (R3).
- Idempotency key prevents duplicate bookings (R7).
- recurrence_group_id links recurring appointments.
- audit columns: status_changed_at, cancelled_by.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin, TenantScopedMixin


# Appointment status lifecycle:
# pending → confirmed → completed
#                    → no_show
# (any state) → cancelled  (soft-deleted via deleted_at)
APPOINTMENT_STATUS = ["pending", "confirmed", "completed", "no_show", "cancelled"]

# Channel through which the appointment was booked
BOOKING_CHANNEL = ["webchat", "whatsapp", "sms", "manual"]


class Appointment(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Patient details (not a User — patients are external customers)
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    patient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Service & staff (UUIDs, no FK constraint — enforced at service layer)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # Slot timing — stored in UTC (R3)
    slot_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    slot_end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    # Channel through which the booking was made
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="webchat")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Deduplication key (R7): prevents double-booking from retries
    # Format: sha256(tenant_id + patient_phone + slot_datetime + staff_id)
    idempotency_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    # Recurring appointments — all occurrences share the same group ID
    recurrence_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    recurrence_index: Mapped[int | None] = mapped_column(nullable=True)

    # Google Calendar event ID for sync
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Audit
    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Soft delete (R2) — NEVER hard-delete an appointment
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment id={self.id} patient={self.patient_name} "
            f"status={self.status} slot={self.slot_datetime}>"
        )
