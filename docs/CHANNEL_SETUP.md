# Channel Setup Guide

## Overview

This platform uses **Option 2 — Tenant-Provided Credentials**.

Each tenant brings their own Twilio account (SMS + WhatsApp) and Gmail account (email).
The platform stores these credentials and uses them to send notifications on behalf of each tenant.

**Why?**
- Tenant owns their number (no platform lock-in)
- Costs go to tenant's Twilio/Gmail account directly
- Platform is not liable for messages sent
- Multi-tenant isolation — each business sends from their own number

---

## Twilio Setup (SMS + WhatsApp)

### Step 1 — Create Twilio Account
1. Go to [twilio.com](https://www.twilio.com) → Sign up (free trial includes $15 credit)
2. Verify your phone number

### Step 2 — Get Credentials
1. Dashboard → **Account Info** panel (top left)
2. Copy **Account SID** and **Auth Token**

### Step 3 — Buy a Phone Number (SMS)
1. Console → **Phone Numbers** → **Manage** → **Buy a number**
2. Choose a country, check SMS capability, buy
3. Copy the number (e.g. `+1234567890`)

### Step 4 — WhatsApp Setup
**Sandbox (for testing):**
1. Console → **Messaging** → **Try it out** → **Send a WhatsApp message**
2. Note the sandbox number (e.g. `+14155238886`)
3. Instruct end-users to send `join <keyword>` to the sandbox number before messaging

**Production (for real business use):**
1. You need a Meta Business Account + verified WhatsApp Business number
2. Console → **Messaging** → **Senders** → **WhatsApp senders** → Apply
3. Takes 1–3 days for Meta approval

### Step 5 — Configure Webhook URL
1. Console → **Phone Numbers** → click your number
2. Under **Messaging** → set webhook URL:
   - SMS: `https://yourdomain.com/api/v1/webhooks/twilio/sms`
   - WhatsApp Sandbox: **Messaging** → **Sandbox settings** → set webhook
3. Set HTTP method to **POST**

### Step 6 — Enter Credentials in App
1. Log into your tenant portal → **Channels** page
2. Click **Configure** on SMS card → enter Account SID, Auth Token, Phone Number → Save
3. Click **Configure** on WhatsApp card → enter credentials + WhatsApp number → Save

---

## Gmail Setup (Email Notifications)

> Uses Python `smtplib` (standard library) + Gmail SMTP — no external email provider needed.

### Step 1 — Create/Use a Gmail Account
Use a dedicated Gmail for your business notifications (e.g. `medcare.notify@gmail.com`)

### Step 2 — Enable 2-Step Verification
1. Google Account → **Security** → **2-Step Verification** → Turn on

### Step 3 — Generate App Password
1. Google Account → **Security** → **2-Step Verification** → scroll down → **App passwords**
2. Select app: **Mail** → Select device: **Other (Custom name)** → type `AppointAI`
3. Click **Generate** → copy the 16-character password (e.g. `abcd efgh ijkl mnop`)
4. Store this password safely — it is shown only once

### Step 4 — Enter Credentials in App
1. Log into your tenant portal → **Channels** page
2. Click **Configure** on Email card
3. Enter:
   - **Gmail address**: `yourname@gmail.com`
   - **App password**: the 16-char password from Step 3
4. Save — the platform sends a test email to verify

---

## Environment Variables (.env)

These are **platform-level defaults** (used when tenant has no custom credentials configured):

```
# Twilio — platform default (for demo tenants)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_FROM=+1234567890
TWILIO_WHATSAPP_FROM=+14155238886

# SMTP Email — platform default
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-platform-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM_NAME=AppointAI
```

---

## How Credentials Are Used

```
Inbound message (SMS/WhatsApp)
       ↓
Twilio webhook → POST /webhooks/twilio/sms
       ↓
Lookup tenant by "To" number in channel_configs table
       ↓
Route message to tenant's deployed agent graph
       ↓
Agent responds → send reply using tenant's own Twilio credentials
```

Credentials are stored in the `channel_configs` table scoped to `tenant_id`.
Platform `.env` credentials are used only as fallback for tenants without custom setup.
