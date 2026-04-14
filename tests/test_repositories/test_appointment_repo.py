"""
tests/test_repositories/test_appointment_repo.py

Integration tests for appointment repository.
Runs against real test DB (not mocked) to catch SQL bugs.
Verifies tenant isolation (TR2).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.appointment import Appointment
from backend.models.staff import Staff
from backend.models.service import Service
from backend.repositories.appointment_repo import (
    check_slot_conflict,
    create_appointment,
    get_appointment_by_id,
    list_appointments,
    soft_cancel_appointment,
    _build_idempotency_key,
)
from backend.schemas.appointment import AppointmentCreate, AppointmentFilter


def _future_slot(hours_ahead: int = 25) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours_ahead)


@pytest_asyncio.fixture
async def staff_a(db: AsyncSession, tenant_a):
    staff = Staff(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        full_name="Dr. Smith",
        working_hours={},
    )
    db.add(staff)
    await db.flush()
    return staff


async def _make_appointment(
    db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID, slot: datetime
) -> Appointment:
    slot_end = slot + timedelta(hours=1)
    data = AppointmentCreate(
        patient_name="Test Patient",
        patient_phone="+911234567890",
        service_id=uuid.uuid4(),
        staff_id=staff_id,
        slot_datetime=slot,
        channel="webchat",
    )
    return await create_appointment(db, tenant_id, data, slot_end)


@pytest.mark.asyncio
async def test_create_and_fetch_appointment(db: AsyncSession, tenant_a, staff_a):
    slot = _future_slot()
    appt = await _make_appointment(db, tenant_a.id, staff_a.id, slot)
    await db.flush()

    fetched = await get_appointment_by_id(db, tenant_a.id, appt.id)
    assert fetched is not None
    assert fetched.id == appt.id
    assert fetched.tenant_id == tenant_a.id


@pytest.mark.asyncio
async def test_tenant_isolation(db: AsyncSession, tenant_a, tenant_b, staff_a):
    """Tenant B must not be able to see Tenant A's appointments (TR2)."""
    slot = _future_slot()
    appt = await _make_appointment(db, tenant_a.id, staff_a.id, slot)
    await db.flush()

    # Tenant B queries for the same appointment ID — should return None
    fetched_by_b = await get_appointment_by_id(db, tenant_b.id, appt.id)
    assert fetched_by_b is None


@pytest.mark.asyncio
async def test_slot_conflict_detection(db: AsyncSession, tenant_a, staff_a):
    """Overlapping slot should be detected as a conflict."""
    base_slot = _future_slot(hours_ahead=48)
    await _make_appointment(db, tenant_a.id, staff_a.id, base_slot)
    await db.flush()

    # Request overlapping slot (30 min into existing 1-hour slot)
    overlap_slot = base_slot + timedelta(minutes=30)
    overlap_end = overlap_slot + timedelta(hours=1)

    has_conflict = await check_slot_conflict(
        db, tenant_a.id, staff_a.id, overlap_slot, overlap_end
    )
    assert has_conflict is True


@pytest.mark.asyncio
async def test_no_conflict_for_different_staff(db: AsyncSession, tenant_a, staff_a, db_2=None):
    """Same slot for different staff should not conflict."""
    other_staff = Staff(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        full_name="Dr. Jones",
        working_hours={},
    )
    db.add(other_staff)
    await db.flush()

    base_slot = _future_slot(hours_ahead=72)
    await _make_appointment(db, tenant_a.id, staff_a.id, base_slot)
    await db.flush()

    slot_end = base_slot + timedelta(hours=1)
    has_conflict = await check_slot_conflict(
        db, tenant_a.id, other_staff.id, base_slot, slot_end
    )
    assert has_conflict is False


@pytest.mark.asyncio
async def test_soft_cancel_does_not_hard_delete(db: AsyncSession, tenant_a, staff_a):
    """Cancelled appointments must remain in DB with deleted_at set (R2)."""
    slot = _future_slot()
    appt = await _make_appointment(db, tenant_a.id, staff_a.id, slot)
    await db.flush()

    await soft_cancel_appointment(db, appt, reason="Patient request", cancelled_by="patient")
    await db.flush()

    # Direct query bypassing deleted_at filter — record must still exist
    from sqlalchemy import select
    result = await db.execute(
        select(Appointment).where(Appointment.id == appt.id)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.deleted_at is not None
    assert row.status == "cancelled"


@pytest.mark.asyncio
async def test_list_excludes_cancelled(db: AsyncSession, tenant_a, staff_a):
    """Listing appointments should not include soft-deleted records."""
    slot = _future_slot()
    appt = await _make_appointment(db, tenant_a.id, staff_a.id, slot)
    await db.flush()

    await soft_cancel_appointment(db, appt, reason="test", cancelled_by="test")
    await db.flush()

    appts, total = await list_appointments(
        db, tenant_a.id, AppointmentFilter(page=1, limit=100)
    )
    ids = [a.id for a in appts]
    assert appt.id not in ids
