"""add hashed_password to tenants

Revision ID: d4e8f1a2b3c9
Revises: c3d9f2b05e8a
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e8f1a2b3c9'
down_revision = 'c3d9f2b05e8a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('hashed_password', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('tenants', 'hashed_password')
