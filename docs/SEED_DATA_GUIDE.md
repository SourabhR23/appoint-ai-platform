# Seed Data Guide

## What is Seed Data?

When you build a backend, the database starts completely empty. Before you can demo or test anything, you need some baseline data — tenants, staff, services, and appointments that already exist so the system behaves like a real running product.

**Seed data** is that pre-loaded baseline. It is not real production data — it is carefully crafted synthetic data that mimics how the system will actually be used.

In this project, seed data covers two tenants:
- **MedCare Clinic** — a medical clinic with OPD, Paediatrics, and Gynaecology sections
- **Gloss & Glow Salon** — a beauty salon with Hair, Skin, Nails, and Bridal sections

---

## Files Involved

```
tests/seed_data.json       ← the data itself (JSON)
scripts/seed_loader.py     ← the script that reads JSON and inserts into DB
docs/SEED_DATA_GUIDE.md    ← this file
```

---

## Tech Stack Used for Seeding — and Why

### PostgreSQL (via Supabase)

The application uses **PostgreSQL** as its database. We use **Supabase** to host it in the cloud — no local database setup needed.

PostgreSQL was chosen over alternatives like MongoDB because:

| Reason | Explanation |
|--------|-------------|
| **Multi-tenant RLS** | PostgreSQL's Row-Level Security (RLS) enforces tenant isolation at the database layer |
| **JSONB columns** | Flexible config fields (`business_hours`, `working_hours`) are stored as JSONB — structured but schema-flexible |
| **ACID transactions** | Appointment booking requires atomicity — book + notify must succeed or both fail |
| **Relational integrity** | `tenant_id` links every row back to a tenant — consistent across all tables |

MongoDB Atlas was considered but rejected — the schema is well-defined and relational, and JSONB in PostgreSQL gives the same flexibility for config fields without abandoning SQL.

### SQLAlchemy (Async)

The project uses **SQLAlchemy** as the ORM (Object-Relational Mapper). This means Python classes represent database tables.

From `backend/models/tenant.py`:
```python
class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ...
```

The seed loader uses these same ORM classes to insert data — not raw SQL. This means:
- Type safety (UUID, datetime, dict all validated)
- No SQL injection risk
- Consistent with how the rest of the app writes to the database

The engine is **async** (using `asyncpg` driver) because the FastAPI application is fully async. The seed loader reuses the same `AsyncSessionLocal` from `backend/core/database.py`:

```python
# backend/core/database.py — reused by seed loader
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
```

### asyncpg

`asyncpg` is the async PostgreSQL driver. It replaces the traditional `psycopg2` for async code. The `DATABASE_URL` must use `postgresql+asyncpg://` to use it:

```
DATABASE_URL=postgresql+asyncpg://postgres:password@db.xyz.supabase.co:5432/postgres
```

### Alembic (migrations — must run before seeding)

Before seed data can be inserted, the tables must exist. **Alembic** creates those tables by reading the ORM models and generating SQL migration files.

```
ORM models (Python)  →  alembic revision --autogenerate  →  migration file
migration file       →  alembic upgrade head              →  tables in Postgres
tables exist         →  python scripts/seed_loader.py     →  data in tables
```

---

## How the Seed Loader Works

### Step 1 — Read JSON

```python
# scripts/seed_loader.py
with open(SEED_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)
```

`seed_data.json` contains four lists: `tenants`, `staff`, `services`, `appointments`.

### Step 2 — Open a DB Session

```python
async with AsyncSessionLocal() as session:
    ...
    await session.commit()
```

This is the same pattern the FastAPI routes use via `Depends(get_db)`. The difference is that in a script there's no HTTP request — we open the session manually.

### Step 3 — Idempotency Check

Before inserting any record, the loader checks if it already exists by primary key:

```python
async def exists(session, model, pk: uuid.UUID) -> bool:
    result = await session.execute(
        select(model).where(model.id == pk)
    )
    return result.scalar_one_or_none() is not None
```

If the record exists, it is skipped with a log message. This means you can run the loader multiple times safely — it will never create duplicates.

### Step 4 — Insert in Dependency Order

The order matters because `staff`, `services`, and `appointments` all reference `tenant_id`. If a tenant doesn't exist yet when staff is inserted, the DB will reject it.

```
tenants  →  staff  →  services  →  appointments
```

```python
t  = await load_tenants(session, data["tenants"])
s  = await load_staff(session, data["staff"])
sv = await load_services(session, data["services"])
a  = await load_appointments(session, data["appointments"])

await session.commit()   # one atomic commit — all or nothing
```

### Step 5 — Type Conversion

JSON stores everything as strings. The ORM expects proper Python types. Two helper functions handle conversion:

```python
def to_uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None

def to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)   # always UTC
    return dt
```

### Step 6 — ORM Object Creation

Each JSON record is mapped to its ORM class, matching the same model the app uses at runtime:

