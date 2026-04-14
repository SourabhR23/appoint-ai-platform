"""
api/tenants.py

Tenant configuration and onboarding endpoints.

GET  /api/v1/tenants/me/config   — get current config
PUT  /api/v1/tenants/me/config   — update config
POST /api/v1/tenants/me/onboarding/complete — mark onboarding done
GET  /api/v1/tenants/agents      — list available agents (for graph builder)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.graph.registry import AGENT_METADATA
from backend.models.tenant import Tenant
from backend.repositories.tenant_repo import mark_onboarding_complete, update_tenant_config
from backend.schemas.common import APIResponse
from backend.schemas.tenant import TenantConfigUpdate, TenantResponse

router = APIRouter(prefix="/tenants", tags=["Tenants"])
logger = logging.getLogger(__name__)


@router.get(
    "/me/config",
    response_model=APIResponse[dict],
)
async def get_tenant_config(
    tenant: Tenant = Depends(get_current_tenant),
) -> APIResponse[dict]:
    """Returns the tenant's JSONB config."""
    return APIResponse.ok(tenant.config)


@router.put(
    "/me/config",
    response_model=APIResponse[TenantResponse],
)
async def update_config(
    data: TenantConfigUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TenantResponse]:
    """Merge-update tenant config. Unspecified keys are preserved."""
    await update_tenant_config(db, tenant, data.config, data.timezone)
    return APIResponse.ok(TenantResponse.model_validate(tenant))


@router.post(
    "/me/onboarding/complete",
    response_model=APIResponse[dict],
)
async def complete_onboarding(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Mark the tenant's onboarding wizard as complete."""
    if tenant.onboarding_completed:
        return APIResponse.ok({"message": "Onboarding already completed."})

    await mark_onboarding_complete(db, tenant)
    logger.info("onboarding_completed", extra={"tenant_id": str(tenant.id)})

    return APIResponse.ok({"message": "Onboarding complete. Graph builder is now unlocked."})


@router.get(
    "/agents",
    response_model=APIResponse[list],
)
async def list_available_agents(
    tenant: Tenant = Depends(get_current_tenant),
) -> APIResponse[list]:
    """
    Returns the list of agent types available for the tenant's plan.
    Used by the frontend graph builder sidebar.
    MVP: all agents available (billing restrictions in Phase 2).
    """
    return APIResponse.ok(AGENT_METADATA)
