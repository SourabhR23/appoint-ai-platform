"""
api/router.py

Central API router — registers all sub-routers under /api/v1/.
All routes are versioned under v1. Adding v2 routes requires a new router file.
"""

from fastapi import APIRouter

from backend.api import (
    auth, appointments, tenants, graphs, chat,
    staff, health, services, slots, channels, webhooks,
)

api_router = APIRouter(prefix="/api/v1")

# Health — no auth, no prefix conflict
api_router.include_router(health.router)

# Auth — no JWT required for register
api_router.include_router(auth.router)

# Protected routes — all require Bearer token
api_router.include_router(tenants.router)
api_router.include_router(appointments.router)
api_router.include_router(staff.router)
api_router.include_router(services.router)
api_router.include_router(slots.router)
api_router.include_router(graphs.router)
api_router.include_router(chat.router)
api_router.include_router(channels.router)

# Inbound webhooks — no JWT, validated by Twilio signature
api_router.include_router(webhooks.router)
