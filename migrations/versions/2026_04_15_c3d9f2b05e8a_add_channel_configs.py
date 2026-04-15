"""add_channel_configs

Revision ID: c3d9f2b05e8a
Revises: a2f8e1c94b7d
Create Date: 2026-04-15

Phase 3 — per-tenant notification channel credentials table.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "c3d9f2b05e8a"
down_revision = "a2f8e1c94b7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channel_configs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("channel_type", sa.String(20), nullable=False),
        sa.Column(
            "credentials",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Enforce one row per tenant per channel type
    op.create_unique_constraint(
        "uq_channel_configs_tenant_channel",
        "channel_configs",
        ["tenant_id", "channel_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_channel_configs_tenant_channel", "channel_configs", type_="unique"
    )
    op.drop_table("channel_configs")
