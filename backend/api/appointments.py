"""
api/appointments.py

CRUD endpoints for appointment management dashboard.

GET    /api/v1/appointments          — paginated list with filters
GET    /api/v1/appointments/{id}     — single appointment
POST   /api/v1/appointments          — manual booking (receptionist)
PATCH  /api/v1/appointments/{id}     — update status/notes
DELETE /api/v1/appointments/{id}     — soft cancel (R2)
POST   /api/v1/appointments/{id}/reschedule — change slot

All routes: tenant_id comes from JWT (R1), never from URL.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.models.appointment import Appointment
from backend.models.tenant import Tenant
from backend.repositories.appointment_repo import (
    get_appointment_by_id,
    soft_cancel_appointment,
    update_appointment_status,
)
from backend.repositories.staff_repo import get_staff_by_id
from backend.schemas.appointment import (
    AppointmentCreate,
    AppointmentFilter,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentUpdate,
)
from backend.schemas.common import APIResponse, PaginatedResponse
from backend.services.appointment_service import (
    book_appointment,
    get_appointments_paginated,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=PaginatedResponse[AppointmentResponse],
)
async def list_appointments(
    staff_id: Optional[uuid.UUID] = Query(None),
    service_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    patient_phone: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AppointmentResponse]:
    filters = AppointmentFilter(
        staff_id=staff_id,
        service_id=service_id,
        status=status_filter,
        patient_phone=patient_phone,
        page=page,
        limit=limit,
    )

    appointments, total = await get_appointments_paginated(db, tenant.id, filters)
    items = [AppointmentResponse.model_validate(a) for a in appointments]

    return PaginatedResponse(items=items, total=total, page=page, limit=limit)


@router.get(
    "/{appointment_id}",
    response_model=APIResponse[AppointmentResponse],
)
async def get_appointment(
    appointment_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AppointmentResponse]:
    appointment = await get_appointment_by_id(db, tenant.id, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    return APIResponse.ok(AppointmentResponse.model_validate(appointment))


@router.post(
    "",
    response_model=APIResponse[AppointmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_appointment(
    data: AppointmentCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AppointmentResponse]:
    """Manual appointment creation by receptionist."""

    # Verify staff belongs to this tenant
    staff = await get_staff_by_id(db, tenant.id, data.staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")

    # Default service duration (service lookup is Phase 2 detail)
    service_duration = 30  # minutes — TODO: fetch from service record
    buffer = tenant.config.get("slot_buffer_minutes", 15)

    try:
        appointment = await book_appointment(
            db=db,
            tenant_id=tenant.id,
            data=data,
            service_duration_minutes=service_duration,
            slot_buffer_minutes=buffer,
            tenant_config=tenant.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return APIResponse.ok(AppointmentResponse.model_validate(appointment))


@router.patch(
    "/{appointment_id}",
    response_model=APIResponse[AppointmentResponse],
)
async def update_appointment(
    appointment_id: uuid.UUID,
    data: AppointmentUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AppointmentResponse]:
    appointment = await get_appointment_by_id(db, tenant.id, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if data.status:
        await update_appointment_status(db, appointment, data.status)
    if data.notes is not None:
        appointment.notes = data.notes
    if data.cancellation_reason is not None:
        appointment.cancellation_reason = data.cancellation_reason
    if data.staff_id:
        staff = await get_staff_by_id(db, tenant.id, data.staff_id)
        if not staff:
            raise HTTPException(status_code=404, detail="Staff member not found.")
        appointment.staff_id = data.staff_id

    return APIResponse.ok(AppointmentResponse.model_validate(appointment))


@router.delete(
    "/{appointment_id}",
    response_model=APIResponse[dict],
)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Soft-cancel an appointment. Never hard-deletes (R2)."""
    appointment = await get_appointment_by_id(db, tenant.id, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if appointment.status == "cancelled":
        raise HTTPException(status_code=400, detail="Appointment is already cancelled.")

    await soft_cancel_appointment(
        db, appointment, reason=reason, cancelled_by="admin"
    )

    return APIResponse.ok({"cancelled": True, "appointment_id": str(appointment_id)})


@router.post(
    "/{appointment_id}/reschedule",
    response_model=APIResponse[AppointmentResponse],
)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    data: AppointmentReschedule,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AppointmentResponse]:
    from datetime import timedelta, timezone
    from datetime import datetime
    from backend.repositories.appointment_repo import check_slot_conflict

    appointment = await get_appointment_by_id(db, tenant.id, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if appointment.status in ("cancelled", "completed", "no_show"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reschedule a {appointment.status} appointment.",
        )

    new_slot = data.new_slot_datetime.astimezone(timezone.utc)
    duration_minutes = int(
        (appointment.slot_end_datetime - appointment.slot_datetime).total_seconds() / 60
    )
    new_end = new_slot + timedelta(minutes=duration_minutes)

    has_conflict = await check_slot_conflict(
        db, tenant.id, appointment.staff_id, new_slot, new_end,
        exclude_appointment_id=appointment_id,
    )
    if has_conflict:
        raise HTTPException(
            status_code=409, detail="The requested time slot is already taken."
        )

    appointment.slot_datetime = new_slot
    appointment.slot_end_datetime = new_end
    appointment.status = "confirmed"

    return APIResponse.ok(AppointmentResponse.model_validate(appointment))
