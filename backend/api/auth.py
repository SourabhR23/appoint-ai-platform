"""
api/auth.py

Tenant registration + login endpoints.

POST /api/v1/auth/register      — create tenant with hashed password → JWT
POST /api/v1/auth/login         — email + password → JWT
POST /api/v1/auth/admin/login   — platform admin login → admin JWT
GET  /api/v1/auth/me            — return current tenant profile
GET  /api/v1/auth/demo-token    — DEV ONLY: issue signed JWT for demo/testing
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
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
from backend.schemas.tenant import (
    AdminLoginRequest,
    LoginRequest,
    TenantCreate,
    TenantResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

def _hash_password(plain: str) -> str:
    # bcrypt truncates at 72 bytes — enforce explicitly for deterministic behavior.
    pwd_bytes = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _issue_tenant_token(tenant: Tenant) -> str:
    from jose import jwt as jose_jwt
    payload = {
        "sub": str(uuid.uuid4()),
        "tenant_id": str(tenant.id),
        "email": tenant.email,
        "role": "admin",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jose_jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


def _issue_admin_token(email: str) -> str:
    from jose import jwt as jose_jwt
    payload = {
        "sub": "platform_admin",
        "email": email,
        "role": "super_admin",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jose_jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


@router.post("/register", response_model=APIResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register_tenant(data: TenantCreate, db: AsyncSession = Depends(get_db)):
    if await get_tenant_by_subdomain(db, data.subdomain):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Subdomain '{data.subdomain}' is already taken.")
    if await get_tenant_by_email(db, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    hashed = _hash_password(data.password)
    trial_ends_at = datetime.now(timezone.utc) + timedelta(days=settings.TRIAL_DAYS)
    tenant = await create_tenant(db, data, trial_ends_at, hashed)
    await db.commit()
    await db.refresh(tenant)

    token = _issue_tenant_token(tenant)
    logger.info("tenant_registered", extra={"tenant_id": str(tenant.id), "subdomain": data.subdomain})

    return APIResponse.ok(TokenResponse(
        access_token=token,
        tenant=TenantResponse.model_validate(tenant),
    ))


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    tenant = await get_tenant_by_email(db, data.email)
    if not tenant or not tenant.hashed_password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    if not _verify_password(data.password, tenant.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    if not tenant.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is inactive.")

    token = _issue_tenant_token(tenant)
    logger.info("tenant_login", extra={"tenant_id": str(tenant.id)})

    return APIResponse.ok(TokenResponse(
        access_token=token,
        tenant=TenantResponse.model_validate(tenant),
    ))


@router.post("/admin/login", response_model=APIResponse[dict])
async def admin_login(data: AdminLoginRequest):
    if data.email != settings.ADMIN_EMAIL:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin credentials.")
    if not settings.ADMIN_PASSWORD_HASH:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Admin login not configured.")
    if not _verify_password(data.password, settings.ADMIN_PASSWORD_HASH):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin credentials.")

    token = _issue_admin_token(data.email)
    logger.info("admin_login", extra={"email": data.email})
    return APIResponse.ok({"access_token": token, "role": "super_admin", "email": data.email})


@router.get("/me", response_model=APIResponse[TenantResponse])
async def get_current_tenant_profile(tenant: Tenant = Depends(get_current_tenant)):
    return APIResponse.ok(TenantResponse.model_validate(tenant))


@router.get("/demo-token", response_model=APIResponse[dict])
async def get_demo_token(subdomain: str, db: AsyncSession = Depends(get_db)):
    """DEV ONLY — issues a signed JWT for a seeded demo tenant."""
    if settings.is_production:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Demo tokens are not available in production.")

    tenant = await get_tenant_by_subdomain(db, subdomain)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Tenant '{subdomain}' not found.")

    token = _issue_tenant_token(tenant)
    logger.info("demo_token_issued", extra={"tenant_id": str(tenant.id), "subdomain": subdomain})

    return APIResponse.ok({
        "access_token": token,
        "tenant": TenantResponse.model_validate(tenant).model_dump(mode="json"),
    })
