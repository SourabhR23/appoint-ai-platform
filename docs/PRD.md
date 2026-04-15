# Product Requirements Document (PRD)
## AI Appointment Agent Platform — Multi-Tenant
**Version:** 1.0  
**Date:** April 2026  
**Status:** Draft

---

## 1. Product Vision

Build a **multi-tenant SaaS platform** that allows appointment-driven businesses (clinics, salons, consultancies, coaching centers) to create an AI-powered virtual receptionist by visually assembling agent workflows — with zero coding required. Businesses drag, drop, and connect pre-built AI agents to handle the full appointment lifecycle: booking, confirmation, reminders, rescheduling, and cancellations — across WhatsApp, SMS, email, and web chat.

---

## 2. Problem Statement

Small and medium appointment-driven businesses in India face:
- Manual WhatsApp/phone booking that consumes staff time
- Missed appointments due to no reminder system
- No 24/7 availability for patient/customer queries
- High no-show rates (avg 25–35%) due to poor follow-up
- No affordable alternative below enterprise-grade solutions (₹20k+/month)
- Multi-language barrier — most tools are English only

**Target businesses:** Clinics, physiotherapy centers, salons, spas, coaching institutes, lawyers, consultants, yoga studios, dental offices.

---

## 3. Users & Personas

### Persona 1: Business Owner / Admin (Primary)
- Runs a clinic or salon with 1–10 staff members
- Not technical — needs no-code setup
- Pain: staff spending 3–4 hours/day on manual bookings
- Goal: automated bookings, reduced no-shows, happy customers
- Device: Mobile + Desktop

### Persona 2: Receptionist / Staff
- Uses the dashboard to see and manage appointments
- Needs to override, manually add, or cancel appointments
- Gets alerts for no-shows and urgent escalations

### Persona 3: End Customer / Patient
- Books via WhatsApp, SMS, or web widget
- Wants quick confirmation and reminders
- May speak Hindi, Marathi, Tamil, etc.
- Not technical at all — interacts only via chat/voice

### Persona 4: Platform Super Admin (Internal)
- Manages all tenants
- Monitors usage, billing, issues
- Can impersonate any tenant for support

---

## 4. Core Features

### 4.1 Multi-Tenant Onboarding
- Business self-registers with name, type, phone, email
- Guided setup wizard: business hours, services, staff, channels
- 14-day free trial with 100 agent executions
- Unique subdomain per tenant (e.g., `drpatel.appointai.in`)
- Tenant isolation at DB level (Row-Level Security)

### 4.2 Drag-and-Drop Graph Builder
- Visual canvas (React Flow based)
- Sidebar with agent node cards
- Connect nodes with directional edges
- Configure each node via side panel (services, channels, templates)
- Live cost estimator as graph is built
- Validate graph before deploy (no orphan nodes, valid entry/exit)
- Save, version, and deploy graph with one click
- Roll back to previous graph versions

### 4.3 Agent Library (MVP — 12 Agents)

**Entry Agents (Channel)**
- Web Chat Widget Agent
- WhatsApp Chatbot Agent
- SMS Agent

**Processing Agents**
- Intent Classifier Agent
- Multi-language Agent (Hindi, Tamil, Marathi, Gujarati, Bengali)
- Escalation Agent (human handoff)

**Appointment Agents**
- Appointment Booking Agent
- Slot Availability Checker
- Reschedule Agent
- Cancellation Agent
- Status Checker Agent
- Waitlist Agent

**Output Agents**
- Email Confirmation Agent
- SMS Confirmation Agent
- WhatsApp Confirmation Agent
- Reminder Agent (configurable: 24h, 1h before)
- Follow-up Agent (post-appointment)

### 4.4 Appointment Management Dashboard
- Today's appointments view (card + calendar views)
- Filter by staff, service, status, date range
- Manual appointment add/edit/cancel
- Patient history — previous appointments, no-show rate
- Search by name, phone, service
- Export appointments (CSV)
- Staff schedule view (who has what, when)

### 4.5 Notification System
- Email: booking confirmation, reminder, cancellation
- SMS: same as email (shorter format)
- WhatsApp: same + interactive buttons (Confirm / Cancel)
- Configurable reminder timing per tenant
- Tenant can customize message templates
- Notification delivery logs

### 4.6 Calendar Integration
- Google Calendar: two-way sync
- Outlook Calendar: two-way sync
- Sync is async (non-blocking)
- Tenant controls which staff calendars to sync
- Conflict resolution: DB is source of truth

