"""
models/user.py

Platform user — admins and staff who log in to the dashboard.
Auth is handled by Supabase; this table stores profile + role info.
The `id` here matches the Supabase Auth user UUID.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin, TenantScopedMixin


class User(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "users"

    # Matches Supabase Auth user ID — not auto-generated
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Role within the tenant
    # admin — full access (business owner)
    # staff — view/manage appointments, no graph builder
    # super_admin — cross-tenant access (platform operators only)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="staff")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
