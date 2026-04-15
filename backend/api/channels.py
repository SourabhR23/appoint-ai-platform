"""
api/channels.py

Channel configuration endpoints — per-tenant SMS, WhatsApp, Email setup.
Credentials are write-only: stored in channel_configs, never returned.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_tenant
from backend.models.tenant import Tenant
from backend.repositories import channel_repo
from backend.schemas.channel import (
    ChannelConfigCreate,
    ChannelConfigResponse,
    ChannelStatusResponse,
)
from backend.schemas.common import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Channels"])


@router.get("", response_model=APIResponse[ChannelStatusResponse])
async def get_channel_status(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Return configured channel status for this tenant.
    Credentials are never included in the response.
    """
    channels = await channel_repo.list_channels(db, tenant.id)
    ch_map = {ch.channel_type: ch for ch in channels}

    def _resp(ch_type: str):
        ch = ch_map.get(ch_type)
        if ch is None:
            return None
        return ChannelConfigResponse.model_validate(ch)

    return APIResponse.ok(
        ChannelStatusResponse(
            sms=_resp("sms"),
            whatsapp=_resp("whatsapp"),
            email=_resp("email"),
        )
    )


@router.post("", response_model=APIResponse[ChannelConfigResponse])
async def configure_channel(
    payload: ChannelConfigCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Save channel credentials for the tenant.
    Validates credentials by running a test connection before saving.
    """
    ch_type = payload.channel_type
    creds = payload.credentials

    # Validate credentials before saving
    verified = False
    if ch_type == "email":
        try:
            from backend.services.smtp_service import test_smtp_connection
            test_smtp_connection(creds)
            verified = True
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email credentials invalid: {exc}",
            )
    elif ch_type in ("sms", "whatsapp"):
        try:
            from twilio.rest import Client
            client = Client(creds.get("account_sid"), creds.get("auth_token"))
            # Lightweight validation — fetch account
            client.api.accounts(creds.get("account_sid")).fetch()
            verified = True
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Twilio credentials invalid: {exc}",
            )

    channel = await channel_repo.upsert_channel(
        db, tenant.id, ch_type, creds, is_verified=verified
    )
    await db.commit()
    await db.refresh(channel)

    logger.info(
        "channel_configured",
        extra={
            "tenant_id": str(tenant.id),
            "channel_type": ch_type,
            "verified": verified,
        },
    )

    return APIResponse.ok(ChannelConfigResponse.model_validate(channel))


@router.delete("/{channel_type}", response_model=APIResponse[dict])
async def remove_channel(
    channel_type: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a channel (does not delete row — keeps audit history)."""
    if channel_type not in ("sms", "whatsapp", "email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid channel type",
        )

    removed = await channel_repo.deactivate_channel(db, tenant.id, channel_type)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active {channel_type} channel found",
        )

    await db.commit()
    return APIResponse.ok({"removed": True, "channel_type": channel_type})
