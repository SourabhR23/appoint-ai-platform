"""
repositories/channel_repo.py

All DB access for channel_configs table.
All queries are scoped to tenant_id.
"""

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.channel_config import ChannelConfig


async def get_channel_by_type(
    db: AsyncSession, tenant_id: uuid.UUID, channel_type: str
) -> Optional[ChannelConfig]:
    result = await db.execute(
        select(ChannelConfig).where(
            ChannelConfig.tenant_id == tenant_id,
            ChannelConfig.channel_type == channel_type,
        )
    )
    return result.scalar_one_or_none()


async def list_channels(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[ChannelConfig]:
    result = await db.execute(
        select(ChannelConfig).where(ChannelConfig.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def upsert_channel(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    channel_type: str,
    credentials: dict,
    is_verified: bool = False,
) -> ChannelConfig:
    """
    Insert or update a channel config for this tenant.
    Uses SELECT + UPDATE pattern (no ON CONFLICT) for clarity.
    """
    existing = await get_channel_by_type(db, tenant_id, channel_type)

    if existing:
        existing.credentials = credentials
        existing.is_active = True
        existing.is_verified = is_verified
        await db.flush()
        return existing

    channel = ChannelConfig(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        channel_type=channel_type,
        credentials=credentials,
        is_active=True,
        is_verified=is_verified,
    )
    db.add(channel)
    await db.flush()
    return channel


async def set_channel_verified(
    db: AsyncSession, tenant_id: uuid.UUID, channel_type: str
) -> None:
    await db.execute(
        update(ChannelConfig)
        .where(
            ChannelConfig.tenant_id == tenant_id,
            ChannelConfig.channel_type == channel_type,
        )
        .values(is_verified=True)
    )


async def deactivate_channel(
    db: AsyncSession, tenant_id: uuid.UUID, channel_type: str
) -> bool:
    existing = await get_channel_by_type(db, tenant_id, channel_type)
    if not existing:
        return False
    existing.is_active = False
    await db.flush()
    return True


async def get_tenant_by_phone_number(
    db: AsyncSession, phone_number: str
) -> Optional[tuple[uuid.UUID, ChannelConfig]]:
    """
    Look up which tenant owns this phone number.
    Used in webhook routing: Twilio sends 'To' number → find tenant.
    Searches both sms and whatsapp channel_configs.
    """
    result = await db.execute(
        select(ChannelConfig).where(
            ChannelConfig.channel_type.in_(["sms", "whatsapp"]),
            ChannelConfig.is_active.is_(True),
        )
    )
    channels = result.scalars().all()

    # Normalize the number for comparison (strip whitespace)
    normalized = phone_number.strip()

    for ch in channels:
        stored = ch.credentials.get("phone_number", "").strip()
        # Match with or without 'whatsapp:' prefix
        if stored == normalized or stored == normalized.replace("whatsapp:", ""):
            return ch.tenant_id, ch

    return None
