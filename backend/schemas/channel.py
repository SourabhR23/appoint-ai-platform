"""
schemas/channel.py

Request / response shapes for channel config endpoints.
Credentials are write-only — never returned in GET responses (security).
"""

import uuid
from typing import Optional

from pydantic import BaseModel, field_validator


# ── Request schemas ───────────────────────────────────────────────────────────

class SMSCredentials(BaseModel):
    account_sid: str
    auth_token: str
    phone_number: str  # E.164 format: +91XXXXXXXXXX


class WhatsAppCredentials(BaseModel):
    account_sid: str
    auth_token: str
    phone_number: str  # WhatsApp-enabled number in E.164


class EmailCredentials(BaseModel):
    smtp_user: str        # Gmail address
    smtp_password: str    # 16-char App Password
    from_name: str = "AppointAI"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587


class ChannelConfigCreate(BaseModel):
    channel_type: str   # sms | whatsapp | email
    credentials: dict   # raw dict — validated per type in service layer

    @field_validator("channel_type")
    @classmethod
    def valid_channel_type(cls, v: str) -> str:
        allowed = {"sms", "whatsapp", "email"}
        if v not in allowed:
            raise ValueError(f"channel_type must be one of: {allowed}")
        return v


# ── Response schemas ──────────────────────────────────────────────────────────

class ChannelConfigResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    channel_type: str
    is_active: bool
    is_verified: bool
    # credentials intentionally omitted — never returned to client

    class Config:
        from_attributes = True


class ChannelStatusResponse(BaseModel):
    """Summary view — which channels are configured."""
    sms: Optional[ChannelConfigResponse] = None
    whatsapp: Optional[ChannelConfigResponse] = None
    email: Optional[ChannelConfigResponse] = None
