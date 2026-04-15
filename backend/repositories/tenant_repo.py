"""
repositories/tenant_repo.py

All DB access for tenant registration and config.
"""

import uuid
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.tenant import Tenant
from backend.schemas.tenant import TenantCreate

logger = logging.getLogger(__name__)


async def get_tenant_by_id(
    db: AsyncSession, tenant_id: uuid.UUID
) -> Optional[Tenant]:
    return await db.get(Tenant, tenant_id)


async def get_tenant_by_subdomain(
    db: AsyncSession, subdomain: str
) -> Optional[Tenant]:
    result = await db.execute(
        select(Tenant).where(Tenant.subdomain == subdomain)
    )
    return result.scalar_one_or_none()


async def get_tenant_by_email(
    db: AsyncSession, email: str
) -> Optional[Tenant]:
    result = await db.execute(
        select(Tenant).where(Tenant.email == email)
    )
    return result.scalar_one_or_none()


async def create_tenant(
    db: AsyncSession,
    data: TenantCreate,
    trial_ends_at,
    hashed_password: str,
) -> Tenant:
    """
    Creates a new tenant with default config.
    Default config seeds sensible business rule defaults from RULES.md.
    """
    default_config = {
        "business_hours": {
            "monday": [{"start": "09:00", "end": "18:00"}],
            "tuesday": [{"start": "09:00", "end": "18:00"}],
            "wednesday": [{"start": "09:00", "end": "18:00"}],
            "thursday": [{"start": "09:00", "end": "18:00"}],
            "friday": [{"start": "09:00", "end": "18:00"}],
            "saturday": [],
            "sunday": [],
        },
        "booking_window_min_hours": 24,
        "booking_window_max_days": 60,
        "allow_same_day": False,
        "slot_buffer_minutes": 15,
        "cancellation_hours": 24,
        "notification_templates": {},  # empty → use platform defaults
    }

    tenant = Tenant(
        id=uuid.uuid4(),
        name=data.name,
        business_type=data.business_type,
        subdomain=data.subdomain,
        email=data.email,
        phone=data.phone,
        timezone=data.timezone,
        config=default_config,
        plan="trial",
        trial_ends_at=trial_ends_at,
        is_active=True,
        onboarding_completed=False,
        hashed_password=hashed_password,
    )
    db.add(tenant)
    logger.info(
        "tenant_created",
        extra={"tenant_id": str(tenant.id), "subdomain": data.subdomain},
    )
    return tenant


async def update_tenant_config(
    db: AsyncSession,
    tenant: Tenant,
    config_patch: dict,
    timezone: Optional[str] = None,
) -> Tenant:
    """Merge-update the JSONB config. Existing keys not in patch are preserved."""
    tenant.config = {**tenant.config, **config_patch}
    if timezone:
        tenant.timezone = timezone
    return tenant


async def mark_onboarding_complete(db: AsyncSession, tenant: Tenant) -> Tenant:
    tenant.onboarding_completed = True
    return tenant
