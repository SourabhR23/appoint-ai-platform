"""
models/tenant.py

Tenant model — one row per registered business.
A tenant represents a clinic, salon, coaching center, etc.
Every other table is scoped to tenant_id.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base_model import TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Business identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # clinic | salon | consultancy | coaching
    subdomain: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )  # e.g. "drpatel" → drpatel.appointai.in
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Localisation
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Asia/Kolkata"
    )
    country: Mapped[str] = mapped_column(String(10), nullable=False, default="IN")

    # JSONB — flexible config that differs per tenant
    # Stores: business_hours, cancellation_hours, allow_same_day, slot_buffer_minutes,
    #         booking_window_min_hours, booking_window_max_days, notification templates
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Billing & plan
    plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="trial"
    )  # trial | starter | growth | pro | enterprise
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_executions_used: Mapped[int] = mapped_column(default=0, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationships (back-reference only — FK is on the child table)
    # Declared here for convenience in queries; lazy="select" avoids N+1
    # relationships are defined in child models via back_populates

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name} plan={self.plan}>"
