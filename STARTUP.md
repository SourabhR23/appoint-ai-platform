# STARTUP.md — AppointAI Platform
## Complete Setup and Run Guide

> Keep this file updated as new phases are completed.  
> Every command listed here has been verified to work.

---

## Quick Reference (Already Set Up)

If the environment is already created and `.env` is configured, skip to **[Daily Start](#daily-start)**.

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Anaconda / Miniconda | Any recent | Python environment manager |
| Python | 3.11+ (via conda) | Backend runtime |
| Git | Any | Version control |
| Browser | Any modern | Frontend (served by backend) |

**Cloud accounts required (free tiers work):**
- [Supabase](https://supabase.com) — PostgreSQL database + Auth
- [Upstash](https://upstash.com) — Redis (TLS, serverless)
- [EuriAI](https://euron.one) — OpenAI-compatible LLM API

---

## One-Time Setup

### Step 1 — Clone and Navigate

```bash
git clone <your-repo-url>
cd AI_Appointment_Agent_Platform
```

### Step 2 — Create Conda Environment

```bash
conda create -n appt_agent python=3.11 -y
conda activate appt_agent
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
pip install aiofiles        # required for FastAPI StaticFiles (frontend serving)
```

### Step 4 — Configure Environment

```bash
# Copy the template
copy .env.example .env     # Windows
# cp .env.example .env     # Mac/Linux

# Edit .env and fill in your real values:
# DATABASE_URL     → Supabase session pooler URL (postgresql+asyncpg://...)
# REDIS_URL        → Upstash rediss:// URL
# SUPABASE_URL     → https://your-ref.supabase.co
# SUPABASE_JWT_SECRET → from Supabase dashboard → Settings → API → JWT Secret
# OPENAI_API_KEY   → your EuriAI key
# OPENAI_BASE_URL  → https://api.euron.one/api/v1/euri
# OPENAI_MODEL     → gpt-4.1-mini
```

> **Supabase DATABASE_URL format (Session Pooler — required on Windows):**
> ```
> postgresql+asyncpg://postgres.[project-ref]:[password]@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres
> ```
> Get it from: Supabase Dashboard → Project Settings → Database → Connection String → URI  
> Then switch the dropdown from "Direct connection" to **"Session pooler"**  
> Then prepend `+asyncpg` so it reads `postgresql+asyncpg://...`

> **Upstash REDIS_URL format:**
> ```
> rediss://default:[password]@[endpoint].upstash.io:6379
> ```
> Note the `rediss://` (double-s) — Upstash requires TLS.

### Step 5 — Run Database Migrations

```bash
conda activate appt_agent
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 65c5cd398923, initial_schema
INFO  [alembic.runtime.migration] Running upgrade 65c5cd398923 -> a2f8e1c94b7d, add_category_staff_ids_to_services
```

### Step 6 — Load Seed Data (Demo Tenants)

```bash
python scripts/seed_loader.py
```

This creates two demo tenants in the database:
- **MedCare Clinic** — subdomain: `medcare`
- **Gloss & Glow Salon** — subdomain: `glossglow`

Each includes staff members, services, and sample appointments for demo purposes.

---

## Daily Start

### Backend (FastAPI + Uvicorn)

```bash
conda activate appt_agent
cd AI_Appointment_Agent_Platform
uvicorn backend.main:app --reload
```

Server starts at: **http://localhost:8000**  
API docs (dev only): **http://localhost:8000/docs**  
Frontend: **http://localhost:8000** (served automatically by FastAPI StaticFiles)

> `--reload` enables hot-reload on code changes. Remove it in production.

### Frontend

No separate command needed. The frontend (`frontend/index.html`) is served directly by the FastAPI backend via `StaticFiles`. Open **http://localhost:8000** in your browser.

---

## Optional: Background Workers (Celery)

Celery handles async tasks: appointment reminders, notification delivery, retry logic.  
Only needed if testing notification features.

```bash
# Terminal 2 — Celery Worker
conda activate appt_agent
celery -A backend.workers.celery_app worker --loglevel=info

# Terminal 3 — Celery Beat (scheduled tasks / reminders)
conda activate appt_agent
celery -A backend.workers.celery_app beat --loglevel=info
```

> Workers connect to Upstash Redis via `CELERY_BROKER_URL` in `.env`.

---

## Docker (Alternative to Conda)

If you prefer Docker over conda:

```bash
# Build and start backend + workers
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all
docker-compose down
```

> Docker uses the same `.env` file. No local PostgreSQL or Redis containers — both are cloud-hosted.

---

## Demo Login

Once the backend is running and seed data is loaded, open http://localhost:8000 and log in with either demo tenant:

| Tenant | Subdomain | Business Type |
|---|---|---|
| MedCare Clinic | `medcare` | Medical clinic, dual OPD sessions |
| Gloss & Glow Salon | `glossglow` | Beauty salon, 4 service categories |

Click either card on the login screen — no password needed in dev mode (demo-token endpoint issues a JWT automatically).

---

## Migration History

| Migration ID | Description | Applied |
|---|---|---|
| `65c5cd398923` | Initial schema — all 8 tables (tenants, staff, services, appointments, graphs, graph_versions, notification_logs, billing_events) | Phase 1 |
| `a2f8e1c94b7d` | Add `category` and `staff_ids` columns to `services` table | Phase 2 |
| `c3d9f2b05e8a` | Add `channel_configs` table — per-tenant SMS/WhatsApp/Email credentials | Phase 3 |

### Adding a New Migration

```bash
# After changing a model in backend/models/
alembic revision --autogenerate -m "describe_your_change"
alembic upgrade head
```

---

## Phase Build Status

| Phase | What Was Built | Status |
|---|---|---|
| **Phase 1** | Core backend (auth, appointments, staff, graphs, chat), LangGraph agent pipeline, tenant portal frontend (login, dashboard, appointments, AI chat, agent setup with template activation) | ✅ Complete |
| **Phase 2** | Services CRUD + rate card UI, staff add/edit/deactivate + working hours editor, slot availability API + calendar page with slot checker | ✅ Complete |
| **Phase 3** | Channel Setup UI (SMS/WhatsApp/Email configure per tenant), Twilio inbound webhooks, Gmail SMTP email, `channel_configs` table | ✅ Complete |
| **Bug fixes** | 6 agent pipeline bugs resolved: contextvars db injection, graph cache, conditional edge routing, EXTRACTION_PROMPT KeyError, service name lookup, exc_info logging | ✅ Complete |
| **Phase 4** | Public website, onboarding wizard (business type → agent template → services → hours → payment), login credential flashcard | 🔲 Not started |
| **Phase 5** | Super admin portal (LLM usage, billing, tenant health), LLM token logging, Stripe metered billing | 🔲 Not started |

---

## API Endpoints (Current — Phase 2)

All routes are prefixed `/api/v1/`. All protected routes require `Authorization: Bearer <token>`.

| Method | Route | Auth | Description |
|---|---|---|---|
| GET | /health | Public | Service health check |
| POST | /auth/register | Public | Create tenant account |
| GET | /auth/me | JWT | Current tenant profile |
| GET | /auth/demo-token?subdomain= | Dev only | Issue demo JWT |
| GET | /appointments | JWT | List appointments (paginated, filtered) |
| POST | /appointments | JWT | Manual booking |
| PATCH | /appointments/{id} | JWT | Update status / notes |
| DELETE | /appointments/{id} | JWT | Soft-cancel |
| POST | /appointments/{id}/reschedule | JWT | Change slot |
| GET | /staff | JWT | List staff |
| POST | /staff | JWT | Add staff member |
| PATCH | /staff/{id} | JWT | Update staff |
| DELETE | /staff/{id} | JWT | Deactivate staff |
| GET | /services | JWT | List services (rate card) |
| POST | /services | JWT | Add service |
| PATCH | /services/{id} | JWT | Update service |
| DELETE | /services/{id} | JWT | Deactivate service |
| GET | /slots | JWT | Available time slots for a date + service |
| GET | /graphs | JWT | List agent graphs |
| POST | /graphs | JWT | Create graph with definition |
| PUT | /graphs/{id} | JWT | Save new version |
| POST | /graphs/{id}/deploy | JWT | Deploy version |
| POST | /chat/{graph_id} | JWT | Send message through agent |
| GET | /channels | JWT | List configured channels |
| POST | /channels | JWT | Save channel credentials (validates before saving) |
| DELETE | /channels/{type} | JWT | Deactivate a channel |
| POST | /webhooks/twilio/sms | Public | Inbound SMS from Twilio |
| POST | /webhooks/twilio/whatsapp | Public | Inbound WhatsApp from Twilio |

---

## Project Structure (Quick Reference)

```
AI_Appointment_Agent_Platform/
├── backend/
│   ├── main.py              # FastAPI app factory, middleware, lifespan
│   ├── core/
│   │   ├── config.py        # All env vars via pydantic-settings
│   │   ├── database.py      # AsyncSession, DB health check
│   │   └── security.py      # JWT verification, get_current_tenant
│   ├── models/              # SQLAlchemy ORM models (one file per table)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── repositories/        # DB access layer (all queries here)
│   ├── api/                 # Route handlers (thin — call services/repos)
│   ├── services/            # Business logic (appointment_service, etc.)
│   ├── agents/              # LangGraph agent implementations
│   ├── graph/               # Graph builder, executor, registry
│   └── workers/             # Celery tasks (reminders, notifications)
├── frontend/
│   └── index.html           # Single-file SPA served by FastAPI
├── migrations/
│   ├── env.py               # Alembic config (sync engine for CLI)
│   └── versions/            # Migration files — never edit manually
├── scripts/
│   └── seed_loader.py       # Loads tests/seed_data.json into DB
├── tests/
│   └── seed_data.json       # Demo data for 2 tenants
├── docs/                    # Architecture, PRD, BRD, Master Guide
├── .env                     # Real secrets — never commit
├── .env.example             # Template — commit this
├── requirements.txt         # Pinned Python dependencies
├── docker-compose.yml       # Docker setup (cloud DB/Redis, no local containers)
└── STARTUP.md               # This file
```

---

## Troubleshooting

### "Database is not reachable" on startup
- Check `DATABASE_URL` in `.env` uses the **Session Pooler** URL, not the direct connection
- Format must start with `postgresql+asyncpg://` (not just `postgresql://`)
- Verify Supabase project is active (free projects pause after 1 week of inactivity — unpause from dashboard)

### "Connection refused" for Redis
- Check `REDIS_URL` starts with `rediss://` (two s's — TLS required by Upstash)
- Verify the Upstash database is in the free tier and not rate-limited

### "failed to fetch" in browser
- Open the app via **http://localhost:8000** — not by opening `index.html` as a file
- The frontend must be served by FastAPI to avoid CORS/null-origin issues

### Alembic "Can't locate revision"
- Run `alembic history` to see applied migrations
- If `down_revision` mismatch, check that all migration files are in `migrations/versions/`

### LLM / Agent not responding
- Verify `OPENAI_API_KEY` and `OPENAI_BASE_URL` in `.env`
- The agent requires a graph to be created and deployed first — go to Agent Setup in the UI
- Check `DEBUG=true` in `.env` to see detailed logs in the uvicorn console

---

*Last updated: Phase 2 complete — April 2026*
