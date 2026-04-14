"""
api/services.py

Service (rate card) management endpoints.

GET    /api/v1/services          — list all active services (rate card)
POST   /api/v1/services          — add a new service
GET    /api/v1/services/{id}     — get single service
PATCH  /api/v1/services/{id}     — update service (name, price, staff, etc.)
DELETE /api/v1/services/{id}     — deactivate service (soft delete)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.models.tenant import Tenant
from backend.repositories.service_repo import (
    create_service,
    deactivate_service,
    get_service_by_id,
    list_services,
    update_service,
)
from backend.schemas.common import APIResponse
from backend.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate

router = APIRouter(prefix="/services", tags=["Services"])
logger = logging.getLogger(__name__)


@router.get("", response_model=APIResponse[list[ServiceResponse]])
async def get_all_services(
    include_inactive: bool = Query(False),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[ServiceResponse]]:
    """Returns all services for the tenant, sorted by category then name."""
    services = await list_services(db, tenant.id, include_inactive=include_inactive)
    return APIResponse.ok([ServiceResponse.model_validate(s) for s in services])


@router.post(
    "",
    response_model=APIResponse[ServiceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_new_service(
    data: ServiceCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ServiceResponse]:
    service = await create_service(db, tenant.id, data)
    logger.info(
        "service_created_via_api",
        extra={"tenant_id": str(tenant.id), "name": data.name},
    )
    return APIResponse.ok(ServiceResponse.model_validate(service))


@router.get("/{service_id}", response_model=APIResponse[ServiceResponse])
async def get_service(
    service_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ServiceResponse]:
    service = await get_service_by_id(db, tenant.id, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")
    return APIResponse.ok(ServiceResponse.model_validate(service))


@router.patch("/{service_id}", response_model=APIResponse[ServiceResponse])
async def update_service_details(
    service_id: uuid.UUID,
    data: ServiceUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ServiceResponse]:
    service = await get_service_by_id(db, tenant.id, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")
    await update_service(db, service, data)
    return APIResponse.ok(ServiceResponse.model_validate(service))


@router.delete("/{service_id}", response_model=APIResponse[dict])
async def remove_service(
    service_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Soft-deactivates a service. It will no longer appear in the rate card or be bookable."""
    service = await get_service_by_id(db, tenant.id, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")
    await deactivate_service(db, service)
    return APIResponse.ok({"deactivated": True, "service_id": str(service_id)})
