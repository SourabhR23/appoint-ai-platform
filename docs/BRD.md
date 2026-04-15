# Business Requirements Document (BRD)
## AI Appointment Agent Platform — Multi-Tenant
**Version:** 1.0  
**Date:** April 2026  
**Prepared by:** Product & Engineering  
**Status:** Draft for Review

---

## 1. Executive Summary

This document defines the business requirements for an AI-powered, multi-tenant appointment management platform. The platform addresses a clear market gap: appointment-driven SMBs in India need affordable, WhatsApp-first, AI-powered scheduling automation — and no such product exists below ₹10,000/month. This platform will be offered as a SaaS product at ₹999–₹5,999/month, generating recurring subscription revenue with a usage-based component.

---

## 2. Business Objectives

| ID | Objective | KPI | Target |
|---|---|---|---|
| BO1 | Reduce manual booking workload for SMBs | Hrs/week saved per tenant | 15+ hours |
| BO2 | Reduce patient no-show rate | % no-show reduction | 30% |
| BO3 | Generate recurring revenue | MRR at 6 months | ₹5L/month |
| BO4 | Capture India SMB market | Paying tenants at 6 months | 200 |
| BO5 | Enable multi-channel booking | Channels supported | 3+ (WhatsApp, SMS, Web) |
| BO6 | Monetize AI agent usage | Avg revenue per tenant/month | ₹2,500 |

---

## 3. Business Context

### Market Opportunity
- 6.3 million SMBs in India use appointment-based service models
- 85% still rely on manual WhatsApp/phone booking
- No-show rates average 25–35% without reminders
- Existing tools (Calendly, Practo) are either too simple or too expensive
- WhatsApp has 500M+ users in India — ideal delivery channel

### Revenue Model

**Subscription Tiers**

| Plan | Monthly Price | Inclusions |
|---|---|---|
| Starter | ₹999/mo | 3 agents, 200 appointments/mo, SMS+Email |
| Growth | ₹2,499/mo | 8 agents, 1,000 appointments/mo, WhatsApp+SMS+Email |
| Pro | ₹5,999/mo | All agents, unlimited appointments, multi-language, calendar sync |
| Enterprise | Custom | White-label, on-premise, SLA, dedicated support |

**Usage-Based Add-Ons**
- WhatsApp messages: ₹0.50/message (pass-through + margin)
- SMS: ₹0.20/SMS
- Overage appointments: ₹2/appointment above plan limit
- Additional staff seats: ₹199/staff member/month

**Revenue Projections**

| Month | Tenants | Avg MRR/Tenant | Total MRR |
|---|---|---|---|
| Month 1 | 10 | ₹1,500 | ₹15,000 |
| Month 3 | 50 | ₹2,000 | ₹1,00,000 |
| Month 6 | 200 | ₹2,500 | ₹5,00,000 |
| Month 12 | 600 | ₹3,000 | ₹18,00,000 |

---

## 4. Stakeholders

| Stakeholder | Role | Interest |
|---|---|---|
| Founding Team | Product + Engineering | Build and ship the product |
| Business Owners (Tenant Admins) | Primary customers | Automate bookings, reduce costs |
| Reception Staff (Tenant Users) | Daily users | Manage appointments easily |
| End Customers/Patients | End users of AI chat | Book and manage appointments easily |
| Investors | Funding | Revenue growth, market size |
| Twilio / SendGrid | Vendors | Notification infrastructure |
| Anthropic / OpenAI | Vendors | LLM API for agents |

---

## 5. Business Requirements

### BR-01: Multi-Tenant Platform
**Priority:** Critical  
**Description:** The platform must support multiple independent business accounts (tenants) with complete data isolation. No tenant should be able to view, access, or affect another tenant's data.  
**Acceptance Criteria:**
- Each tenant has a unique account with their own data, users, and graph
- DB-level isolation using Row-Level Security
- Tenant A cannot access Tenant B's appointments under any condition
- All API endpoints enforce tenant scoping via JWT

### BR-02: Self-Service Onboarding
**Priority:** Critical  
**Description:** Businesses must be able to sign up, configure, and deploy their agent workflow without requiring assistance from the platform team.  
**Acceptance Criteria:**
- Registration to first deployed graph in under 30 minutes
- Guided wizard for business setup (hours, services, staff)
- No credit card required for 14-day trial
- In-app help tooltips on all complex screens

### BR-03: Visual Workflow Builder
**Priority:** Critical  
**Description:** Business owners must be able to design their agent workflow using a drag-and-drop interface — no coding required.  
**Acceptance Criteria:**
- Agents displayed as node cards in a sidebar
- Canvas allows drag, drop, connect, and configure
- Real-time cost estimation as graph is modified
- One-click deploy with validation
- Version history with rollback capability

### BR-04: WhatsApp-First Communication
**Priority:** Critical  
**Description:** WhatsApp must be a supported channel for end-customer interaction, as it is the dominant messaging platform for Indian SMBs.  
**Acceptance Criteria:**
- Tenant connects their WhatsApp Business number via Twilio
- Customers can book, check, and manage appointments over WhatsApp
- Confirmations and reminders sent via WhatsApp
- Interactive buttons (Confirm / Cancel) in WhatsApp messages

### BR-05: Multi-Language Support
**Priority:** High  
**Description:** The platform must support conversations in Hindi and top 4 regional Indian languages to serve non-English-speaking customers.  
**Acceptance Criteria:**
- Language auto-detected from first message
- System responds in detected language throughout session
- Support for: English, Hindi, Marathi, Tamil, Gujarati, Bengali
- Language preference stored per patient for future sessions