### 4.7 Multi-Language Support
- Detect language from first user message
- Respond in same language throughout session
- Supported: English, Hindi, Marathi, Tamil, Gujarati, Bengali
- Agent prompts are translated server-side
- Language preference saved per patient

### 4.8 Usage-Based Billing
- Each agent node execution = billable units (per node cost weight)
- SMS/WhatsApp/Email = pass-through cost + platform margin
- Dashboard: live usage meter, projected monthly cost
- Invoice generated monthly via Stripe
- Plans: Starter (₹999/mo), Growth (₹2,499/mo), Pro (₹5,999/mo)
- Overage: ₹0.25 per execution unit beyond plan limit

---

## 5. User Stories

### Business Owner
- As a business owner, I want to drag and connect agents so that I can build my virtual receptionist without writing code
- As a business owner, I want to see estimated monthly cost as I build the graph so that I can manage expenses
- As a business owner, I want to see today's appointments at a glance so that I can plan my staff's day
- As a business owner, I want my customers to receive reminders so that I can reduce no-shows

### End Customer
- As a patient, I want to book an appointment on WhatsApp so that I don't need to call the clinic
- As a patient, I want to reschedule my appointment via chat so that I can change plans without difficulty
- As a patient, I want to receive a reminder before my appointment so that I don't forget
- As a Hindi-speaking patient, I want to communicate in Hindi so that I can book without language barrier

### Receptionist
- As a receptionist, I want to see live appointment updates so that I can manage walk-ins alongside booked patients
- As a receptionist, I want to manually add an appointment so that I can handle phone bookings in the system
- As a receptionist, I want to receive no-show alerts so that I can follow up promptly

---

## 6. Non-Functional Requirements

### Performance
- Chat response time: < 3 seconds (P95)
- Appointment creation API: < 500ms (P95)
- Dashboard page load: < 2 seconds
- Notification delivery: < 30 seconds from trigger

### Scalability
- Support 1,000 tenants on launch
- Support 10,000 concurrent chat sessions
- Handle 50,000 appointment bookings/day at scale
- Horizontal scaling via Docker + ECS

### Availability
- 99.9% uptime SLA
- Zero-downtime deployments
- Automated DB backups every 6 hours
- Redis failover with Sentinel

### Security
- OWASP Top 10 compliance
- JWT with 24hr expiry + refresh tokens
- Row-Level Security on all tenant data
- Encrypted at rest (AES-256)
- TLS 1.3 in transit
- No PII logging
- GDPR and India DPDPA compliant

### Compliance
- Store patient data only in India region (AWS Mumbai)
- Right to erasure — tenant can delete all their data
- Audit log for all appointment changes

---

## 7. MVP Scope (2-Week Build)

**In MVP:**
- Tenant registration + login (Supabase Auth)
- Graph builder with 6 core agents
- Booking + rescheduling via web chat widget
- WhatsApp integration (Twilio)
- Email + SMS confirmation
- Basic appointments dashboard
- Google Calendar sync (one-way)
- English only

**Out of MVP:**
- Voice/IVR agent
- Multi-language
- Outlook sync
- Waitlist agent
- Stripe billing (hardcode free trial)
- Analytics dashboard

---

## 8. Success Metrics

| Metric | Target at 90 days |
|---|---|
| Tenants onboarded | 50 |
| Appointments booked via AI | 5,000 |
| No-show rate reduction | 30% vs baseline |
| Chat-to-booking conversion | > 60% |
| Monthly recurring revenue | ₹1.5L |
| Avg tenant NPS | > 50 |
| P95 chat response time | < 3s |

---

## 9. Out of Scope (V1)

- Voice AI / IVR calling
- Payment collection within chat
- CRM integration (HubSpot, Salesforce)
- Custom AI model training per tenant
- Video consultation booking (future)
- Mobile app for patients (future)
- Marketplace for community agents

---

## 10. Dependencies & Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| WhatsApp API approval delay | Medium | High | Use Twilio sandbox for demo; apply early |
| LLM API rate limits at scale | Low | High | Implement queue + retry; use multiple API keys |
| Google Calendar OAuth complexity | Low | Medium | Use Supabase OAuth flow |
| Multi-language accuracy | Medium | Medium | Test with native speakers before launch |
| Stripe India compliance | Low | Medium | Use Razorpay as fallback |
