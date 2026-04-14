"""
core/database.py

Async SQLAlchemy engine + session factory.
All database I/O in this codebase is async — no sync calls allowed.
Session is provided to routes via FastAPI Dependency Injection (get_db).

Usage in a route:
    async def my_route(db: AsyncSession = Depends(get_db)):
        ...
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────
# pool_pre_ping=True ensures stale connections are recycled automatically.
# echo=False in production; set to True only during local debugging.
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.is_development,  # logs SQL only in dev
    future=True,
)

# ── Session Factory ────────────────────────────────────────────────────────────
# expire_on_commit=False prevents SQLAlchemy from expiring objects after commit,
# which would cause additional queries when accessing attributes post-commit.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All SQLAlchemy ORM models inherit from this base.
    Provides metadata registry used by Alembic for migrations.
    """
    pass


# ── Dependency ────────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async DB session per request.
    The session is automatically closed after the request, even on exceptions.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Health Check ──────────────────────────────────────────────────────────────
async def check_db_health() -> bool:
    """
    Executes a lightweight query to verify DB connectivity.
    Called by the /health endpoint.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("db_health_check_failed", extra={"error": str(exc)})
        return False
