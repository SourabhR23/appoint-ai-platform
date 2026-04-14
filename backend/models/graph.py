"""
models/graph.py

Two tables:
1. graphs — one row per saved workflow (the "latest" pointer)
2. graph_versions — full JSON snapshot per version (R6)

This allows:
- Version history and rollback
- Diff between deployed and draft
- Safe compilation from a specific version snapshot
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin, TenantScopedMixin


class Graph(Base, TenantScopedMixin, TimestampMixin):
    """
    A saved agent workflow. The frontend stores React Flow JSON here.
    `active_version` points to which graph_versions row is deployed.
    """

    __tablename__ = "graphs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Which version is live
    active_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Whether this graph is currently serving incoming chats
    is_deployed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<Graph id={self.id} name={self.name} v{self.active_version}>"


class GraphVersion(Base, TenantScopedMixin, TimestampMixin):
    """
    Immutable snapshot of a graph at a specific version number.
    A new row is created on every save — old versions are never overwritten.
    """

    __tablename__ = "graph_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Full React Flow JSON: { nodes: [...], edges: [...] }
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Whether this version is the currently deployed one
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # When this version was compiled into a LangGraph (null = not yet compiled)
    compiled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<GraphVersion graph_id={self.graph_id} version={self.version}>"
