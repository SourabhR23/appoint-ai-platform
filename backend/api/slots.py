"""
api/slots.py

Slot availability endpoint.

GET /api/v1/slots?date=YYYY-MM-DD&service_id=UUID&staff_id=UUID

Returns all time slots for the given date and service.
Each slot is marked available or taken.

Slot generation algorithm:
  1. Get service (duration, buffer, allowed staff_ids)
  2. For each relevant staff member:
     a. Fetch their working_hours for the weekday
     b. Fetch existing confirmed/pending appointments for that staff on that date
     c. Walk the working window in steps of (duration + buffer) minutes
     d. Mark a slot taken if any existing appointment overlaps
  3. Return flat list ordered by time

The tenant config can override slot_interval_minutes (default = duration + buffer).
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.models.appointment import Appointment
from backend.models.staff import Staff
from backend.models.tenant import Tenant
from backend.repositories.service_repo import get_service_by_id
from backend.repositories.staff_repo import get_staff_by_id, list_staff
from backend.schemas.common import APIResponse

router = APIRouter(prefix="/slots", tags=["Slots"])
logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _parse_time(date_obj: date, time_str: str) -> datetime:
    """Parse 'HH:MM' into a timezone-aware datetime on the given date (UTC naive, local interpretation)."""
    h, m = map(int, time_str.split(":"))
    return datetime(date_obj.year, date_obj.month, date_obj.day, h, m, tzinfo=timezone.utc)


def _slots_for_staff_window(
    date_obj: date,
    windows: list,             # [{"start": "09:00", "end": "13:00"}, ...]
    duration_minutes: int,
    interval_minutes: int,     # duration + buffer
    booked: list,              # list of (slot_start_dt, slot_end_dt) tuples
) -> list:
    slots = []
    slot_duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=interval_minutes)

    for window in windows:
        current = _parse_time(date_obj, window["start"])
        window_end = _parse_time(date_obj, window["end"])

        while current + slot_duration <= window_end:
            slot_end = current + slot_duration
            # A slot is taken if it overlaps any existing appointment
            taken = any(
                current < b_end and slot_end > b_start
                for b_start, b_end in booked
            )
            slots.append({
                "start": current.strftime("%H:%M"),
                "end": slot_end.strftime("%H:%M"),
                "available": not taken,
            })
            current += step

    return slots


@router.get("", response_model=APIResponse[dict])
async def get_available_slots(
    date_str: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    service_id: uuid.UUID = Query(...),
    staff_id: Optional[uuid.UUID] = Query(None, description="If omitted, returns slots for all qualified staff"),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """
    Returns available time slots for a given date, service, and optional staff member.
    Groups results by staff member so the frontend can show per-staff availability.
    """

    # Validate date
    try:
        date_obj = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be in YYYY-MM-DD format.")

    if date_obj < date.today():
        raise HTTPException(status_code=400, detail="Cannot query slots for past dates.")

    # Fetch service
    service = await get_service_by_id(db, tenant.id, service_id)
    if not service or not service.is_active:
        raise HTTPException(status_code=404, detail="Service not found.")

    duration_minutes = service.duration_minutes
    buffer_minutes = service.buffer_minutes
    interval_minutes = duration_minutes + buffer_minutes

    # Determine which staff members to query
    if staff_id:
        staff_member = await get_staff_by_id(db, tenant.id, staff_id)
        if not staff_member:
            raise HTTPException(status_code=404, detail="Staff member not found.")
        staff_list = [staff_member]
    else:
        all_staff = await list_staff(db, tenant.id)
        # Filter to staff who can perform this service (if service.staff_ids is set)
        if service.staff_ids:
            staff_list = [s for s in all_staff if str(s.id) in service.staff_ids]
        else:
            staff_list = all_staff  # any staff can perform it

    if not staff_list:
        return APIResponse.ok({
            "date": date_str,
            "service": {"id": str(service.id), "name": service.name, "duration_minutes": duration_minutes},
            "staff_slots": [],
        })

    weekday = WEEKDAY_NAMES[date_obj.weekday()]

    # Fetch all appointments for this tenant on this date (for all relevant staff)
    day_start = datetime(date_obj.year, date_obj.month, date_obj.day, 0, 0, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    relevant_staff_ids = [s.id for s in staff_list]
    appt_result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant.id,
                Appointment.staff_id.in_(relevant_staff_ids),
                Appointment.slot_datetime >= day_start,
                Appointment.slot_datetime < day_end,
                Appointment.status.in_(["confirmed", "pending"]),
            )
        )
    )
    all_appts = list(appt_result.scalars().all())

    # Build per-staff result
    staff_slots = []
    for staff_member in staff_list:
        windows = staff_member.working_hours.get(weekday, [])
        if not windows:
            # Staff not working this day
            continue

        # Booked intervals for this staff member
        booked = [
            (a.slot_datetime, a.slot_end_datetime)
            for a in all_appts
            if a.staff_id == staff_member.id
        ]

        slots = _slots_for_staff_window(date_obj, windows, duration_minutes, interval_minutes, booked)

        staff_slots.append({
            "staff_id": str(staff_member.id),
            "staff_name": staff_member.full_name,
            "specialization": staff_member.specialization,
            "slots": slots,
        })

    return APIResponse.ok({
        "date": date_str,
        "service": {
            "id": str(service.id),
            "name": service.name,
            "duration_minutes": duration_minutes,
            "price_paise": service.price_paise,
        },
        "staff_slots": staff_slots,
    })
