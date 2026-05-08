"""Shared Pydantic base schemas + response envelopes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppSchema(BaseModel):
    """Base for all DTOs. Strict by default — extra fields rejected."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class IdSchema(AppSchema):
    id: UUID


class TimestampedSchema(AppSchema):
    created_at: datetime
    updated_at: datetime


T = TypeVar("T")


class PageResponse(AppSchema, Generic[T]):
    """Standard paginated response envelope."""

    items: list[T]
    total: int
    page: int
    size: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, size: int) -> "PageResponse[T]":
        return cls(items=items, total=total, page=page, size=size)


class MessageResponse(AppSchema):
    """Generic acknowledgement response."""

    message: str
    data: dict[str, Any] | None = None
