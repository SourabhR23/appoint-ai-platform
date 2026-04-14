<div align="center">

# AppointAI Platform

**Multi-tenant AI appointment agent platform for appointment-driven businesses.**  
Build a virtual receptionist — no code required.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Engine-blueviolet?style=flat)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=flat&logo=postgresql&logoColor=white)](https://supabase.com)
[![Redis](https://img.shields.io/badge/Redis-Upstash-DC382D?style=flat&logo=redis&logoColor=white)](https://upstash.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

</div>

---

## What Is This?

AppointAI is a **multi-tenant SaaS platform** that lets clinics, salons, coaching centers, and other appointment-driven businesses deploy an AI-powered virtual receptionist — without writing a single line of code.

A business logs into their dashboard, selects which AI agents to activate, and their virtual receptionist is live — handling bookings, reschedules, cancellations, and reminders across **WhatsApp, SMS, and web chat**, 24/7.

```
Customer sends WhatsApp message
        ↓
  Intent Classifier  (What does the user want?)
        ↓
  ┌─────┴──────────────────────────────────────┐
  │  book → Booking Agent → Notification Agent  │
  │  reschedule → Reschedule Agent → Notify     │
  │  cancel → Cancellation Agent → Notify       │
  │  check  → Status Checker                    │
  │  other  → Escalation Agent                  │
  └─────────────────────────────────────────────┘
        ↓
  Confirmed appointment in dashboard
```

---

## Features

### For Businesses (Tenant Portal)
- **Dashboard** — appointment counts, AI agent status, recent bookings at a glance
- **Rate Card** — manage services with prices (₹), durations, and assigned staff; grouped by category
- **Staff Management** — add/edit staff, set per-day working hours with multi-session support (morning + evening shifts)
- **Calendar** — monthly booking view with color-coded status, click any day for details
- **Slot Checker** — see available time slots per staff per date before manually booking
- **AI Agent Setup** — activate a pre-built agent template in one click (Full Booking Suite, Booking Only, Info & Status)
- **AI Chat** — live chat interface connected to the deployed agent graph

### For the Platform (Architecture)
- **Multi-tenancy** — every tenant's data is isolated via `tenant_id` scoping on every table and Supabase RLS
- **Agent Graphs** — visual node-edge configuration compiled into LangGraph `StateGraph` at runtime; versioned and rollback-capable
- **Graph Caching** — compiled graphs cached in Redis; no recompilation per message
- **Async throughout** — FastAPI + SQLAlchemy async + asyncpg — no blocking I/O
- **Worker queue** — Celery + Redis for async notifications, reminders, and retry logic

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | FastAPI 0.111 + Python 3.11 | API server, dependency injection, async routes |
| **Agent Engine** | LangGraph + LangChain | Stateful multi-agent graph orchestration |
| **LLM** | EuriAI (OpenAI-compatible) | Intent classification, entity extraction, response generation |
| **Database** | PostgreSQL via Supabase | Multi-tenant data store, Row-Level Security |
| **Cache / Queue** | Redis via Upstash (TLS) | Graph cache, Celery broker, rate limiting |
| **ORM** | SQLAlchemy 2.0 async | Async DB access, Alembic migrations |
| **Auth** | Supabase Auth + JWT | Multi-tenant JWT with `tenant_id` claims |
| **Notifications** | Twilio + SendGrid | WhatsApp, SMS, email delivery |
| **Billing** | Stripe | Subscription plans + usage-based metering |
| **Frontend** | Vanilla JS + Tailwind CSS | Single-file SPA served by FastAPI |
| **Workers** | Celery + Redis | Reminders, async notification delivery |
| **Deployment** | Docker + docker-compose | Containerized, cloud-DB-backed |

---

## Project Structure

```
appoint-ai-platform/
├── backend/
│   ├── main.py                    # FastAPI app factory, middleware, lifespan
│   ├── core/
│   │   ├── config.py              # All settings via pydantic-settings (env vars)
│   │   ├── database.py            # Async engine, session factory, health check
│   │   └── security.py            # JWT verification, get_current_tenant dependency
│   ├── models/                    # SQLAlchemy ORM — one file per table
│   ├── schemas/                   # Pydantic request/response validation
│   ├── repositories/              # All DB queries (tenant-scoped)
│   ├── api/                       # Route handlers — thin, delegate to services/repos
│   │   ├── appointments.py
│   │   ├── staff.py
│   │   ├── services.py            # Rate card CRUD
│   │   ├── slots.py               # Slot availability computation
│   │   ├── graphs.py              # Agent graph create/version/deploy
│   │   └── chat.py                # Chat endpoint → LangGraph executor
│   ├── agents/                    # Individual AI agent implementations
│   │   ├── base.py
│   │   ├── intent_classifier.py
│   │   ├── booking_agent.py
│   │   ├── reschedule_agent.py
│   │   ├── cancellation_agent.py
│   │   ├── status_checker.py
│   │   ├── notification_agent.py
│   │   └── escalation_agent.py
│   ├── graph/
│   │   ├── builder.py             # JSON definition → LangGraph StateGraph
│   │   ├── executor.py            # Run a compiled graph against a message
│   │   ├── registry.py            # Agent type → class mapping
│   │   └── state.py               # GraphState TypedDict
│   ├── services/                  # Business logic (appointment_service, etc.)
│   └── workers/                   # Celery tasks — reminders, notifications
├── frontend/
│   └── index.html                 # Single-file SPA — served by FastAPI at /
├── migrations/
│   ├── env.py                     # Alembic config (sync engine for CLI)
│   └── versions/                  # Migration files — complete history
├── scripts/
│   └── seed_loader.py             # Loads demo data into the database
├── tests/
│   ├── seed_data.json             # Demo tenants: MedCare Clinic + Gloss & Glow Salon
│   ├── test_agents/
│   └── test_repositories/
├── .env.example                   # All required env vars documented (no real values)
├── docker-compose.yml             # Backend + Celery worker + beat (no local DB needed)
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── STARTUP.md                     # Full setup and run guide
```

---

## Quick Start

### Prerequisites
- [Anaconda](https://anaconda.com) or Miniconda
- [Supabase](https://supabase.com) account (free) — PostgreSQL + Auth
- [Upstash](https://upstash.com) account (free) — Redis
- [EuriAI](https://euron.one) API key — OpenAI-compatible LLM

### Setup

```bash
# 1. Clone
git clone https://github.com/SourabhR23/appoint-ai-platform.git
cd appoint-ai-platform

# 2. Create environment
conda create -n appt_agent python=3.11 -y
conda activate appt_agent

# 3. Install dependencies
pip install -r requirements.txt
pip install aiofiles

# 4. Configure
copy .env.example .env
# Edit .env — fill in DATABASE_URL, REDIS_URL, SUPABASE_*, OPENAI_*

# 5. Run migrations
alembic upgrade head

# 6. Load demo data
python scripts/seed_loader.py

# 7. Start server
uvicorn backend.main:app --reload
```

Open **http://localhost:8000** — the frontend loads automatically.

> Full setup details, troubleshooting, and Docker instructions: see **[STARTUP.md](STARTUP.md)**

---

## Environment Variables

Copy `.env.example` to `.env` and fill in these values:

| Variable | Where to Get It |
|---|---|
| `DATABASE_URL` | Supabase → Project Settings → Database → Session Pooler URI → prepend `+asyncpg` |
| `REDIS_URL` | Upstash console → Redis DB → `rediss://` URL |
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_JWT_SECRET` | Supabase → Project Settings → API → JWT Secret |
| `OPENAI_API_KEY` | EuriAI dashboard |
| `OPENAI_BASE_URL` | `https://api.euron.one/api/v1/euri` |

---

## API Overview

All routes are under `/api/v1/`. Protected routes require `Authorization: Bearer <token>`.  
Response envelope: `{ "success": bool, "data": any, "error": string | null }`

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/auth/register` | Create tenant account |
| `GET` | `/auth/me` | Current tenant profile |
| `GET` | `/appointments` | List appointments (paginated + filtered) |
| `POST` | `/appointments` | Manual booking |
| `GET` | `/staff` | List staff members |
| `POST` | `/staff` | Add staff member |
| `PATCH` | `/staff/{id}` | Update staff / working hours |
| `DELETE` | `/staff/{id}` | Deactivate staff |
| `GET` | `/services` | Rate card — all active services |
| `POST` | `/services` | Add service |
| `PATCH` | `/services/{id}` | Update service (price, duration, staff) |
| `DELETE` | `/services/{id}` | Deactivate service |
| `GET` | `/slots` | Available time slots for a date + service |
| `POST` | `/graphs` | Create agent graph with definition |
| `POST` | `/graphs/{id}/deploy` | Deploy graph version (makes it live) |
| `POST` | `/chat/{graph_id}` | Send message through deployed agent |

Full route reference in [STARTUP.md](STARTUP.md#api-endpoints-current--phase-2).

---

## Agent System

Each tenant deploys an **agent graph** — a directed state machine where nodes are AI agents and edges are routing rules.

### Available Agents

| Agent | Role | LLM Call |
|---|---|---|
| `intent_classifier` | Classify incoming message into: book / reschedule / cancel / check / other | Yes |
| `booking_agent` | Extract service + datetime, check slot availability, create appointment | Yes |
| `reschedule_agent` | Identify existing appointment, validate new slot, update | Yes |
| `cancellation_agent` | Soft-cancel appointment, log reason | Yes |
| `status_checker` | Look up upcoming appointments by phone number | Conditional |
| `notification_agent` | Send confirmation via WhatsApp / SMS / email | No |
| `escalation_agent` | Alert business owner, log for human follow-up | No |

### Pre-built Templates (one-click activation)

| Template | Agents | Use Case |
|---|---|---|
| **Full Booking Suite** | All 7 agents | Clinics, salons — full lifecycle |
| **Booking Only** | Classifier + Booking + Notify | Simple single-service businesses |
| **Info & Status** | Classifier + Status + Escalation | Read-only — let customers check bookings |

### Graph Versioning

Every graph change creates a new version row. Deploy any previous version in one click — full rollback support. Compiled graphs are cached in Redis to avoid recompilation per message.

---

## Database Schema

8 tables — all scoped to `tenant_id`:

| Table | Purpose |
|---|---|
| `tenants` | Business profile, plan, config (JSONB for hours/settings) |
| `staff` | Staff members with per-day working hours (JSONB) |
| `services` | Rate card — name, price (paise), duration, buffer, category, staff_ids |
| `appointments` | All bookings — soft-delete only, full history |
| `graphs` | Agent graph records with deployed version pointer |
| `graph_versions` | Immutable version snapshots — never updated, only appended |
| `notification_logs` | Every outbound message with delivery status |
| `billing_events` | Metered usage events for Stripe reporting |

---

## Build Phases

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Core backend, LangGraph agent pipeline, tenant portal (login, dashboard, appointments, AI chat, agent setup) | ✅ Complete |
| **Phase 2** | Services rate card, staff CRUD + working hours editor, slot availability API, calendar with slot checker | ✅ Complete |
| **Phase 3** | WhatsApp webhook, SMS webhook, voice/IVR, embeddable web chat widget, inbound channel routing | 🔲 Planned |
| **Phase 4** | Public website, self-service onboarding wizard, login credential generation, Stripe checkout | 🔲 Planned |
| **Phase 5** | Super admin portal — LLM usage tracking, per-tenant cost dashboard, revenue metrics | 🔲 Planned |

---

## Demo

Two demo tenants are seeded out of the box:

| Tenant | Subdomain | Type | Highlights |
|---|---|---|---|
| MedCare Clinic | `medcare` | Medical | Dual OPD sessions (morning + evening), 3 doctors, 7 services |
| Gloss & Glow Salon | `glossglow` | Beauty Salon | 4 categories (Hair, Skin, Nails, Bridal), 3 stylists, 14 services |

After running `python scripts/seed_loader.py`, visit http://localhost:8000 and click either tenant card to log in — no password needed in development mode.

---

## Docker

```bash
# Start backend + Celery worker + beat (uses cloud DB and Redis from .env)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

No local PostgreSQL or Redis containers — both are cloud-hosted (Supabase + Upstash).

---

## License

MIT — see [LICENSE](LICENSE)
