"""
migrations/env.py

Alembic migration environment — uses a SYNC engine.
Migrations run from the CLI, not inside an async request, so sync is correct here.
The application runtime uses asyncpg; migrations use psycopg2-binary (sync).

DATABASE_URL is read from settings (environment variable).
asyncpg prefix is swapped to psycopg2 automatically.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add project root to path so backend imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import all models so Alembic autogenerate detects every table
from backend.models import *  # noqa: F401, F403
from backend.core.database import Base
from backend.core.config import settings

# Alembic config object (from alembic.ini)
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which metadata to compare against
target_metadata = Base.metadata

# Convert async URL → sync URL for Alembic
# postgresql+asyncpg://...  →  postgresql+psycopg2://...
sync_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    """Generate SQL script without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live database (sync)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
