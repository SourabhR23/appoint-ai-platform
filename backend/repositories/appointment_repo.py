"""
repositories/appointment_repo.py

All SQL logic for appointments lives here.
Services call these functions — routes NEVER touch the DB directly.

Rules enforced:
- Every query scoped to tenant_id (R1)
- All filters exclude deleted_at IS NOT NULL (R2)
- Idempotency check before insert (R7)
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.appointment import Appointment
from backend.schemas.appointment import AppointmentCreate, AppointmentFilter

logger = logging.getLogger(__name__)


def _build_idempotency_key(
    tenant_id: uuid.UUID,
    patient_phone: str,
    slot_datetime: datetime,
    staff_id: uuid.UUID,
) -> str:
    """
    Deterministic deduplication key (R7).
    Same inputs always produce the same key → prevents duplicate bookings.
    """
    raw = f"{tenant_id}:{patient_phone}:{slot_datetime.isoformat()}:{staff_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_appointment_by_id(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    appointment_id: uuid.UUID,
) -> Optional[Appointment]:
    """Fetch a single appointment scoped to the tenant. Returns None if not found."""
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == tenant_id,
            Appointment.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_appointments(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    filters: AppointmentFilter,
) -> tuple[List[Appointment], int]:
    """
    Returns a paginated list of appointments and the total count.
    Applies optional filters for staff, service, status, date range, and phone.
    """
    base_query = select(Appointment).where(
        Appointment.tenant_id == tenant_id,
        Appointment.deleted_at.is_(None),
    )

    if filters.staff_id:
        base_query = base_query.where(Appointment.staff_id == filters.staff_id)
    if filters.service_id:
        base_query = base_query.where(Appointment.service_id == filters.service_id)
    if filters.status:
        base_query = base_query.where(Appointment.status == filters.status)
    if filters.date_from:
        base_query = base_query.where(Appointment.slot_datetime >= filters.date_from)
    if filters.date_to:
        base_query = base_query.where(Appointment.slot_datetime <= filters.date_to)
    if filters.patient_phone:
        base_query = base_query.where(
            Appointment.patient_phone == filters.patient_phone
        )

    # Count query
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # Paginated data query
    offset = (filters.page - 1) * filters.limit
    data_result = await db.execute(
        base_query.order_by(Appointment.slot_datetime.asc())
        .offset(offset)
        .limit(filters.limit)
    )
    appointments = list(data_result.scalars().all())

    return appointments, total


async def check_duplicate_booking(
    db: AsyncSession,
    idempotency_key: str,
) -> Optional[Appointment]:
    """Check if an appointment with this idempotency key already exists (R7)."""
    result = await db.execute(
        select(Appointment).where(
            Appointment.idempotency_key == idempotency_key,
            Appointment.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def check_slot_conflict(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    staff_id: uuid.UUID,
    slot_start: datetime,
    slot_end: datetime,
    exclude_appointment_id: Optional[uuid.UUID] = None,
) -> bool:
    """
    Returns True if there is a conflicting appointment for this staff + time window.
    Excludes the given appointment_id (used when rescheduling).
    """
    query = select(Appointment).where(
        Appointment.tenant_id == tenant_id,
        Appointment.staff_id == staff_id,
        Appointment.status.in_(["pending", "confirmed"]),
        Appointment.deleted_at.is_(None),
        # Overlap check: existing slot overlaps with requested window
        Appointment.slot_datetime < slot_end,
        Appointment.slot_end_datetime > slot_start,
    )

    if exclude_appointment_id:
        query = query.where(Appointment.id != exclude_appointment_id)

    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def create_appointment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: AppointmentCreate,
    slot_end_datetime: datetime,
) -> Appointment:
    """
    Creates a new appointment after the service layer has:
    1. Checked for slot conflicts.
    2. Verified the idempotency key is unique.

    Returns the newly created appointment (not yet committed — caller commits).
    """
    idempotency_key = _build_idempotency_key(
        tenant_id, data.patient_phone, data.slot_datetime, data.staff_id
    )

    appointment = Appointment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        patient_name=data.patient_name,
        patient_phone=data.patient_phone,
        patient_email=data.patient_email,
        service_id=data.service_id,
        staff_id=data.staff_id,
        slot_datetime=data.slot_datetime.astimezone(timezone.utc),
        slot_end_datetime=slot_end_datetime.astimezone(timezone.utc),
        status="confirmed",
        channel=data.channel,
        notes=data.notes,
        idempotency_key=idempotency_key,
    )

    db.add(appointment)
    logger.info(
        "appointment_created",
        extra={
            "tenant_id": str(tenant_id),
            "appointment_id": str(appointment.id),
            "channel": data.channel,
            "staff_id": str(data.staff_id),
        },
    )
    return appointment


async def soft_cancel_appointment(
    db: AsyncSession,
    appointment: Appointment,
    reason: Optional[str],
    cancelled_by: str = "patient",
) -> Appointment:
    """
    Soft-delete: sets deleted_at, status='cancelled', reason (R2).
    NEVER hard-deletes an appointment.
    """
    now = datetime.now(timezone.utc)
    appointment.status = "cancelled"
    appointment.deleted_at = now
    appointment.status_changed_at = now
    appointment.cancellation_reason = reason
    appointment.cancelled_by = cancelled_by

    logger.info(
        "appointment_cancelled",
        extra={
            "tenant_id": str(appointment.tenant_id),
            "appointment_id": str(appointment.id),
            "cancelled_by": cancelled_by,
        },
    )
    return appointment


async def update_appointment_status(
    db: AsyncSession,
    appointment: Appointment,
    new_status: str,
) -> Appointment:
    """Update only the status of an appointment (e.g. confirmed → no_show)."""
    appointment.status = new_status
    appointment.status_changed_at = datetime.now(timezone.utc)
    return appointment
