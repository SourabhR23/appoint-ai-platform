# AppointAI — Master Project Guide
## AI-Powered Multi-Tenant Appointment Agent Platform

**Version:** 1.0  
**Date:** April 2026  
**Audience:** Engineers, Architects, Product Owners  
**Purpose:** Single source of truth for what this product is, how it is built, and in what order to build it.

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Who Uses This Platform](#2-who-uses-this-platform)
3. [The Four Product Surfaces](#3-the-four-product-surfaces)
4. [AI Agent System — How It Works](#4-ai-agent-system--how-it-works)
5. [Communication Channels](#5-communication-channels)
6. [Architecture Overview](#6-architecture-overview)
7. [Database Design](#7-database-design)
8. [Multi-Tenancy Model](#8-multi-tenancy-model)
9. [Security Model](#9-security-model)
10. [Backend API Reference](#10-backend-api-reference)
11. [Build Phases — What to Build and When](#11-build-phases--what-to-build-and-when)
12. [Technology Stack Decisions](#12-technology-stack-decisions)
13. [Infrastructure and Deployment](#13-infrastructure-and-deployment)
14. [Revenue and Billing Model](#14-revenue-and-billing-model)
15. [Observability and Admin Visibility](#15-observability-and-admin-visibility)

---

## 1. Product Overview

AppointAI is a **multi-tenant SaaS platform** that lets appointment-driven businesses — clinics, salons, physiotherapy centers, coaching institutes, law offices, yoga studios — deploy an AI-powered virtual receptionist without writing a single line of code.

A business visits the platform website, selects which AI capabilities they want, fills in their company details, and within minutes their AI agent is live — answering WhatsApp messages, booking appointments, sending reminders, handling cancellations, and escalating to a human when needed.

The platform operates on three levels:

- **The business owner** sets up and monitors their AI agent through a dashboard.
- **Their customers** interact with the AI agent through WhatsApp, SMS, a web chat widget, or a voice call — whichever channel the business activates.
- **The platform owner (you)** monitors all tenants, their AI usage, LLM costs, active agent graphs, and revenue — without ever seeing any tenant's customer data.

### Core Value Proposition

| Problem | Solution |
|---|---|
| Staff spend 3–4 hours/day on manual WhatsApp bookings | AI handles all inbound booking requests 24/7 |
| 25–35% no-show rate from no follow-ups | Automated reminders via WhatsApp + SMS + Email |
| Businesses can't afford enterprise scheduling tools | ₹999–₹5,999/month tier pricing |
| Setup requires IT teams | Zero-code onboarding wizard — live in under 30 minutes |
| One tool per channel (WhatsApp, SMS, web) | Single platform, all channels unified |

---

## 2. Who Uses This Platform

### Persona 1 — Business Owner / Admin
The owner of a clinic, salon, or similar business. Not technical. Uses the **Tenant Portal** to see appointment activity, configure their AI agent, manage staff and services, and connect their WhatsApp number. Their primary goal: never have to manually respond to a booking message again.

### Persona 2 — Business Staff / Receptionist
Uses the appointment list inside the **Tenant Portal** to see today's schedule, override or manually add an appointment, and see notes from the AI agent. Does not configure anything — just reads and acts on data.

### Persona 3 — End Customer / Patient
Never touches any portal. Sends a WhatsApp message to the business's number, types on a web chat widget on the business's own website, receives an SMS, or calls a phone number. Interacts only with the AI agent. May speak in Hindi, Tamil, English, or other regional languages.

### Persona 4 — Platform Super Admin (You)
Has a completely separate **Admin Portal** that shows all tenants, their LLM token usage, agent graph activity, revenue, error rates, and system health. Cannot see any tenant's appointment data, customer names, or messages. The view is purely operational and financial.

---

## 3. The Four Product Surfaces

The platform consists of four entirely separate frontends. Each serves a different audience and has its own routes, authentication, and design purpose.

---

### Surface 1 — Public Website (Marketing + Acquisition)

**Who sees it:** Any business owner browsing the internet.  
**Purpose:** Explain the product, show pricing, and funnel visitors into the onboarding wizard.  
**Authentication:** None — fully public.

#### Pages

**Landing Page**  
Hero section explaining the product in one sentence. A short animated demo of the AI agent handling a WhatsApp booking. Three feature blocks: 24/7 AI Booking, Multi-Channel (WhatsApp, SMS, Web), and No-Code Setup. Social proof: sample businesses, appointment counts handled. Primary CTA: "Start Free Trial".

**Pricing Page**  
Three plan cards — Starter (₹999/mo), Growth (₹2,499/mo), Pro (₹5,999/mo). Feature comparison table. FAQ. CTA on each card goes to the onboarding wizard with plan pre-selected.

**How It Works Page**  
Step-by-step visual: visit site → select agents → fill business info → go live. Animated flowchart showing a patient WhatsApp message flowing through the agent pipeline into a confirmed booking.

**Use Case Pages**  
Dedicated pages for clinics, salons, coaching centers — each showing the agent setup relevant to that business type, sample conversations, and results.

---

### Surface 2 — Onboarding Wizard (Self-Service Registration)

**Who uses it:** A new business signing up for the first time.  
**Purpose:** Collect all information needed to configure the platform for this tenant and get them live.  
**Authentication:** None until the account is created at the end.

This is a multi-step form wizard. No code, no technical knowledge needed. Each step is saved progressively so the business can resume if they leave.

#### Step 1 — Business Type Selection
A visual card selection: Clinic / Hospital, Beauty Salon / Spa, Physiotherapy, Coaching / Tuition, Yoga / Fitness, Consultancy, Other. This choice pre-populates default services, working hours, and agent templates in the next steps.

#### Step 2 — Agent Template Selection
Based on the business type, 2–3 recommended agent configurations are shown as visual cards. Each card shows which agents are included (Intent Classifier → Booking → Notification, for example), what the agent can and cannot do, and the estimated monthly message volume it handles. The business selects one. Advanced users can customize later from the Tenant Portal.

This step is the conceptual equivalent of choosing a SaaS plan feature set — but expressed in AI capability terms, not pricing terms. Pricing comes later.

#### Step 3 — Company Information
Business name, registered address, timezone, primary language, website URL (optional). This data populates the AI agent's context — the agent will use the business name in its responses.

#### Step 4 — Working Hours
A visual schedule editor. For each day of the week, toggle open/closed and set open/close times. Some business types have multiple sessions (morning OPD 9am–1pm and evening OPD 5pm–8:30pm). The schedule is stored per-tenant and used by the booking agent to validate slot availability.

#### Step 5 — Services Setup
Add the services this business offers. Each service has: name, duration (minutes), price, which staff can perform it, and which department/category it belongs to. Pre-populated defaults are shown based on Step 1 business type. The business edits or adds to this list.

#### Step 6 — Staff Members
Add staff names, specialization, and working hours (can differ from business hours — a physiotherapist might only work Mon/Wed/Fri). Each staff member can optionally connect their Google Calendar later from the portal.

#### Step 7 — Channel Selection
Which communication channels to activate:
- **Web Chat Widget** — embeds on the business's own website. No phone number needed.
- **WhatsApp** — link a Twilio WhatsApp-enabled number to this tenant.
- **SMS** — link a Twilio SMS number.
- **Voice / IVR** — link a Twilio phone number for voice calls.

The business selects the channels they want. Each channel can be enabled independently and configured separately.

#### Step 8 — Plan and Payment
Show the three pricing tiers. The recommended plan is highlighted based on the services count and channels selected. Stripe Checkout integration. On successful payment, the account is created.

#### Step 9 — Account Created (Flashcard)
A visually prominent card displayed on screen and sent by email:
- Business portal login URL (e.g., `yourplatform.com/login`)
- Subdomain assigned (e.g., `medcare.appointai.in`)
- Email address used
- Temporary password (prompted to change on first login)
- API key for direct integration (for tech-savvy tenants)
- QR code for the web chat widget (if selected)
- WhatsApp number assigned (if selected)

The business bookmarks this page and shares it with staff who need portal access.

---

### Surface 3 — Tenant Portal (Business Dashboard)

**Who uses it:** The business owner and their staff.  
**Purpose:** Full visibility into appointment activity, manage business configuration, monitor AI agent performance, and control all settings.  
**Authentication:** JWT-based login via Supabase Auth.

#### Dashboard
At-a-glance view of today's appointment count, confirmed vs pending vs cancelled, yesterday's comparison, this week's revenue estimate. AI agent status badge (Active / Paused / Not configured). Quick-action buttons: Add Appointment, View Today's Schedule, Open Chat Agent.

#### Appointments
Full paginated list of all appointments with filters for date range, status, channel, staff member, and service. Each row shows patient name, phone, service, staff assigned, slot time, channel used (WhatsApp icon / SMS icon / web icon), and status badge. Inline actions: Confirm, Reschedule, Cancel, Add Note. Manual appointment creation form for walk-ins or phone calls taken by staff.

#### Staff Management
Cards for each staff member showing name, specialization, active/inactive status, which days they work, and whether their Google Calendar is connected. Add new staff form. Edit working hours. Deactivate (soft delete). Assign services each staff can perform.

#### Services Management
Table of all services with name, category/department, duration, price. Add, edit, and deactivate services. Assign staff members who can perform each service. Services feed directly into the AI booking agent's knowledge — it will only offer slots for services that exist here.

#### Working Hours
Visual weekly schedule editor. Set open/close times per day. Add session breaks (e.g., lunch 1–5pm). Override holidays or special closure dates. Changes take effect immediately for the booking agent.

#### AI Agent Setup
Visual display of the active agent graph. Shows which agents are connected, the routing logic, and the version deployed. Button to change template or customize. Version history — see every saved version with timestamp. Deploy a previous version (rollback). Agent activity log — see every conversation the AI handled, its intent classification, what action it took, and the outcome.

#### Channels
One tab per channel type:
- **Web Chat Widget**: Copy embed code. Preview the widget. Customize widget color, greeting message, avatar.
- **WhatsApp**: Shows connected number. Test button sends a test WhatsApp to a number you specify. Message template status (Meta approved templates for notifications).
- **SMS**: Shows connected number. Test button.
- **Voice**: Shows connected number. Configure IVR greeting text.
- **API Access**: Shows the tenant's API key. Rotate key option. Documentation link.

#### Notifications and Templates
Edit the message templates the AI agent sends after a booking, reminder, cancellation, or escalation. Separate templates per channel (WhatsApp template format differs from SMS). Supports variables like `{{patient_name}}`, `{{service_name}}`, `{{slot_time}}`, `{{business_name}}`.

#### Billing and Usage
Current plan, next billing date, usage this month (appointments handled, messages sent, LLM calls). Usage bar against plan limits. Upgrade/downgrade plan. Invoice history. Add-on purchases (extra SMS credits, additional staff seats).

#### Settings
Business name, logo upload, timezone, primary language, contact email, notification email for escalations. Change password. Manage team members (invite staff to portal, assign roles: Admin / Staff).

---

### Surface 4 — Super Admin Portal (Platform Owner View)

**Who uses it:** You — the platform owner.  
**Purpose:** Operational and financial visibility across all tenants. Never sees any tenant's customer data.  
**Authentication:** Separate admin credentials, separate login URL, MFA enforced.

#### Tenant Overview
Paginated list of all tenants with: business name, plan, signup date, last active, status (trial / active / churned / suspended). Search and filter. Click any tenant to see their profile.

#### Tenant Detail (No Customer Data)
For a selected tenant: their plan, channels activated, active agent graph name and version, this month's appointment count (number only — no names), LLM tokens used this month, estimated cost to platform for this tenant, Stripe subscription status, last login.

#### LLM Usage Dashboard
Per-tenant breakdown of input tokens + output tokens + total cost (using the LLM provider's per-token pricing). Date range filter. Identifies which tenants are high-cost relative to their plan — these are candidates for plan upgrade prompts.

#### Agent Activity
Across all tenants: total conversations today / this week / this month. Intent distribution chart (how many were book vs reschedule vs cancel vs check vs escalate). Fallback / escalation rate. Average response time. These are aggregate numbers — no individual conversation content.

#### Revenue Dashboard
MRR by plan tier. New signups this week. Churn count this month. Trial-to-paid conversion rate. Stripe webhook events log.

#### System Health
API error rate, P50/P95 response latency, Redis cache hit rate, Celery queue depth, DB connection pool usage. Alert log for any 5xx spikes.

---

## 4. AI Agent System — How It Works

The AI agent system is the technical core of the platform. Every tenant gets their own isolated agent graph that processes inbound messages and takes actions.

### Concept: Agent Graph

An agent graph is a directed state machine. Each node is a specialized AI agent. Each edge is a routing rule. When a message arrives, it flows through the graph:

```
Inbound Message
      ↓
Intent Classifier (LLM call — what does the user want?)
      ↓
   [branch by intent]
      ├── book       → Booking Agent → Notification Agent → END
      ├── reschedule → Reschedule Agent → Notification Agent → END
      ├── cancel     → Cancellation Agent → Notification Agent → END
      ├── check      → Status Checker → END
      └── other      → Escalation Agent → END
```

The graph is defined by the tenant in the Agent Setup section. It is saved as a versioned JSON definition in the database and compiled into a LangGraph `StateGraph` at runtime. Compiled graphs are cached in Redis so they do not need recompilation on every message.

### The Agents

**Intent Classifier Agent**  
Every message enters here first. Makes a single LLM call to classify the user's intent into one of: `book`, `reschedule`, `cancel`, `check`, `other`. Uses a tightly scoped prompt with few-shot examples. Returns a structured output with `intent` and `confidence`. Cost weight: 0.5 (cheap — small prompt, fast).

**Booking Agent**  
Receives a `book` intent. Extracts service name, preferred date, preferred time, and patient name from the conversation using an LLM call. Queries the database for available slots (staff availability + working hours + existing appointments). If a slot is available, creates the appointment row. If not, suggests the nearest alternatives. Returns a confirmation message or an alternatives message. Cost weight: 1.5.

**Reschedule Agent**  
Receives a `reschedule` intent. Identifies the existing appointment by phone number or reference. Asks for new preferred time. Checks slot availability. Updates the appointment row. Returns confirmation. Cost weight: 1.5.

**Cancellation Agent**  
Receives a `cancel` intent. Identifies the appointment. Soft-cancels it (sets `status = cancelled`, does not delete). Returns confirmation. Cost weight: 1.0.

**Status Checker Agent**  
Receives a `check` intent. Looks up appointments for the incoming phone number. Returns a formatted list of upcoming appointments, their status, and their times. No LLM call needed for simple lookups — only if the query is ambiguous. Cost weight: 0.5.

**Notification Agent**  
Triggered after Booking, Reschedule, or Cancellation. Reads the tenant's notification template for the relevant event and channel. Fills in variables (`patient_name`, `slot_time`, `service_name`, `business_name`). Sends via the appropriate channel: Twilio WhatsApp, Twilio SMS, or SendGrid Email. Logs the notification in `notification_logs`. Cost weight: 1.0.

**Escalation Agent**  
Triggered on `other` intent or when any upstream agent fails after retries. Sends an alert to the business owner's configured escalation email/phone. Logs the conversation for human review. Returns a friendly message to the customer: "Our team will get back to you shortly." Cost weight: 0.5.

### State Object

Every agent reads from and writes to a shared `GraphState` dictionary:

```python
class GraphState(TypedDict):
    tenant_id: str
    session_id: str
    channel: str                   # webchat | whatsapp | sms | voice
    sender_identifier: str         # phone number or session UUID
    messages: list[dict]           # full conversation history
    intent: str                    # set by IntentClassifier
    extracted_entities: dict       # service, date, time, patient_name
    appointment_id: str            # set after booking/reschedule
    response: str                  # final reply to send to user
    error: str                     # set if any agent fails
    next_action: str               # used for multi-turn flows
```

### Versioning

Every change to a graph creates a new version row in `graph_versions`. The active version is tracked on the `graphs` row. Deploying sets `is_active = True` on a specific version. The previous version is preserved and can be reactivated (rollback). This means a tenant can safely experiment with graph changes without losing their working configuration.

---

## 5. Communication Channels

Each channel is independent. A tenant activates only the channels they want. All channels funnel into the same agent graph — the graph does not care which channel a message came from, only the `channel` field in the state object differs.

### Web Chat Widget

A JavaScript snippet that the tenant pastes into their own website's HTML. The widget opens a chat bubble in the corner. Messages are sent to the platform API via `POST /api/v1/chat/{graph_id}` with `channel: webchat`. The widget stores the session ID in localStorage to maintain conversation continuity across page reloads. CORS is configured to allow the tenant's domain.

### WhatsApp (via Twilio)

A Twilio WhatsApp number is assigned to each tenant. When a customer sends a WhatsApp message to that number, Twilio sends a webhook POST to `POST /api/v1/webhooks/whatsapp`. The platform resolves which tenant owns that number using the `channel_numbers` table, then routes the message through the tenant's agent graph. Responses are sent back via the Twilio WhatsApp API.

Meta requires pre-approved message templates for business-initiated WhatsApp messages (e.g., reminders). Customer-initiated messages allow free-form replies within a 24-hour window. The Notification Agent handles this distinction automatically.

### SMS (via Twilio)

Same architecture as WhatsApp. A different Twilio number per tenant. Webhook at `POST /api/v1/webhooks/sms`. No template restriction for SMS — plain text replies. Useful for markets where WhatsApp adoption is lower or for reminder fallback when WhatsApp delivery fails.

### Voice / IVR (via Twilio)

A Twilio phone number per tenant. When a customer calls, Twilio sends a webhook to `POST /api/v1/webhooks/voice`. The platform responds with TwiML (Twilio Markup Language) that plays an IVR greeting and prompts the caller to speak their request. Twilio Speech-to-Text transcribes the speech, which is then processed by the agent graph exactly like a text message. The agent's text response is converted back to speech via Twilio's text-to-speech and played to the caller.

### Direct API Access

A tenant can call `POST /api/v1/chat/{graph_id}` directly with their API key. This enables integration with their own website, mobile app, or any custom surface. The API key is shown in the Channels section of the Tenant Portal.

---

## 6. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│  Public Website │ Onboarding Wizard │ Tenant Portal │ Admin │
└─────────────┬───────────────────────────────────────────────┘
              │ HTTPS
┌─────────────▼───────────────────────────────────────────────┐
│                    FASTAPI BACKEND                          │
│                                                             │
│  /api/v1/auth      /api/v1/graphs     /api/v1/chat         │
│  /api/v1/tenants   /api/v1/staff      /api/v1/webhooks     │
│  /api/v1/appointments               /api/v1/admin          │
│  /api/v1/services  /api/v1/billing   /api/v1/metrics       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Services   │  │  LangGraph   │  │  Celery Workers  │  │
│  │  (Twilio,    │  │  Agent Engine│  │  (Reminders,     │  │
│  │  SendGrid,   │  │  (builder +  │  │  Notifications,  │  │
│  │  Stripe,     │  │  executor +  │  │  Retry, Usage    │  │
│  │  Google Cal) │  │  registry)   │  │  Aggregation)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└───────┬─────────────────────┬─────────────────────┬────────┘
        │                     │                     │
┌───────▼──────┐   ┌──────────▼──────┐   ┌─────────▼──────┐
│  PostgreSQL  │   │     Redis        │   │  External APIs  │
│  (Supabase)  │   │   (Upstash)      │   │  Twilio         │
│              │   │                  │   │  SendGrid       │
│  All tenant  │   │  Graph cache     │   │  Stripe         │
│  data with   │   │  Session state   │   │  Google Calendar│
│  tenant_id   │   │  Rate limiting   │   │  EuriAI (LLM)  │
│  scoping     │   │  Celery broker   │   └────────────────┘
└──────────────┘   └──────────────────┘
```

### Request Lifecycle (Inbound WhatsApp Message)

1. Customer sends WhatsApp message to `+91-XXXX-XXXXXX`
2. Twilio receives it and POSTs to `https://yourplatform.com/api/v1/webhooks/whatsapp`
3. Backend resolves tenant from phone number via `channel_numbers` table
4. Loads the tenant's deployed graph from Redis cache (or DB + recompile if cache miss)
5. Constructs `GraphState` with tenant context and message
6. LangGraph executor runs the state machine — agents execute sequentially
7. Final `response` string is extracted from state
8. Backend calls Twilio API to send the reply WhatsApp message
9. All events (intent, agent chain, token usage) logged to DB and Redis

### Request Lifecycle (Tenant Portal API Call)

1. Frontend sends `Authorization: Bearer <JWT>` with every request
2. `get_current_tenant` dependency extracts `tenant_id` from JWT claims
3. All repository queries are scoped: `WHERE tenant_id = :tenant_id`
4. Response returned as `{ success: bool, data: any, error: string | null }`

---

## 7. Database Design

All tables have `id` (UUID), `tenant_id` (UUID), `created_at`, `updated_at`. Soft deletes use `deleted_at` (nullable timestamp). No hard deletes for any customer-facing data.

### Core Tables

**tenants** — One row per business. Stores name, subdomain, email, plan, working hours config (JSONB), `onboarding_completed` flag, `trial_ends_at`, Stripe customer ID.

**staff** — One row per staff member. Belongs to a tenant. Stores name, specialization, working hours override (JSONB, overrides tenant-level hours), `is_active`, `calendar_token` (encrypted, for Google Calendar sync).

**services** — One row per service offered by a tenant. Stores name, category, duration in minutes, price, which staff can perform it (JSONB array of staff IDs), `is_active`.

**appointments** — The central operational table. One row per booking. Stores `patient_name`, `patient_phone`, `patient_email`, `service_id`, `staff_id`, `slot_datetime`, `status` (pending / confirmed / completed / cancelled / no_show), `channel` (whatsapp / sms / webchat / voice / manual), `notes` (JSONB for AI-extracted context), `cancelled_at`, `cancellation_reason`.

**channel_numbers** — Maps a Twilio phone number or WhatsApp number to a `tenant_id`. When an inbound message arrives, this table is queried to find the right tenant.

**graphs** — One row per agent graph. Stores `name`, `active_version` (int), `is_deployed` (bool). Each tenant can have multiple graphs (e.g., one for bookings, one for a chatbot FAQ), but only one deployed at a time per channel.

**graph_versions** — One row per save operation. Stores the full `definition` (JSONB: nodes and edges), `version` int, `is_active` bool, `compiled_at`. Never deleted — complete history preserved.

**notification_logs** — One row per notification sent. Stores `appointment_id`, `channel`, `status` (sent / failed / delivered), `message_sid` (Twilio SID), `error_message`.

**billing_events** — One row per metered event. Stores `event_type` (appointment_handled / llm_call / sms_sent / whatsapp_sent), `units` (tokens for LLM, 1 for appointments), `cost_usd`. Aggregated monthly for Stripe usage reporting.

**llm_usage_logs** — One row per LLM API call. Stores `tenant_id`, `graph_id`, `agent_type`, `input_tokens`, `output_tokens`, `model`, `latency_ms`, `cost_usd`. This is the source for the Super Admin's LLM usage dashboard and for tenant billing.

---

## 8. Multi-Tenancy Model

Every piece of data in the system belongs to exactly one tenant. Isolation is enforced at two levels:

**API Layer:** Every protected route extracts `tenant_id` from the JWT token. The token is issued by Supabase Auth and contains `tenant_id` as a custom claim. `tenant_id` is never read from the request body — only from the verified JWT. All repository functions take `tenant_id` as a required parameter and include it in every `WHERE` clause.

**Database Layer:** Row-Level Security (RLS) policies on Supabase enforce that a database connection associated with a tenant JWT can only read rows where `tenant_id` matches. Even if the API layer had a bug, the database would reject the query.

**Agent Isolation:** Each tenant's agent graph is compiled and cached separately in Redis under a key scoped to `{graph_id}:{version}`. No graph state is shared between tenants. The `GraphState` always carries `tenant_id` and every agent validates it before performing any DB operation.

**Channel Isolation:** Each Twilio number is assigned to exactly one tenant. Inbound webhook routing uses the phone number → tenant mapping before any processing begins. A message to the wrong tenant's number is impossible by design.

---

## 9. Security Model

### Authentication
Supabase Auth issues JWTs signed with the `SUPABASE_JWT_SECRET`. The backend verifies every token on every protected request. Tokens expire in 1 hour. Refresh tokens are handled client-side by the Supabase SDK.

A `demo-token` endpoint exists for development only. It is blocked in production (`is_production` check). It issues a signed JWT for a seeded demo tenant, allowing testing without Supabase credentials.

### Authorization
Three roles exist in the JWT claims:
- `admin` — full access to their tenant's data
- `staff` — read access to appointments and schedule, limited write
- `platform_admin` — access to the Super Admin Portal only, no access to any tenant data routes

### Input Validation
All request bodies are validated by Pydantic models before reaching any service or repository. Invalid input returns a `400` with a structured error response. No raw exception messages are ever returned to the client in production.

### Secrets
All secrets (API keys, JWT secrets, database passwords) are environment variables. Never hardcoded. Never logged. The `.env` file is gitignored. `.env.example` documents every required variable with placeholder values.

### Prompt Injection Resistance
The Booking Agent and other LLM-calling agents use structured output parsing — the LLM must return a predefined schema, not free text. The agent prompt does not include raw user message text in a way that could override instructions. User messages are passed as a separate `user` role message in the conversation history, not interpolated into the system prompt.

---

## 10. Backend API Reference

All routes are under `/api/v1/`. All protected routes require `Authorization: Bearer <token>`. All responses use the envelope: `{ "success": bool, "data": any, "error": string | null }`.

| Method | Route | Auth | Purpose |
|---|---|---|---|
| POST | /auth/register | Public | Create tenant account |
| POST | /auth/login | Public | Exchange credentials for JWT |
| GET | /auth/me | JWT | Get current tenant profile |
| GET | /auth/demo-token | Dev only | Issue demo JWT for testing |
| GET | /appointments | JWT | List appointments (paginated + filtered) |
| POST | /appointments | JWT | Manually create appointment |
| GET | /appointments/{id} | JWT | Get single appointment |
| PUT | /appointments/{id} | JWT | Update status, reschedule |
| DELETE | /appointments/{id} | JWT | Soft-cancel appointment |
| GET | /staff | JWT | List staff |
| POST | /staff | JWT | Add staff member |
| PUT | /staff/{id} | JWT | Update staff |
| DELETE | /staff/{id} | JWT | Deactivate staff |
| GET | /services | JWT | List services |
| POST | /services | JWT | Add service |
| PUT | /services/{id} | JWT | Update service |
| DELETE | /services/{id} | JWT | Deactivate service |
| GET | /graphs | JWT | List tenant graphs |
| POST | /graphs | JWT | Create graph with definition |
| GET | /graphs/{id} | JWT | Get graph |
| PUT | /graphs/{id} | JWT | Save new version |
| POST | /graphs/{id}/deploy | JWT | Deploy version to production |
| GET | /graphs/{id}/versions | JWT | List all versions |
| POST | /chat/{graph_id} | JWT or API Key | Send message through agent |
| POST | /webhooks/whatsapp | Twilio Signature | Inbound WhatsApp message |
| POST | /webhooks/sms | Twilio Signature | Inbound SMS message |
| POST | /webhooks/voice | Twilio Signature | Inbound voice call |
| POST | /billing/webhook | Stripe Signature | Stripe payment events |
| GET | /agents/registry | JWT | List available agent types |
| GET | /admin/tenants | Platform Admin JWT | List all tenants |
| GET | /admin/usage | Platform Admin JWT | LLM + billing usage across tenants |
| GET | /admin/metrics | Platform Admin JWT | System health metrics |
| GET | /health | Public | Service health check |

---

## 11. Build Phases — What to Build and When

The build is organized into five phases. Each phase produces a working, testable, demonstrable increment. No phase requires the next phase to function. Each phase builds directly on the previous one without rework.

---

### Phase 1 — Core Infrastructure and Tenant Portal (Current State)
**Goal:** A fully working tenant dashboard where a seeded tenant can log in, see appointments, and activate an AI agent manually.

**What is included:**
- FastAPI backend with PostgreSQL (Supabase) and Redis (Upstash)
- All database tables via Alembic migrations
- JWT authentication (Supabase + demo-token for development)
- Appointments API (CRUD, pagination, filtering)
- Staff API (read)
- Agent graph API (create, version, deploy)
- LangGraph agent pipeline (Intent Classifier, Booking, Reschedule, Cancel, Status, Notification, Escalation)
- Chat API endpoint
- Tenant portal frontend: login, dashboard, appointments, staff, services placeholder, agent setup with template selection, chat interface
- Seed data for two demo tenants (MedCare Clinic, Gloss & Glow Salon)

**What this phase proves:** The core AI booking loop works end-to-end. A business can see their appointments. The AI agent can be activated with one click.

**Milestone check:** User logs in as MedCare → opens Agent Setup → activates Full Booking Suite → goes to Chat → types "Book an appointment for tomorrow at 10am" → AI responds with available slots.

---

### Phase 2 — Complete Tenant Portal (Missing CRUD and Settings)
**Goal:** The tenant portal covers every operational need. No placeholder sections remain.

**Backend to build:**
- Services API — full CRUD (`POST /services`, `PUT /services/{id}`, `DELETE /services/{id}`)
- Staff write endpoints — add, update, deactivate staff
- Working hours API — read and update business hours per tenant
- Tenant settings API — update business name, timezone, language, escalation email
- Notification templates API — read and update per-event, per-channel templates
- Google Calendar OAuth flow — link/unlink a staff member's calendar

**Frontend to build:**
- Services page — table with Add, Edit, Deactivate. Modal form for service details.
- Staff page — add/edit/deactivate staff. Set per-staff working hours.
- Working hours page — visual weekly schedule editor. Holiday overrides.
- Settings page — business profile form. Notification template editor.
- Channels page — show active channels, embed code for widget, API key display and rotation.
- Billing page — current plan, usage bars, invoice history (Stripe Customer Portal embed).

**Milestone check:** Business owner can add a new service ("Bridal Makeup, 3 hours, ₹8,000"), assign it to a staff member, and the AI booking agent immediately offers it as a bookable option.

---

### Phase 3 — Communication Channels (WhatsApp, SMS, Web Widget, Voice)
**Goal:** Real customers can interact with the AI agent through actual messaging channels, not just the demo chat interface.

**Backend to build:**
- `POST /webhooks/whatsapp` — validate Twilio signature, resolve tenant from number, run agent, reply via Twilio API
- `POST /webhooks/sms` — same pattern as WhatsApp
- `POST /webhooks/voice` — receive Twilio voice webhook, process speech input, return TwiML response
- `channel_numbers` table and management API — assign Twilio numbers to tenants
- CORS policy extension — allow web widget requests from tenant-configured domains
- Rate limiting per channel per tenant
- Twilio number provisioning — either manual assignment via admin panel or automated via Twilio API

**Frontend to build (Tenant Portal — Channels section):**
- WhatsApp tab: show assigned number, test button, Meta template approval status
- SMS tab: show assigned number, test button
- Voice tab: show assigned phone number, configure IVR greeting text
- Web Widget tab: copy embed code (`<script>` tag), customize widget appearance (color, greeting, avatar), live preview

**Infrastructure:**
- Twilio account setup — buy numbers, configure webhook URLs
- WhatsApp Business API approval via Meta (required for production WhatsApp)
- Celery worker for async notification delivery (already partially built)

**Milestone check:** Business owner sends a WhatsApp message to their assigned number from their personal phone → AI responds with a booking confirmation → appointment appears in the portal.

---

### Phase 4 — Onboarding Wizard and Public Website
**Goal:** A new business can discover the platform online, sign up completely self-service, and be live on WhatsApp in under 30 minutes.

**Backend to build:**
- Onboarding wizard API — `POST /onboarding/start`, `PUT /onboarding/{session_id}/step/{n}`, `POST /onboarding/complete`
- The complete endpoint triggers: create tenant row, seed default services from template, create default staff from input, compile and deploy the selected agent graph, provision Twilio number (if selected), create Stripe customer, generate login credentials, send welcome email
- Stripe Checkout session creation — `POST /billing/checkout`
- Stripe webhook handler — `POST /billing/webhook` to handle `checkout.session.completed` and activate the tenant
- Plan enforcement — middleware that checks `trial_ends_at` and blocks API access on expired trials

**Frontend to build:**
- Public landing page — hero, features, pricing overview, testimonials, CTA
- Pricing page — plan comparison table with feature matrix
- Onboarding wizard — 9-step form with progress indicator, live validation, resume capability
- Login page — separate from the demo flashcard login, proper Supabase Auth login form
- Account created confirmation page — the "flashcard" with all credentials

**Milestone check:** A new user visits the site, completes the wizard in under 15 minutes, receives login credentials by email, logs in, and their WhatsApp number is already responding to test messages.

---

### Phase 5 — Super Admin Portal and Observability
**Goal:** You have complete visibility into the platform's operational and financial health across all tenants.

**Backend to build:**
- LLM usage logging — every chat API call records `input_tokens`, `output_tokens`, `model`, `cost_usd` to `llm_usage_logs`
- Billing event aggregation — Celery periodic task that aggregates daily billing events into Stripe usage records for metered billing
- Admin API routes (platform admin JWT only):
  - `GET /admin/tenants` — paginated list with key metrics per tenant
  - `GET /admin/tenants/{id}` — tenant operational profile (no customer data)
  - `GET /admin/usage` — aggregate and per-tenant LLM usage and cost
  - `GET /admin/metrics` — system health (API error rate, latency, queue depth)
  - `GET /admin/revenue` — MRR, churn, conversion from Stripe data
- Tenant suspension API — `PUT /admin/tenants/{id}/status`

**Frontend to build (Super Admin Portal — completely separate app):**
- Admin login page (separate URL, separate credentials, MFA)
- Tenant list with search, filter by plan, activity status
- Tenant detail page — plan, usage, graph info, Stripe status — zero customer data fields
- LLM usage dashboard — per-tenant cost breakdown, total platform cost, cost-per-conversation metric
- Revenue dashboard — MRR chart, new signups, churn
- System health page — API metrics, error log, queue depth
- Agent activity overview — aggregate intent distribution chart across all tenants

**Milestone check:** You can log into the admin portal, see that MedCare Clinic handled 47 conversations this week using 12,400 tokens costing $0.37, is on the Starter plan generating ₹999/month, and has been active for 3 days — without seeing any patient names, phone numbers, or message content.

---

## 12. Technology Stack Decisions

### Why FastAPI (not Django, Flask, Express)
FastAPI's async-first design matches the workload perfectly — most API calls are I/O bound (database queries, LLM calls, Twilio API calls). Django would add ORM complexity that conflicts with the async SQLAlchemy approach. Flask is too minimal for a production multi-tenant system. FastAPI gives automatic OpenAPI docs, Pydantic validation, and dependency injection out of the box.

### Why LangGraph (not plain LangChain or custom state machine)
LangGraph's `StateGraph` maps directly to the concept of an agent workflow: nodes are agents, edges are routing rules, state is passed between agents. It handles conditional routing (intent → agent), retries, and streaming. A plain LangChain sequential chain cannot handle conditional multi-agent routing. A custom state machine would need to replicate what LangGraph already provides.

### Why Supabase (not raw PostgreSQL, MongoDB, Firebase)
Supabase provides managed PostgreSQL with Row-Level Security, Auth (JWT issuance), and the realtime layer — three critical platform needs in one service. MongoDB would require a different query model for a relational dataset (appointments, staff, services are highly relational). Firebase is not well-suited for complex relational queries with multi-tenant isolation.

### Why Upstash Redis (not local Redis, Elasticache)
Upstash provides serverless Redis with TLS and a generous free tier. For a startup-phase platform with variable traffic, paying per-request is better than provisioning a fixed Redis instance. The same Redis serves as LangGraph graph cache, Celery broker, rate limiter, and session store.

### Why EuriAI (OpenAI-compatible endpoint) (not direct OpenAI, not Anthropic)
EuriAI provides an OpenAI-compatible API (`/api/v1/euri`) that wraps multiple models. Using `langchain_openai.ChatOpenAI` with a custom `base_url` means the LLM provider can be swapped by changing one environment variable — no code changes. This gives flexibility to move to OpenAI, Claude, or any other provider at any time.

### Why Twilio (not WhatsApp Cloud API directly, not other providers)
Twilio abstracts WhatsApp, SMS, and Voice behind a single SDK. The webhook format is consistent across channels. Twilio handles number provisioning, delivery receipts, and the Meta approval flow for WhatsApp Business. Building directly on the WhatsApp Cloud API would require separate handling for SMS and Voice.

### Why Stripe (not Razorpay, not PayPal)
Stripe's usage-based billing (metered subscriptions) is essential for billing tenants based on appointment volume and message counts. Stripe's webhook system is reliable and well-documented. Razorpay would be appropriate for India-only deployment but does not support metered usage billing as cleanly.

---

## 13. Infrastructure and Deployment

### Production Architecture

```
CloudFlare (CDN + DDoS)
       ↓
AWS Application Load Balancer
       ↓
ECS Fargate (FastAPI containers, 2+ replicas, auto-scaling)
       ↓
Supabase (PostgreSQL, managed, Asia-Pacific region)
Upstash Redis (TLS, serverless, same region)

Celery Workers: separate ECS task definition, same image
Celery Beat: single ECS scheduled task
```

### Environments

| Environment | Purpose | Database | Redis |
|---|---|---|---|
| development | Local development | Supabase dev project | Upstash dev instance |
| staging | Pre-production testing | Supabase staging project | Upstash staging instance |
| production | Live tenant traffic | Supabase production project | Upstash production instance |

### Environment Variables (Critical)

Every environment-specific value lives in environment variables. The application reads them at startup via `backend/core/config.py` which uses Pydantic `BaseSettings`. Missing required variables cause immediate startup failure — no silent misconfiguration.

Variables are grouped by service: Database, Redis, Supabase Auth, OpenAI/EuriAI, Twilio, SendGrid, Stripe, Google, App config. See `.env.example` for the full list.

### Docker

The backend has a multi-stage Dockerfile: `builder` stage installs dependencies, `runtime` stage copies only the virtualenv. No secrets baked into the image. No running as root. Health check endpoint (`/health`) used by ECS for container health monitoring.

---

## 14. Revenue and Billing Model

### Subscription Plans

| Plan | Price (INR/month) | Agents | Appointments | Channels |
|---|---|---|---|---|
| Starter | ₹999 | 3 agents | 200/month | SMS + Email |
| Growth | ₹2,499 | 8 agents | 1,000/month | WhatsApp + SMS + Email |
| Pro | ₹5,999 | All agents | Unlimited | All channels + Voice |
| Enterprise | Custom | Custom | Unlimited | White-label |

### Usage Add-Ons

- WhatsApp messages: ₹0.50/message (pass-through Twilio cost + margin)
- SMS: ₹0.20/SMS
- Overage appointments: ₹2/appointment above plan limit
- Additional staff seats: ₹199/staff/month

### How Billing Works Technically

Every billable event (appointment handled, LLM call, message sent) is written to the `billing_events` table with `event_type`, `units`, and `cost_usd`. A daily Celery task aggregates these events and reports usage to Stripe's metered billing API for the tenant's subscription. Stripe calculates the invoice at the end of the billing cycle. Webhooks from Stripe update the tenant's plan status in real time.

---

## 15. Observability and Admin Visibility

### What the Platform Owner Can See

Everything listed below is **aggregate or operational data** — no tenant customer data:

- **LLM Usage per Tenant:** Input tokens, output tokens, cost in USD per day/month. Which model was used. Average tokens per conversation.
- **Agent Activity:** Conversations started, intents classified, booking success rate, escalation rate, average response latency.
- **Channel Volume:** Messages received per channel per tenant per day.
- **Revenue:** MRR by plan, new signups, churn events from Stripe.
- **System Health:** API P50/P95/P99 latency, error rate by route, Celery queue depth, Redis memory usage, DB connection pool saturation.

### What the Platform Owner Cannot See

- Patient names, phone numbers, email addresses
- Appointment details (service booked, time, notes)
- Conversation content (the actual messages between agent and customer)
- Staff personal information

This separation is enforced at the API layer — all admin routes aggregate by tenant ID and return counts, not rows. The admin JWT role is checked before every admin route and is explicitly excluded from all tenant data routes.

### Logging

Structured JSON logs in production. Every log entry includes: `timestamp`, `level`, `logger_name`, `request_id`, `tenant_id` (where applicable), and the event message. No patient data, tokens, passwords, or secrets are ever logged. Log retention: 30 days for application logs, 90 days for billing events, indefinite for audit trail.

---

*This document covers the complete product scope. For API schema details see `docs/API_SPEC.md`. For database schema DDL see `docs/DB_SCHEMA.md`. For deployment runbooks see `docs/DEPLOYMENT.md`. For business requirements and revenue model see `docs/BRD.md`. For product feature specifications see `docs/PRD.md`.*
