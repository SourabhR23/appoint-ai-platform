"""
models/notification_log.py

Tracks every notification sent (or attempted) by the platform.
Used for delivery status, retry tracking, and tenant audit logs.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin, TenantScopedMixin


class NotificationLog(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Links back to the appointment that triggered this notification
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Channel: email | sms | whatsapp
    channel: Mapped[str] = mapped_column(String(20), nullable=False)

    # The recipient address (phone number or email)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)

    # Which template was used: booking_confirmation | reminder_24h | cancellation ...
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)

    # Delivery status: queued | sent | failed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued", index=True
    )

    # Error message from provider (Twilio / SendGrid) if failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Number of send attempts made (max 3 per R8)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # External provider message ID for tracing
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<NotificationLog id={self.id} channel={self.channel} "
            f"status={self.status} recipient={self.recipient}>"
        )
