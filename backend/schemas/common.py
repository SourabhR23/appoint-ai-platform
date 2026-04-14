"""
schemas/common.py

Shared response envelopes used by every API endpoint.
All API responses follow one consistent shape (R15):
    { "success": bool, "data": any, "error": str | null }
"""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard single-item response envelope."""

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, data: T) -> "APIResponse[T]":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, message: str) -> "APIResponse[None]":
        return cls(success=False, data=None, error=message)


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list response envelope."""

    success: bool = True
    items: List[T]
    total: int
    page: int
    limit: int
    error: Optional[str] = None


class PaginationParams(BaseModel):
    """Common query params for paginated endpoints."""

    page: int = 1
    limit: int = 20

    def offset(self) -> int:
        return (self.page - 1) * self.limit
