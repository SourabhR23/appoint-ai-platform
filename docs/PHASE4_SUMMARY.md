# Phase 4 — Public Website, Auth & Onboarding Wizard

**Status:** Complete  
**Date:** April 2026  
**Commit:** `a7e30fb` → `github.com/SourabhR23/appoint-ai-platform`

---

## What Was Built

Phase 4 transformed the platform from a developer-only demo into a publicly accessible SaaS product. Before Phase 4, the app loaded directly into a dashboard with hardcoded demo cards. After Phase 4:

- A **public landing page** is the entry point
- New businesses can **self-register** via a signup wizard
- Existing tenants log in with **email + password**
- A **super admin portal** (placeholder, fully built out in Phase 5) is accessible via a separate admin login
- A **FitLife Coaching** demo tenant with real credentials demonstrates the credential login flow

---

## Changes by Layer

### Frontend (`frontend/index.html`)

The single-file SPA was restructured from 3 views to 5 views. Old `view-login` (demo cards only) was replaced with:

| View ID | Purpose |
|---|---|
| `view-landing` | Public marketing page — hero, features, how-it-works, demo cards, footer |
| `view-auth` | Combined login + signup screen with tab switcher |
| `view-admin-login` | Separate admin login form |
| `view-admin-dashboard` | Super admin overview (Phase 5 placeholder) |
| `view-app` | Main tenant dashboard (unchanged) |

**New JS functions added:**

| Function | What it does |
|---|---|
| `hideAllViews()` | Hides all 5 view divs |
| `showLanding()` | Shows the public landing page |
| `showAuth(tab)` | Shows auth screen on login or signup tab |
| `showAdminLogin()` | Shows admin login form |
| `showAdminDashboard(email)` | Shows admin dashboard, loads stats |
| `showApp()` | Shows the main tenant app |
| `switchAuthTab(tab)` | Switches login/signup tabs with active styling |
| `doLogin()` | Calls `POST /auth/login`, stores JWT, enters dashboard |
| `loginAs(subdomain)` | Calls `GET /auth/demo-token`, enters dashboard (unchanged behaviour) |
| `doAdminLogin()` | Calls `POST /auth/admin/login`, enters admin dashboard |
| `adminLogout()` | Returns to landing page |
| `loadAdminStats()` | Populates admin stat cards (hardcoded placeholders for Phase 5) |
| `selectTemplate(key)` | Highlights selected agent template card in wizard |
| `swSetStep(n)` | Advances wizard step with progress-bar and dot state |
| `swNext(fromStep)` | Validates current step and advances to next |
| `swBack(fromStep)` | Goes back one step |
| `swSubmit()` | Registers tenant, auto-deploys chosen template, enters dashboard |
| `logout()` | Clears token, returns to landing page (previously returned to demo cards) |
| `updateSidebar()` | Updated to handle all 5 business types: clinic, salon, coaching, consultancy, other |

**Signup wizard — 3 steps:**

1. **Business Info** — name, business type, subdomain, phone, email (validated client-side)
2. **Password** — password + confirm (min 8 chars, match check)
3. **Agent Template** — choose from Full Booking Suite / Booking + Info / Info & Status Only (defaults to Full)

On submit: registers via API → gets JWT → auto-creates and deploys the chosen agent graph → lands on Agents page.

---

### Backend — Auth (`backend/api/auth.py`)

Fully rewritten to support credential-based auth. Key decisions:

