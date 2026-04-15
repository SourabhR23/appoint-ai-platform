"""
scripts/seed_loader.py

Loads synthetic seed data from tests/seed_data.json into the database.

Run this AFTER alembic upgrade head (tables must exist first).

Usage:
    python scripts/seed_loader.py

Design:
- Uses the same AsyncSessionLocal from backend.core.database (no duplicate engine).
- Inserts in dependency order: tenants → staff → services → appointments.
- Idempotent: skips records that already exist (checks by primary key).
- All UUIDs and datetimes are parsed from JSON strings before insert.
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

import bcrypt

from backend.core.database import AsyncSessionLocal
from backend.models.tenant import Tenant
from backend.models.staff import Staff
from backend.models.service import Service
from backend.models.appointment import Appointment


def _hash_password(plain: str) -> str:
    pwd_bytes = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)

SEED_FILE = Path(__file__).resolve().parent.parent / "tests" / "seed_data.json"


# ── Helpers ────────────────────────────────────────────────────────────────────

def to_uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None


def to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    # Ensure timezone-aware UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def exists(session, model, pk: uuid.UUID) -> bool:
    """Returns True if a row with this primary key already exists."""
    result = await session.execute(
        select(model).where(model.id == pk)
    )
    return result.scalar_one_or_none() is not None


# ── Loaders ────────────────────────────────────────────────────────────────────

async def load_tenants(session, records: list[dict]) -> int:
    count = 0
    for r in records:
        pk = to_uuid(r["id"])
        if await exists(session, Tenant, pk):
            logger.info(f"  SKIP  tenant '{r['name']}' — already exists")
            continue

        hashed_password = None
        if r.get("password"):
            hashed_password = _hash_password(r["password"])

        tenant = Tenant(
            id=pk,
            name=r["name"],
            business_type=r["business_type"],
            subdomain=r["subdomain"],
            email=r["email"],
            phone=r["phone"],
            timezone=r.get("timezone", "Asia/Kolkata"),
            country=r.get("country", "IN"),
            config=r.get("config", {}),
            plan=r.get("plan", "trial"),
            is_active=r.get("is_active", True),
            onboarding_completed=r.get("onboarding_completed", False),
            hashed_password=hashed_password,
        )
        session.add(tenant)
        count += 1
        logger.info(f"  ADD   tenant '{r['name']}'")

    return count


async def load_staff(session, records: list[dict]) -> int:
    count = 0
    for r in records:
        pk = to_uuid(r["id"])
        if await exists(session, Staff, pk):
            logger.info(f"  SKIP  staff '{r['full_name']}' — already exists")
            continue

        staff = Staff(
            id=pk,
            tenant_id=to_uuid(r["tenant_id"]),
            full_name=r["full_name"],
            email=r.get("email"),
            phone=r.get("phone"),
            specialization=r.get("specialization"),
            priority_order=r.get("priority_order", 1),
            working_hours=r.get("working_hours", {}),
            google_calendar_id=r.get("google_calendar_id"),
            calendar_connected=r.get("calendar_connected", False),
            is_active=r.get("is_active", True),
        )
        session.add(staff)
        count += 1
        logger.info(f"  ADD   staff '{r['full_name']}'")

    return count


async def load_services(session, records: list[dict]) -> int:
    count = 0
    for r in records:
        pk = to_uuid(r["id"])
        if await exists(session, Service, pk):
            logger.info(f"  SKIP  service '{r['name']}' — already exists")
            continue

        service = Service(
            id=pk,
            tenant_id=to_uuid(r["tenant_id"]),
            name=r["name"],
            description=r.get("description"),
            duration_minutes=r.get("duration_minutes", 30),
            buffer_minutes=r.get("buffer_minutes", 15),
            price_paise=r.get("price_paise", 0),
            is_active=r.get("is_active", True),
        )
        session.add(service)
        count += 1
        logger.info(f"  ADD   service '{r['name']}'")

    return count


async def load_appointments(session, records: list[dict]) -> int:
    count = 0
    for r in records:
        pk = to_uuid(r["id"])
        if await exists(session, Appointment, pk):
            logger.info(f"  SKIP  appointment for '{r['patient_name']}' — already exists")
            continue

        appointment = Appointment(
            id=pk,
            tenant_id=to_uuid(r["tenant_id"]),
            patient_name=r["patient_name"],
            patient_phone=r["patient_phone"],
            patient_email=r.get("patient_email"),
            service_id=to_uuid(r["service_id"]),
            staff_id=to_uuid(r["staff_id"]),
            slot_datetime=to_dt(r["slot_datetime"]),
            slot_end_datetime=to_dt(r["slot_end_datetime"]),
            status=r.get("status", "pending"),
            channel=r.get("channel", "webchat"),
            notes=r.get("notes"),
            cancellation_reason=r.get("cancellation_reason"),
            idempotency_key=r["idempotency_key"],
            recurrence_group_id=to_uuid(r.get("recurrence_group_id")),
            recurrence_index=r.get("recurrence_index"),
            google_event_id=r.get("google_event_id"),
            deleted_at=to_dt(r.get("deleted_at")),
        )
        session.add(appointment)
        count += 1
        logger.info(f"  ADD   appointment for '{r['patient_name']}' on {r['slot_datetime'][:10]}")

    return count


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    logger.info(f"Loading seed data from: {SEED_FILE}")

    if not SEED_FILE.exists():
        logger.error(f"Seed file not found: {SEED_FILE}")
        sys.exit(1)

    with open(SEED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Seed file version: {data['_meta']['version']}")
    logger.info("")

    async with AsyncSessionLocal() as session:
        try:
            # Order matters — staff/services/appointments reference tenants
            logger.info("── Tenants ──────────────────────────────────")
            t = await load_tenants(session, data.get("tenants", []))

            logger.info("── Staff ─────────────────────────────────────")
            s = await load_staff(session, data.get("staff", []))

            logger.info("── Services ──────────────────────────────────")
            sv = await load_services(session, data.get("services", []))

            logger.info("── Appointments ──────────────────────────────")
            a = await load_appointments(session, data.get("appointments", []))

            await session.commit()

            logger.info("")
            logger.info("── Summary ───────────────────────────────────")
            logger.info(f"  Tenants inserted     : {t}")
            logger.info(f"  Staff inserted       : {s}")
            logger.info(f"  Services inserted    : {sv}")
            logger.info(f"  Appointments inserted: {a}")
            logger.info("  Seed completed successfully.")

        except Exception as exc:
            await session.rollback()
            logger.error(f"Seed failed — rolled back. Error: {exc}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
