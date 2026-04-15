# Running the System — Complete Guide

## Quick Start (You just ran this!)

### Backend Status ✅

```bash
Backend running on: http://localhost:8000
Health check: http://localhost:8000/api/v1/health
API docs: http://localhost:8000/docs
```

The backend is **already running** with auto-reload enabled. Any Python file changes in `backend/` will trigger automatic reload.

---

## Access the System

### 1. Frontend (Tenant Portal)
**URL:** http://localhost:8000

**Demo Login:**
Click either tenant card to log in — no password needed in dev mode:
- **MedCare Clinic** (medical clinic, dual OPD sessions)
- **Gloss & Glow Salon** (beauty salon, 4 service categories)

Each login automatically issues a JWT token and shows their dashboard.

### 2. API Endpoints
**Base URL:** http://localhost:8000/api/v1

**Key Endpoints:**
```
GET    /health                           # System health
POST   /auth/register                    # Create tenant
GET    /auth/demo-token?subdomain=...    # Dev: issue demo JWT

# Protected routes (require Authorization: Bearer <token>)
GET    /appointments                     # List bookings
GET    /staff                            # List staff
GET    /services                         # Rate card
GET    /slots?date=YYYY-MM-DD&service_id=...
GET    /graphs                           # Agent graphs
POST   /graphs                           # Create graph
POST   /graphs/{id}/deploy               # Deploy version
POST   /chat/{graph_id}                  # Chat with agent
GET    /channels                         # Configured SMS/WhatsApp/Email
POST   /channels                         # Configure channel
POST   /webhooks/twilio/sms              # Inbound SMS
POST   /webhooks/twilio/whatsapp         # Inbound WhatsApp
```

### 3. Interactive API Documentation
**URL:** http://localhost:8000/docs

This is Swagger UI — try requests directly:
1. Click "Authorize" → paste a demo JWT
2. Expand any endpoint → "Try it out" → "Execute"

---

## File Structure at Runtime

```
AI_Appointment_Agent_Platform/
├── backend/
│   ├── main.py                 ← Entry point (serves frontend + API)
│   ├── core/
│   │   ├── config.py           ← Settings from .env
│   │   ├── database.py         ← AsyncSession factory
│   │   └── security.py         ← JWT verification
│   ├── models/                 ← SQLAlchemy ORM (10 tables)
│   ├── api/                    ← Route handlers
│   ├── agents/                 ← LangGraph agent implementations
│   ├── graph/
│   │   ├── builder.py          ← JSON → LangGraph compiler
│   │   ├── executor.py         ← Graph execution engine
│   │   └── registry.py         ← Agent type → class mapping
│   ├── services/               ← Business logic
│   └── workers/                ← Celery background tasks
├── frontend/
│   └── index.html              ← Single-file SPA (served at /)
├── migrations/
│   └── versions/               ← Alembic migration history
├── .env                        ← Secrets (never commit!)
└── requirements.txt            ← Python dependencies
```

---

## Testing the Flow End-to-End

### Scenario 1: Manual Booking via API

**Step 1: Get your JWT**
```bash
curl http://localhost:8000/api/v1/auth/demo-token?subdomain=medcare
# Returns: {"success": true, "data": {"token": "eyJ..."}}
```

**Step 2: Create appointment**
```bash
curl -X POST http://localhost:8000/api/v1/appointments \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "<service-uuid>",
    "staff_id": "<staff-uuid>",
    "customer_name": "John",
    "customer_phone": "+919876543210",
    "appointment_datetime": "2026-04-20T15:00:00Z"
  }'
```

**Step 3: Check response**
```json
{
  "success": true,
  "data": {
    "id": "...",
    "appointment_datetime": "2026-04-20T15:00:00Z",
    "status": "confirmed"
  }
}
```

### Scenario 2: Chat with Agent

**Step 1: Get graph ID**
```bash
curl http://localhost:8000/api/v1/graphs \
  -H "Authorization: Bearer <TOKEN>"
# Returns list of deployed graphs
```

