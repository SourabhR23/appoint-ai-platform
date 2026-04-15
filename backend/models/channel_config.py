"""
models/channel_config.py

Stores per-tenant notification channel credentials.
Each row = one channel type configured by a tenant.

Credential fields stored as plain JSONB for demo.
In production, encrypt with Fernet before writing to DB.
"""

import uuid

from sqlalchemy import Boolean, String, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin, TenantScopedMixin


class ChannelConfig(Base, TimestampMixin, TenantScopedMixin):
    """
    Per-tenant channel configuration.
    channel_type: sms | whatsapp | email

    credentials JSONB shape:
      SMS/WhatsApp: {account_sid, auth_token, phone_number}
      Email:        {smtp_host, smtp_port, smtp_user, smtp_password, from_name}
    """

    __tablename__ = "channel_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    channel_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # sms | whatsapp | email

    credentials: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # channel-specific secrets

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # set True after test send succeeds

    def __repr__(self) -> str:
        return (
            f"<ChannelConfig tenant={self.tenant_id} "
            f"type={self.channel_type} active={self.is_active}>"
        )