**bcrypt direct usage** (not passlib):  
`passlib 1.7.x` is incompatible with `bcrypt 5.x` (calls `bcrypt.__about__.__version__` which doesn't exist). Direct `bcrypt.hashpw` / `bcrypt.checkpw` used instead.

```python
def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain[:72].encode(), bcrypt.gensalt()).decode()

def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain[:72].encode(), hashed.encode())
```

The `[:72]` slice is intentional — bcrypt silently truncates at 72 bytes. Explicit truncation makes behavior deterministic.

**JWT issuance:**  
Both tenant and admin tokens are signed with `SUPABASE_JWT_SECRET` using `python-jose`. This keeps them compatible with the existing `decode_jwt()` function in `security.py` — no new verification logic needed.

- Tenant JWT: 24-hour expiry, carries `tenant_id`, `role: admin`
- Admin JWT: 8-hour expiry, carries `role: super_admin`, no `tenant_id` (intentionally rejected by `get_current_tenant`)

**New endpoints:**

| Endpoint | Auth | Description |
|---|---|---|
| `POST /auth/register` | Public | Creates tenant with hashed password, returns JWT + tenant profile |
| `POST /auth/login` | Public | Verifies email + bcrypt password, returns JWT + tenant profile |
| `POST /auth/admin/login` | Public | Checks against `ADMIN_EMAIL` + `ADMIN_PASSWORD_HASH` env vars, returns admin JWT |

---

### Database — Migration (`migrations/versions/2026_04_16_add_hashed_password_to_tenants.py`)

| Field | | |
|---|---|---|
| **Revision ID** | `d4e8f1a2b3c9` | |
| **Down revision** | `c3d9f2b05e8a` | (add_channel_configs) |
| **Change** | `ADD COLUMN hashed_password VARCHAR(255) NULL` to `tenants` | |

`nullable=True` is deliberate — existing tenants (MedCare, Gloss & Glow) have no password and authenticate via `demo-token`. Adding NOT NULL would break existing rows.

---

### Schema (`backend/schemas/tenant.py`)

Three new Pydantic schemas:

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant: TenantResponse
```

`TenantCreate` gained a `password` field (`min_length=8`).

---

### Config (`backend/core/config.py`)

Two new env vars:

```python
ADMIN_EMAIL: str = "admin@appointai.in"
ADMIN_PASSWORD_HASH: str = ""  # bcrypt hash; empty = admin login disabled
```

If `ADMIN_PASSWORD_HASH` is empty, `/auth/admin/login` returns `503 Service Unavailable` rather than silently allowing login.

---

### Seed Data (`tests/seed_data.json` → v1.1.0)

Added **FitLife Coaching** as a third demo tenant:

```json
{
  "id": "33333333-0000-0000-0000-000000000003",
  "name": "FitLife Coaching",
  "business_type": "coaching",
  "subdomain": "fitlife",
  "email": "coach@fitlife.example",
  "password": "demo@123"
}
```

The `seed_loader.py` now hashes `password` via bcrypt when present. MedCare and Gloss & Glow have no `password` field — their `hashed_password` is `NULL`.

---

## Login Credentials — All Accounts

### Tenant Accounts (Business Portal)

| Business | Email | Password | Login Method | Notes |
|---|---|---|---|---|
| **MedCare Clinic** | `admin@medcare.example` | *(none)* | Demo button | Uses `GET /auth/demo-token?subdomain=medcare` |
| **Gloss & Glow Salon** | `admin@glossglow.example` | *(none)* | Demo button | Uses `GET /auth/demo-token?subdomain=glossglow` |
| **FitLife Coaching** | `coach@fitlife.example` | `demo@123` | Email + password | Uses `POST /auth/login` |

**How to access demo accounts:**  
Visit `http://localhost:8000` → click a tenant card on the landing page, or click **Sign In** → use the demo buttons at the bottom of the login form.

**How to access FitLife:**  
Visit `http://localhost:8000` → click **Sign In** → enter `coach@fitlife.example` / `demo@123`.

### Platform Admin Account

| Role | Email | Password | Login Method |
|---|---|---|---|
| **Super Admin** | `admin@appointai.in` | `Admin@123` | Admin login page |

**How to access:**  
Visit `http://localhost:8000` → click **Admin** in the top-right navbar → enter credentials.

**To change the admin password:**
```bash
# Generate new hash
python -c "import bcrypt; print(bcrypt.hashpw(b'YourNewPassword', bcrypt.gensalt()).decode())"

# Paste the output into .env:
ADMIN_PASSWORD_HASH=<paste hash here>
```

### New Tenant (Self-Registration)

Any user can register at `http://localhost:8000` → **Get Started Free**:

1. Fill in business name, type, subdomain, phone, email
2. Set a password (min 8 characters)
3. Choose an agent template
4. Account is created and the chosen template is deployed automatically

---

## API Endpoints Added

```
POST  /api/v1/auth/register      → Create tenant + return JWT (used by signup wizard)
POST  /api/v1/auth/login         → Email + password → JWT (used by login form)
POST  /api/v1/auth/admin/login   → Platform admin credentials → admin JWT
```

These join the existing endpoints:
```
GET   /api/v1/auth/me            → Current tenant profile (JWT required)
GET   /api/v1/auth/demo-token    → Dev-only demo JWT (no password required)
```

---

## Environment Variables Added

Add these to your `.env` (already set for local dev):

```bash
# Platform Admin
ADMIN_EMAIL=admin@appointai.in
ADMIN_PASSWORD_HASH=$2b$12$...   # bcrypt hash of admin password
```

---

## Architecture Decisions

**Why env-var admin credentials, not a DB table?**  
Super admin management (create/update/delete admins) is a Phase 5 concern. Using env vars avoids a premature `admins` table while still enabling secure login. The `ADMIN_PASSWORD_HASH` being empty disables login entirely — safe by default.

**Why not use Supabase Auth for tenant login?**  
The platform issues its own JWTs signed with `SUPABASE_JWT_SECRET`. This keeps all auth in one layer (FastAPI) without requiring Supabase Auth client calls per login. The JWTs are fully compatible with the existing `decode_jwt()` in `security.py`.

**Why nullable `hashed_password`?**  
Existing demo tenants (MedCare, Gloss & Glow) were created without passwords. Making the column NOT NULL would break them. The `NULL` check in `/auth/login` returns `401` with the same generic message — no information leaked about whether the account exists or just has no password.

---

## What Phase 5 Will Add

The admin dashboard currently shows placeholder stats and a Phase 5 teaser card. Phase 5 will wire in:

- Real tenant list with active/inactive management
- LLM token usage per tenant (from `billing_events` table)
- Per-tenant cost dashboard
- Stripe subscription and usage billing
- Platform health monitoring