**Step 2: Send message**
```bash
curl -X POST http://localhost:8000/api/v1/chat/<GRAPH_ID> \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can I book an appointment with a haircut tomorrow at 3 PM?",
    "session_id": "user-123"
  }'
```

**Step 3: Agent responds**
```json
{
  "success": true,
  "data": {
    "response": "I found a haircut slot tomorrow at 3:00 PM with Priya. Shall I confirm?",
    "state": {
      "intent": "book",
      "service_id": "...",
      "staff_id": "...",
      "appointment_id": "..."
    }
  }
}
```

### Scenario 3: Configure SMS Channel

**Step 1: POST channel config**
```bash
curl -X POST http://localhost:8000/api/v1/channels \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_type": "sms",
    "credentials": {
      "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "auth_token": "your_token",
      "phone_number": "+1234567890"
    }
  }'
```

**Step 2: API validates, saves, returns status**
```json
{
  "success": true,
  "data": {
    "id": "...",
    "channel_type": "sms",
    "is_active": true,
    "is_verified": true
  }
}
```

---

## Frontend Tour

### Dashboard
- **What:** Overview of your appointment activity
- **Shows:** Total appointments, AI agent status, recent bookings, quick action buttons

### Appointments
- **What:** Full list of all bookings (paginated, filterable by staff/status)
- **Actions:** View details, update status (pending → confirmed → completed), soft-cancel

### Staff
- **What:** Team members and their working hours
- **Actions:** Add staff, edit working hours (multi-session per day), deactivate

### Services
- **What:** Rate card — services grouped by category with prices and assigned staff
- **Actions:** Add service, edit price/duration/category, deactivate
- **Note:** Prices stored as integer paise (₹ × 100) for precision

### Calendar
- **What:** Monthly grid with color-coded appointment dots
- **Features:** 
  - Click a day to see all appointments
  - Slot Checker: select service/staff/date to see available time slots
  - Booked slots marked as "taken", available slots marked as "available"

### Agent Setup
- **What:** Activate a pre-built agent template
- **Templates:**
  - Full Booking Suite (7 agents: classify → book/reschedule/cancel/check → notify)
  - Booking Only (3 agents: classify → book → notify)
  - Info & Status (2 agents: classify → status check)
- **How:** Click card → "Activate" → API creates graph → deploys → badge turns "Live"
- **Auto-discovery:** When you log in, if a deployed graph exists, it's auto-selected for chat

### Channels
- **What:** Configure SMS/WhatsApp/Email for inbound messages
- **Status Badges:** Active ✓, Saved (unverified), Not configured
- **Modal Form:** Enter Twilio credentials (SMS/WhatsApp) or Gmail credentials (email)
- **Validation:** Before saving, backend tests connection (Twilio API call or SMTP login)

### AI Chat Agent
- **What:** Live chat with your activated agent
- **How:** Type a message → agent classifies intent → routes to appropriate agent → replies
- **Requires:** Deployed graph (set up on Agent Setup page first)
- **Banner:** Shows if agent is active or prompts to set up

---

## Understanding the Data Flow

### Appointment Booking Flow

```
Customer clicks "Book" on frontend
    ↓
Frontend opens appointment modal
    ↓
Customer selects service, staff, date, time
    ↓
Frontend calls POST /api/v1/appointments
    ↓
Backend:
  1. Load tenant from JWT
  2. Validate service exists + is_active
  3. Validate staff exists + is_active
  4. Check slot availability (appointment_service.py)
  5. INSERT appointment (status: pending)
  6. Enqueue notification worker (Celery task)
  ↓
Return appointment_id + confirmed_datetime
    ↓
Frontend shows success banner
    ↓
(Async) Celery worker sends SMS/email notification
```

### Agent Chat Flow

