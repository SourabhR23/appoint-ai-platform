"""
services/appointment_service.py

Business logic for appointment management.
Routes and agents call services — never repositories directly.

Services handle:
- Booking window validation (BR1)
- Slot conflict checks (via repo)
- Calculating slot_end_datetime (duration + buffer from service)
- Orchestrating DB calls within one transaction
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.appointment import Appointment
from backend.repositories.appointment_repo import (
    check_duplicate_booking,
    check_slot_conflict,
    create_appointment,
    list_appointments,
    _build_idempotency_key,
)
from backend.schemas.appointment import AppointmentCreate, AppointmentFilter

logger = logging.getLogger(__name__)


async def book_appointment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: AppointmentCreate,
    service_duration_minutes: int,
    slot_buffer_minutes: int,
    tenant_config: dict,
) -> Appointment:
    """
    Full appointment creation flow with all business rule validations.

    Raises:
        ValueError: for booking window, duplicate, or slot conflict violations.
    """
    now_utc = datetime.now(timezone.utc)
    requested_utc = data.slot_datetime.astimezone(timezone.utc)

    # ── BR1: Booking window ───────────────────────────────────────────────────
    min_hours: int = tenant_config.get("booking_window_min_hours", 24)
    max_days: int = tenant_config.get("booking_window_max_days", 60)
    allow_same_day: bool = tenant_config.get("allow_same_day", False)

    if not allow_same_day and requested_utc.date() == now_utc.date():
        raise ValueError("Same-day bookings are not allowed for this business.")

    if requested_utc < now_utc + timedelta(hours=min_hours):
        raise ValueError(
            f"Appointments must be booked at least {min_hours} hours in advance."
        )

    if requested_utc > now_utc + timedelta(days=max_days):
        raise ValueError(
            f"Appointments cannot be booked more than {max_days} days in advance."
        )

    # ── Calculate slot end (service duration + buffer) ────────────────────────
    total_minutes = service_duration_minutes + slot_buffer_minutes
    slot_end_utc = requested_utc + timedelta(minutes=total_minutes)

    # ── R7: Idempotency check ─────────────────────────────────────────────────
    idem_key = _build_idempotency_key(
        tenant_id, data.patient_phone, requested_utc, data.staff_id
    )
    existing = await check_duplicate_booking(db, idem_key)
    if existing:
        logger.info(
            "idempotent_booking_returned",
            extra={"appointment_id": str(existing.id), "tenant_id": str(tenant_id)},
        )
        return existing  # idempotent: return the already-existing appointment

    # ── Slot conflict check ────────────────────────────────────────────────────
    has_conflict = await check_slot_conflict(
        db, tenant_id, data.staff_id, requested_utc, slot_end_utc
    )
    if has_conflict:
        raise ValueError(
            "The requested time slot is not available. Please choose another time."
        )

    # ── Create appointment ────────────────────────────────────────────────────
    return await create_appointment(db, tenant_id, data, slot_end_utc)


async def get_appointments_paginated(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    filters: AppointmentFilter,
) -> Tuple[List[Appointment], int]:
    """Returns paginated appointments with total count."""
    return await list_appointments(db, tenant_id, filters)
