"""
repositories/service_repo.py

DB access for service management.
All queries scoped to tenant_id.
"""

import uuid
import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.service import Service
from backend.schemas.service import ServiceCreate, ServiceUpdate

logger = logging.getLogger(__name__)


async def list_services(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    include_inactive: bool = False,
) -> List[Service]:
    query = select(Service).where(Service.tenant_id == tenant_id)
    if not include_inactive:
        query = query.where(Service.is_active == True)
    query = query.order_by(Service.category.asc().nulls_last(), Service.name.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_service_by_id(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
) -> Optional[Service]:
    result = await db.execute(
        select(Service).where(
            Service.id == service_id,
            Service.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def find_service_by_name(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    name_fragment: str,
) -> Optional[Service]:
    """
    Case-insensitive partial match on service name.
    Used by booking agent to resolve service_name → service_id from user input.
    Returns the best single match (first result ordered by name).
    """
    from sqlalchemy import func as sa_func
    result = await db.execute(
        select(Service).where(
            Service.tenant_id == tenant_id,
            Service.is_active == True,
            Service.name.ilike(f"%{name_fragment}%"),
        ).order_by(Service.name.asc()).limit(1)
    )
    return result.scalar_one_or_none()


async def create_service(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: ServiceCreate,
) -> Service:
    service = Service(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        category=data.category,
        duration_minutes=data.duration_minutes,
        buffer_minutes=data.buffer_minutes,
        price_paise=data.price_paise,
        staff_ids=data.staff_ids,
    )
    db.add(service)
    logger.info(
        "service_created",
        extra={"tenant_id": str(tenant_id), "service_id": str(service.id)},
    )
    return service


async def update_service(
    db: AsyncSession,
    service: Service,
    data: ServiceUpdate,
) -> Service:
    if data.name is not None:
        service.name = data.name
    if data.description is not None:
        service.description = data.description
    if data.category is not None:
        service.category = data.category
    if data.duration_minutes is not None:
        service.duration_minutes = data.duration_minutes
    if data.buffer_minutes is not None:
        service.buffer_minutes = data.buffer_minutes
    if data.price_rupees is not None:
        service.price_paise = data.price_paise
    if data.staff_ids is not None:
        service.staff_ids = data.staff_ids
    if data.is_active is not None:
        service.is_active = data.is_active
    return service


async def deactivate_service(
    db: AsyncSession,
    service: Service,
) -> Service:
    service.is_active = False
    logger.info(
        "service_deactivated",
        extra={"tenant_id": str(service.tenant_id), "service_id": str(service.id)},
    )
    return service