```python
# Same Tenant model used by FastAPI routes, agents, and seed loader
tenant = Tenant(
    id=to_uuid(r["id"]),
    name=r["name"],
    business_type=r["business_type"],
    config=r.get("config", {}),   # JSONB — Python dict maps directly
    ...
)
session.add(tenant)
```

---

## The Seed Data — What's Inside

### Tenant 1: MedCare Clinic

```json
{
  "id": "11111111-0000-0000-0000-000000000001",
  "name": "MedCare Clinic",
  "business_type": "clinic",
  "subdomain": "medcare",
  "config": {
    "business_hours": {
      "monday":   [{"start": "09:00", "end": "13:00"}, {"start": "17:00", "end": "20:30"}],
      "saturday": [{"start": "09:00", "end": "14:00"}],
      "sunday":   []
    },
    "sections": ["General OPD", "Paediatrics", "Gynaecology"],
    "allow_same_day": true,
    "cancellation_hours": 2
  }
}
```

Split shift hours (morning + evening) — typical for Indian clinics. Sunday closed.

### Tenant 2: Gloss & Glow Salon

```json
{
  "id": "22222222-0000-0000-0000-000000000002",
  "name": "Gloss & Glow Salon",
  "business_type": "salon",
  "subdomain": "glossglow",
  "config": {
    "business_hours": {
      "monday":   [],
      "friday":   [{"start": "10:00", "end": "21:00"}],
      "saturday": [{"start": "09:00", "end": "21:00"}]
    },
    "sections": ["Hair", "Skin & Facial", "Nails", "Bridal"],
    "allow_same_day": true,
    "cancellation_hours": 1
  }
}
```

Closed on Mondays (common for salons). Extended hours on Friday/Saturday.

### Staff Working Hours (JSONB)

Staff hours are stored as JSONB — different days, different shifts:

```json
{
  "full_name": "Dr. Priya Mehta",
  "specialization": "General Physician",
  "working_hours": {
    "monday":    [{"start": "09:00", "end": "13:00"}, {"start": "17:00", "end": "20:30"}],
    "wednesday": [{"start": "09:00", "end": "13:00"}],
    "sunday":    []
  }
}
```

This maps directly to the `Staff.working_hours` JSONB column. The booking agent reads this when checking slot availability.

### Services (Price in Paise)

```json
{
  "name": "General Consultation",
  "duration_minutes": 15,
  "buffer_minutes": 5,
  "price_paise": 50000
}
```

`price_paise = 50000` means ₹500 (50000 paise = ₹500). Integer storage avoids floating-point precision errors for currency.

---

## How to Run

### Prerequisites

```bash
# 1. Tables must exist first
alembic upgrade head

# 2. Then load data
python scripts/seed_loader.py
```

### Expected Output

```
2026-04-14  INFO  Loading seed data from: tests/seed_data.json
2026-04-14  INFO  Seed file version: 1.0.0

── Tenants ──────────────────────────────────
2026-04-14  INFO    ADD   tenant 'MedCare Clinic'
2026-04-14  INFO    ADD   tenant 'Gloss & Glow Salon'
── Staff ─────────────────────────────────────
2026-04-14  INFO    ADD   staff 'Dr. Priya Mehta'
2026-04-14  INFO    ADD   staff 'Dr. Arjun Nair'
...
── Summary ───────────────────────────────────
2026-04-14  INFO    Tenants inserted     : 2
2026-04-14  INFO    Staff inserted       : 6
2026-04-14  INFO    Services inserted    : 14
2026-04-14  INFO    Appointments inserted: 6
2026-04-14  INFO    Seed completed successfully.
```

### Running Again (Idempotent)

```
── Tenants ──────────────────────────────────
2026-04-14  INFO    SKIP  tenant 'MedCare Clinic' — already exists
2026-04-14  INFO    SKIP  tenant 'Gloss & Glow Salon' — already exists
```

Safe to run multiple times.

---

## How Seed Data Connects to the Running Application

Once loaded, these records are immediately usable by the API. Here's the chain from seed data to a live API response:

```
seed_data.json
    ↓ seed_loader.py inserts
PostgreSQL (Supabase)
    ↓ SQLAlchemy ORM reads
backend/repositories/appointment_repo.py
    ↓ called by
backend/services/appointment_service.py
    ↓ called by
backend/api/appointments.py  →  GET /api/v1/appointments
    ↓
{ "items": [...seeded appointments...], "total": 6 }
```

The booking agent also reads staff and services from the same tables when checking availability:

```python
# backend/agents/booking_agent.py
has_conflict = await check_slot_conflict(
    db, tenant_id, staff_id, requested_dt, slot_end
)
# → queries the same staff rows loaded by seed_loader.py
```

---

## Adding More Seed Data Later

To add a new tenant or staff member:

1. Open `tests/seed_data.json`
2. Add new objects to the relevant list (`tenants`, `staff`, `services`, `appointments`)
3. Use a new unique UUID for each `id`
4. Run `python scripts/seed_loader.py` — existing records are skipped, only new ones are inserted
