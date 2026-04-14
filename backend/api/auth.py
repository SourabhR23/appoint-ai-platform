"""
api/auth.py

Tenant registration + login endpoints.
Auth tokens are issued by Supabase — this API handles the platform-side
tenant record creation that must happen alongside Supabase user creation.

POST /api/v1/auth/register      — create Supabase user + Tenant row
POST /api/v1/auth/login         — proxy to Supabase (or handled client-side)
GET  /api/v1/auth/me            — return current tenant profile
GET  /api/v1/auth/demo-token    — DEV ONLY: issue a signed JWT for demo/testing
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.models.tenant import Tenant
from backend.repositories.tenant_repo import (
    create_tenant,
    get_tenant_by_email,
    get_tenant_by_subdomain,
)
from backend.schemas.common import APIResponse
from backend.schemas.tenant import TenantCreate, TenantResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=APIResponse[TenantResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[TenantResponse]:
    """
    Step 1: Business registration.

    1. Validate subdomain + email uniqueness.
    2. Create the Supabase Auth user (email/password handled client-side via Supabase SDK).
    3. Create the Tenant row in our DB.
    4. Return tenant profile.

    Note: Supabase SDK is used client-side for password management.
    This endpoint only handles the platform-side tenant record.
    """
    # Check uniqueness
    existing_subdomain = await get_tenant_by_subdomain(db, data.subdomain)
    if existing_subdomain:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subdomain '{data.subdomain}' is already taken.",
        )

    existing_email = await get_tenant_by_email(db, data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    trial_ends_at = datetime.now(timezone.utc) + timedelta(days=settings.TRIAL_DAYS)
    tenant = await create_tenant(db, data, trial_ends_at)

    logger.info(
        "tenant_registered",
        extra={"tenant_id": str(tenant.id), "subdomain": data.subdomain},
    )

    return APIResponse.ok(TenantResponse.model_validate(tenant))


@router.get(
    "/me",
    response_model=APIResponse[TenantResponse],
)
async def get_current_tenant_profile(
    tenant: Tenant = Depends(get_current_tenant),
) -> APIResponse[TenantResponse]:
    """Returns the authenticated tenant's profile."""
    return APIResponse.ok(TenantResponse.model_validate(tenant))


@router.get(
    "/demo-token",
    response_model=APIResponse[dict],
)
async def get_demo_token(
    subdomain: str,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """
    DEV ONLY — issues a signed JWT for a seeded demo tenant.
    Blocked in production. Used by the demo frontend to skip Supabase setup.

    Usage: GET /api/v1/auth/demo-token?subdomain=medcare
    """
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo tokens are not available in production.",
        )

    tenant = await get_tenant_by_subdomain(db, subdomain)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{subdomain}' not found.",
        )

    from jose import jwt as jose_jwt

    payload = {
        "sub": str(uuid.uuid4()),        # fake user_id — demo only
        "tenant_id": str(tenant.id),
        "email": tenant.email,
        "role": "admin",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }

    token = jose_jwt.encode(
        payload,
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )

    logger.info("demo_token_issued", extra={"tenant_id": str(tenant.id), "subdomain": subdomain})

    return APIResponse.ok({
        "access_token": token,
        "tenant": TenantResponse.model_validate(tenant).model_dump(mode="json"),
    })
