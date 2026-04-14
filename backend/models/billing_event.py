"""
models/billing_event.py

Records every agent graph execution for usage-based billing.
Each node executed has a cost_weight (from agent registry).
Total units = sum of cost_weights for all nodes executed in one run.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin, TenantScopedMixin


class BillingEvent(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "billing_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # The graph that was executed
    graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Unique ID for this execution run (used as Stripe idempotency key)
    execution_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    # List of agent node types executed in this run: ["intent_classifier", "booking_agent", ...]
    nodes_executed: Mapped[list] = mapped_column(JSONB, nullable=False)

    # Sum of cost_weight for all executed nodes
    total_units: Mapped[float] = mapped_column(Float, nullable=False)

    # Timestamp of execution
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Stripe meter event ID (null until reported to Stripe)
    stripe_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<BillingEvent id={self.id} tenant_id={self.tenant_id} "
            f"units={self.total_units}>"
        )
