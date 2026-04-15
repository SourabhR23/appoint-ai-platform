"""
schemas/tenant.py

Pydantic schemas for tenant registration, onboarding, and responses.
All inputs are validated here before reaching services/repositories.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class TenantCreate(BaseModel):
    """Payload for business registration (Step 1 of onboarding)."""

    name: str = Field(..., min_length=2, max_length=255)
    business_type: str = Field(
        ..., pattern="^(clinic|salon|consultancy|coaching|other)$"
    )
    subdomain: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-z0-9-]+$",
        description="Lowercase letters, numbers, and hyphens only.",
    )
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    timezone: str = Field(default="Asia/Kolkata")
    password: str = Field(..., min_length=8, description="Account password")

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, v: str) -> str:
        digits = v.replace("+", "").replace("-", "").replace(" ", "")
        if not digits.isdigit():
            raise ValueError("Phone must contain only digits, +, -, or spaces.")
        return v


class TenantConfigUpdate(BaseModel):
    """Partial update of tenant configuration (business hours, policies, etc.)."""

    config: dict = Field(
        default_factory=dict,
        description=(
            "Flexible config: business_hours, cancellation_hours, "
            "allow_same_day, slot_buffer_minutes, notification_templates"
        ),
    )
    timezone: Optional[str] = None


class TenantResponse(BaseModel):
    """Outbound tenant representation — never returns secrets or internal fields."""

    id: uuid.UUID
    name: str
    business_type: str
    subdomain: str
    email: str
    phone: str
    timezone: str
    plan: str
    is_active: bool
    onboarding_completed: bool
    trial_ends_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


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
