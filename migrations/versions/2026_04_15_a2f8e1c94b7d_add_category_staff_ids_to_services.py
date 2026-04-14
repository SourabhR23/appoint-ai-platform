"""add category and staff_ids to services

Revision ID: a2f8e1c94b7d
Revises: 65c5cd398923
Create Date: 2026-04-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a2f8e1c94b7d"
down_revision: Union[str, None] = "65c5cd398923"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add category column — nullable, used for rate card grouping
    op.add_column(
        "services",
        sa.Column("category", sa.String(length=100), nullable=True),
    )
    # Add staff_ids JSONB column — list of staff UUID strings who can perform this service
    op.add_column(
        "services",
        sa.Column(
            "staff_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("services", "staff_ids")
    op.drop_column("services", "category")
