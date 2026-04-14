"""
models/staff.py

Staff members (doctors, therapists, stylists, etc.) who perform services.
Each appointment is assigned to a staff member.
Working hours are stored as JSONB for flexibility.
"""

import uuid

from sqlalchemy import Boolean, Integer, String, Text, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin, TenantScopedMixin


class Staff(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Priority for auto-routing (lower = higher priority)
    priority_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # JSONB: { "monday": [{"start": "09:00", "end": "18:00"}], ... }
    # Allows different hours per day + multiple shifts
    working_hours: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Calendar integration
    google_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    calendar_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Staff id={self.id} name={self.full_name}>"
