"""
schemas/appointment.py

Pydantic schemas for appointment CRUD.
Input timestamps must include timezone offset — backend normalises to UTC.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class AppointmentCreate(BaseModel):
    """Request body for creating a new appointment."""

    patient_name: str = Field(..., min_length=2, max_length=255)
    patient_phone: str = Field(..., min_length=10, max_length=15)
    patient_email: Optional[EmailStr] = None

    service_id: uuid.UUID
    staff_id: uuid.UUID

    # Must be ISO 8601 with timezone: 2026-04-10T14:30:00+05:30
    slot_datetime: datetime

    channel: str = Field(
        default="manual",
        pattern="^(webchat|whatsapp|sms|manual)$",
    )
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("slot_datetime")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("slot_datetime must include timezone info (ISO 8601).")
        return v


class AppointmentUpdate(BaseModel):
    """Request body for updating an existing appointment (receptionist edits)."""

    status: Optional[str] = Field(
        default=None,
        pattern="^(pending|confirmed|completed|no_show|cancelled)$",
    )
    notes: Optional[str] = Field(default=None, max_length=1000)
    cancellation_reason: Optional[str] = Field(default=None, max_length=500)
    staff_id: Optional[uuid.UUID] = None


class AppointmentReschedule(BaseModel):
    """Request body for rescheduling — changes only the slot."""

    new_slot_datetime: datetime

    @field_validator("new_slot_datetime")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("new_slot_datetime must include timezone info (ISO 8601).")
        return v


class AppointmentResponse(BaseModel):
    """Outbound appointment representation."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_name: str
    patient_phone: str
    patient_email: Optional[str]
    service_id: uuid.UUID
    staff_id: uuid.UUID
    slot_datetime: datetime
    slot_end_datetime: datetime
    status: str
    channel: str
    notes: Optional[str]
    cancellation_reason: Optional[str]
    idempotency_key: str
    recurrence_group_id: Optional[uuid.UUID]
    recurrence_index: Optional[int]
    google_event_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppointmentFilter(BaseModel):
    """Query parameters for listing appointments."""

    staff_id: Optional[uuid.UUID] = None
    service_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    patient_phone: Optional[str] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