```
Customer types message in chat box
    ↓
Frontend calls POST /api/v1/chat/{graph_id}
    ↓
Backend:
  1. Load deployed graph from Redis cache
  2. Create GraphState { tenant_id, session_id, message, ... }
  3. Execute graph:
     a. Intent Classifier node (LLM call to EuriAI)
     b. Route to Book/Reschedule/Cancel/Status agent
     c. Agent executes (DB query + LLM call if needed)
     d. Update state { appointment_id, success, response, ... }
     e. Notification Agent enqueues SMS (if booking succeeded)
  ↓
Return state + response message
    ↓
Frontend renders agent response in chat box
    ↓
(Async) Notifications sent via Celery
```

---

## Logs & Debugging

### View Backend Logs
The backend console shows structured logs:
```
2026-04-15T10:30:45 | INFO  | appointment_created | tenant_id=abc... | appointment_id=xyz...
2026-04-15T10:30:46 | INFO  | agent_execution | graph_id=def... | intent=book | elapsed_ms=2341
2026-04-15T10:30:47 | INFO  | notification_sent | channel=sms | status=sent
```

### API Docs (Interactive)
http://localhost:8000/docs — try endpoints, see responses, learn schema

### Database Inspection
```bash
# Connect to Supabase
# View tables: tenants, appointments, staff, services, graphs, channel_configs, etc.
# All data scoped to your tenant_id
```

---

## Key Database Tables

| Table | Purpose | Rows |
|---|---|---|
| `tenants` | Businesses (clinics, salons) | 2 demo tenants |
| `staff` | Staff members | 7 (MedCare) + 3 (Salon) |
| `services` | Rate card | 10 (MedCare) + 14 (Salon) |
| `appointments` | All bookings (soft-deleted) | 50+ demo appointments |
| `graphs` | Agent graph definitions | 1–2 per tenant |
| `graph_versions` | Immutable version snapshots | 1+ per graph |
| `channel_configs` | SMS/WhatsApp/Email credentials | 0–3 per tenant |
| `notification_logs` | Sent SMS/emails (audit) | Auto-logged |
| `billing_events` | LLM usage for metering | Auto-logged |

---

## Troubleshooting

### Backend won't start
**Error:** `ModuleNotFoundError: No module named 'backend'`
- **Fix:** Run from project root: `cd AI_Appointment_Agent_Platform`

**Error:** `SQLALCHEMY_ASYNCPG_DATABASE_URL` not set
- **Fix:** Copy `.env.example` to `.env` and fill in real values

### Frontend loads but APIs fail
**Error:** 401 Unauthorized
- **Fix:** Not logged in. Click a demo tenant card first.

**Error:** 404 Not Found on POST `/appointments`
- **Fix:** API routes are `/api/v1/appointments`. Check URL.

### Agent doesn't respond
**Error:** "No AI agent activated yet"
- **Fix:** Go to Agent Setup page → click "Activate" on a template

**Error:** Chat returns empty response
- **Fix:** Check backend logs. May be EuriAI API key invalid in `.env`.

### Migrations fail
**Error:** `alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'`
- **Fix:** Ensure all migration files exist in `migrations/versions/`. Run `alembic upgrade head`.

---

## Next Steps

1. **Explore the frontend:** Log in → navigate all pages
2. **Try the chat:** Go to Agent Setup → Activate → Chat page → send message
3. **Test APIs:** Use http://localhost:8000/docs → Authorize → Try endpoints
4. **Read code:** Understand agent implementations in `backend/agents/`
5. **Read docs:** Study `docs/AGENTS_AND_GRAPHS.md` for interview prep

---

## System Readiness Checklist

- ✅ Backend running (http://localhost:8000)
- ✅ Database connected (Supabase)
- ✅ Redis connected (Upstash)
- ✅ Frontend loaded (single-file SPA, auto-served)
- ✅ Migrations applied (9 tables created)
- ✅ Demo data seeded (MedCare Clinic + Gloss & Glow Salon)
- ✅ Phase 3 complete (SMS/WhatsApp/Email channels)
- ✅ Documentation ready (MASTER_GUIDE, AGENTS_AND_GRAPHS, CHANNEL_SETUP)

**You're ready to demo, develop, and interview!**
