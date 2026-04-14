"""
api/staff.py

Staff management endpoints.

GET    /api/v1/staff         — list staff
POST   /api/v1/staff         — create staff
GET    /api/v1/staff/{id}    — get staff
PATCH  /api/v1/staff/{id}    — update staff
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.models.tenant import Tenant
from backend.repositories.staff_repo import (
    create_staff,
    get_staff_by_id,
    list_staff,
    update_staff,
)
from backend.schemas.common import APIResponse
from backend.schemas.staff import StaffCreate, StaffResponse, StaffUpdate

router = APIRouter(prefix="/staff", tags=["Staff"])
logger = logging.getLogger(__name__)


@router.get("", response_model=APIResponse[list[StaffResponse]])
async def get_all_staff(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[StaffResponse]]:
    staff_list = await list_staff(db, tenant.id)
    return APIResponse.ok([StaffResponse.model_validate(s) for s in staff_list])


@router.post(
    "",
    response_model=APIResponse[StaffResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_new_staff(
    data: StaffCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[StaffResponse]:
    staff = await create_staff(db, tenant.id, data)
    return APIResponse.ok(StaffResponse.model_validate(staff))


@router.get("/{staff_id}", response_model=APIResponse[StaffResponse])
async def get_staff_member(
    staff_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[StaffResponse]:
    staff = await get_staff_by_id(db, tenant.id, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    return APIResponse.ok(StaffResponse.model_validate(staff))


@router.delete("/{staff_id}", response_model=APIResponse[dict])
async def deactivate_staff_member(
    staff_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Soft-deactivates a staff member. Existing appointments are preserved."""
    staff = await get_staff_by_id(db, tenant.id, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    staff.is_active = False
    logger.info("staff_deactivated", extra={"tenant_id": str(tenant.id), "staff_id": str(staff_id)})
    return APIResponse.ok({"deactivated": True, "staff_id": str(staff_id)})


@router.patch("/{staff_id}", response_model=APIResponse[StaffResponse])
async def update_staff_member(
    staff_id: uuid.UUID,
    data: StaffUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[StaffResponse]:
    staff = await get_staff_by_id(db, tenant.id, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")

    await update_staff(db, staff, data)
    return APIResponse.ok(StaffResponse.model_validate(staff))
