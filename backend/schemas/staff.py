"""
schemas/staff.py
"""

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class StaffCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    specialization: Optional[str] = Field(default=None, max_length=255)
    priority_order: int = Field(default=1, ge=1)
    # working_hours: { "monday": [{"start": "09:00", "end": "18:00"}], ... }
    working_hours: dict = Field(default_factory=dict)


class StaffUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    specialization: Optional[str] = None
    priority_order: Optional[int] = None
    working_hours: Optional[dict] = None
    is_active: Optional[bool] = None


class StaffResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    specialization: Optional[str]
    priority_order: int
    working_hours: dict
    calendar_connected: bool
    is_active: bool

    model_config = {"from_attributes": True}
