"""
schemas/service.py

Pydantic schemas for service CRUD.
Price is stored in paise (integer) to avoid float precision issues.
Frontend receives/sends price_rupees (float) — conversion happens here.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: Optional[str] = Field(default=None, max_length=100)
    duration_minutes: int = Field(default=30, ge=5, le=480)
    buffer_minutes: int = Field(default=10, ge=0, le=120)
    # Accept price in rupees from frontend, store as paise
    price_rupees: float = Field(default=0.0, ge=0)
    # UUIDs of staff who can perform this service
    staff_ids: List[str] = Field(default_factory=list)

    @property
    def price_paise(self) -> int:
        return round(self.price_rupees * 100)


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=100)
    duration_minutes: Optional[int] = Field(default=None, ge=5, le=480)
    buffer_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    price_rupees: Optional[float] = Field(default=None, ge=0)
    staff_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @property
    def price_paise(self) -> Optional[int]:
        if self.price_rupees is not None:
            return round(self.price_rupees * 100)
        return None


class ServiceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str]
    category: Optional[str]
    duration_minutes: int
    buffer_minutes: int
    price_paise: int
    staff_ids: list
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed field: price in rupees for frontend display
    @property
    def price_rupees(self) -> float:
        return self.price_paise / 100

    model_config = {"from_attributes": True}
