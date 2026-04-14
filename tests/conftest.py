"""
tests/conftest.py

Shared pytest fixtures for all tests.

Fixture hierarchy:
  engine → db (per test, rolled back after) → tenant_a, tenant_b (per test)
  client (FastAPI TestClient with auth headers)

Multi-tenant isolation tests use tenant_a and tenant_b.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.core.database import Base, get_db
from backend.core.config import settings
from backend.main import app
from backend.models.tenant import Tenant

# ── Test Database ─────────────────────────────────────────────────────────────
# Use a separate test DB or in-memory SQLite for isolation.
# For full PostgreSQL behaviour (JSONB, UUID), use a real test DB.
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/appointment_db", "/appointment_test_db"
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    """Create all tables once per test session. Drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test DB session. Each test gets a clean transaction that is
    rolled back after the test — no data persists between tests.
    """
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def tenant_a(db: AsyncSession) -> Tenant:
    """Test tenant A — used to verify tenant isolation."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Clinic A",
        business_type="clinic",
        subdomain=f"clinic-a-{uuid.uuid4().hex[:6]}",
        email=f"a-{uuid.uuid4().hex[:6]}@test.com",
        phone="+911234567890",
        timezone="Asia/Kolkata",
        config={
            "booking_window_min_hours": 24,
            "booking_window_max_days": 60,
            "allow_same_day": False,
            "slot_buffer_minutes": 15,
            "cancellation_hours": 24,
            "notification_templates": {},
        },
        plan="trial",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=14),
        is_active=True,
        onboarding_completed=True,
    )
    db.add(tenant)
    await db.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db: AsyncSession) -> Tenant:
    """Test tenant B — used to verify tenant isolation."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Salon B",
        business_type="salon",
        subdomain=f"salon-b-{uuid.uuid4().hex[:6]}",
        email=f"b-{uuid.uuid4().hex[:6]}@test.com",
        phone="+919876543210",
        timezone="Asia/Kolkata",
        config={
            "booking_window_min_hours": 24,
            "booking_window_max_days": 60,
            "allow_same_day": False,
            "slot_buffer_minutes": 15,
            "cancellation_hours": 24,
            "notification_templates": {},
        },
        plan="trial",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=14),
        is_active=True,
        onboarding_completed=True,
    )
    db.add(tenant)
    await db.flush()
    return tenant