### BR-06: Calendar Integration
**Priority:** High  
**Description:** Booked appointments must sync to the business's calendar tools to prevent double-booking with manually managed schedules.  
**Acceptance Criteria:**
- Google Calendar two-way sync supported
- Outlook/MS 365 Calendar supported
- Sync failures do not block appointment confirmation
- Sync conflicts resolved with DB as source of truth

### BR-07: Automated Reminders
**Priority:** High  
**Description:** The system must send automated reminders to reduce no-shows, configurable by the business.  
**Acceptance Criteria:**
- Configurable reminder timing: 24 hours before, 1 hour before (default)
- Tenant can set custom reminder windows and multiple reminders
- Reminder sent on the same channel the patient used to book
- Patient can confirm or cancel directly from reminder message
- No-show detected and logged if patient doesn't arrive

### BR-08: Usage-Based Billing
**Priority:** High  
**Description:** Revenue must be generated via a combination of subscription and usage-based pricing to align platform cost with customer value.  
**Acceptance Criteria:**
- Subscription plans with included usage limits
- Overage tracked and billed at per-unit rate
- Real-time usage meter visible to tenant in dashboard
- Monthly invoice generated and charged via Stripe
- Usage data available for export/reconciliation

### BR-09: Business Analytics Dashboard
**Priority:** Medium  
**Description:** Business owners must be able to see appointment performance metrics to make operational decisions.  
**Acceptance Criteria:**
- Total appointments (day, week, month)
- No-show rate and cancellation rate
- Busiest hours and days (heatmap)
- Revenue attribution by service type
- Channel breakdown (WhatsApp vs web vs SMS)
- Staff utilization rate

### BR-10: Human Escalation Path
**Priority:** Medium  
**Description:** The AI must be able to escalate to a human receptionist when it cannot handle a request, to ensure no customer is left unserved.  
**Acceptance Criteria:**
- Escalation agent triggers on low-confidence intent classification
- Human receives notification (WhatsApp or in-app) with full conversation context
- Human can take over conversation from dashboard
- Customer informed they're being transferred to staff

---

## 6. Functional Requirements Summary

| ID | Feature | Priority | Phase |
|---|---|---|---|
| F01 | Tenant registration & onboarding | Critical | MVP |
| F02 | Drag-drop graph builder | Critical | MVP |
| F03 | Appointment booking via web chat | Critical | MVP |
| F04 | Appointment booking via WhatsApp | Critical | MVP |
| F05 | Slot availability checking | Critical | MVP |
| F06 | Appointment status check | Critical | MVP |
| F07 | Rescheduling via chat | Critical | MVP |
| F08 | Cancellation via chat | Critical | MVP |
| F09 | Email confirmation & reminders | Critical | MVP |
| F10 | SMS confirmation & reminders | Critical | MVP |
| F11 | WhatsApp confirmation & reminders | Critical | MVP |
| F12 | Appointments dashboard | Critical | MVP |
| F13 | Manual appointment management | Critical | MVP |
| F14 | Google Calendar sync | High | Phase 2 |
| F15 | Multi-language support | High | Phase 2 |
| F16 | Voice/IVR agent | High | Phase 2 |
| F17 | Waitlist management | High | Phase 2 |
| F18 | Analytics dashboard | Medium | Phase 2 |
| F19 | Stripe usage billing | High | Phase 2 |
| F20 | No-show detection & alerts | High | Phase 2 |
| F21 | Outlook Calendar sync | Medium | Phase 3 |
| F22 | Instagram DM agent | Medium | Phase 3 |
| F23 | White-label offering | Low | Phase 3 |
| F24 | API access for integrations | Medium | Phase 3 |

---

## 7. Non-Functional Business Requirements

### NFR-01: Data Residency
All customer data (appointments, patient info, conversations) must be stored in India (AWS Mumbai ap-south-1 region) to comply with India's DPDPA 2023.

### NFR-02: Data Privacy
Patient PII (name, phone, health info) must be encrypted at rest. Platform team must not have access to tenant patient data. Tenant admin can export or delete all their data at any time.

### NFR-03: Uptime
Platform must maintain 99.9% uptime (< 8.7 hours downtime/year). Planned maintenance must be notified 48 hours in advance and scheduled outside 8am–10pm IST.

### NFR-04: Support SLA
- Starter plan: 48-hour email support
- Growth plan: 24-hour email + WhatsApp support
- Pro plan: 4-hour response, dedicated account manager
- Critical outages: 1-hour response for all plans

---

## 8. Assumptions

1. Tenants have access to a WhatsApp Business number or can acquire one
2. Patients have WhatsApp installed (500M+ India users — safe assumption)
3. Tenants are willing to pay ₹999–₹5,999/month for demonstrated ROI
4. Initial target market is Tier 1 and Tier 2 Indian cities
5. English is adequate for V1 UI (owners) even if Hindi needed for V1 customers
6. Anthropic/OpenAI API costs can be absorbed within margins at stated pricing

---

## 9. Constraints

1. 2-week MVP development timeline
2. Budget: Bootstrap / lean (no VC funding assumed initially)
3. Twilio WhatsApp requires Meta Business approval (can take 1–2 weeks)
4. LLM API costs must be factored into pricing model
5. Google OAuth requires verified app for production calendar access

---

## 10. Acceptance Criteria for Product Launch

The product is ready to launch when:
- 5 beta tenants have used the system for 2 weeks with no critical bugs
- System handles 100 concurrent chat sessions without degradation
- No cross-tenant data leakage detected in security testing
- WhatsApp booking flow works end-to-end in < 3 seconds response time
- Reminder delivery rate > 95% in testing
- At least 3 tenants confirm they would pay for the product

---

## 11. Approval & Sign-Off

| Role | Name | Date | Sign-off |
|---|---|---|---|
| Product Owner | | April 2026 | Pending |
| Tech Lead | | April 2026 | Pending |
| Business Stakeholder | | April 2026 | Pending |
