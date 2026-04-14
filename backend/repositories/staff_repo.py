"""
repositories/staff_repo.py

DB access for staff management.
All queries scoped to tenant_id.
"""

import uuid
import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.staff import Staff
from backend.schemas.staff import StaffCreate, StaffUpdate

logger = logging.getLogger(__name__)


async def get_staff_by_id(
    db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID
) -> Optional[Staff]:
    result = await db.execute(
        select(Staff).where(
            Staff.id == staff_id,
            Staff.tenant_id == tenant_id,
            Staff.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def list_staff(
    db: AsyncSession, tenant_id: uuid.UUID
) -> List[Staff]:
    result = await db.execute(
        select(Staff)
        .where(Staff.tenant_id == tenant_id, Staff.is_active == True)
        .order_by(Staff.priority_order.asc())
    )
    return list(result.scalars().all())


async def create_staff(
    db: AsyncSession, tenant_id: uuid.UUID, data: StaffCreate
) -> Staff:
    staff = Staff(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        specialization=data.specialization,
        priority_order=data.priority_order,
        working_hours=data.working_hours,
    )
    db.add(staff)
    logger.info(
        "staff_created",
        extra={"tenant_id": str(tenant_id), "staff_id": str(staff.id)},
    )
    return staff


async def update_staff(
    db: AsyncSession, staff: Staff, data: StaffUpdate
) -> Staff:
    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(staff, field, value)
    return staff
