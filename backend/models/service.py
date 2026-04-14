"""
models/service.py

Services offered by the business (e.g. "Dental Cleaning", "Haircut", "Consultation").
Each appointment is linked to one service.
Duration and buffer configure the slot availability checker.
"""

import uuid

from sqlalchemy import Boolean, Integer, String, Text, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin, TenantScopedMixin


class Service(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Category groups services on the rate card (e.g. "Hair", "Skin", "General OPD")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # UUIDs of staff members who can perform this service (stored as JSONB list of strings)
    staff_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # Duration of the appointment slot in minutes
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Buffer added AFTER each appointment before the next slot opens
    # Defaults to tenant-level config if not set per-service
    buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    # Price in minor currency units (paise for INR, cents for USD)
    # Stored as integer to avoid floating-point errors
    price_paise: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name} duration={self.duration_minutes}m>"
