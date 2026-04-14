"""
models/base_model.py

Shared mixin for all ORM models.
Every table has: id (UUID PK), tenant_id (UUID FK), created_at, updated_at.
This enforces the multi-tenancy and audit requirements from RULES.md.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class TimestampMixin:
    """Adds created_at and updated_at to any model. All stored in UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantScopedMixin:
    """
    Adds tenant_id to any model.
    tenant_id is NOT a FK at the ORM level — we use RLS policies at DB level.
    This design avoids FK cascade issues across tenant-isolated tables.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,  # index for fast tenant-scoped queries
    )
