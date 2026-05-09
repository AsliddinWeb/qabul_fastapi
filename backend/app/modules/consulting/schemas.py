from __future__ import annotations

from pydantic import Field

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema


class ConsultingAgencyBase(AppSchema):
    name: str = Field(min_length=1, max_length=150)
    is_active: bool = True
    notes: str | None = None


class ConsultingAgencyCreate(ConsultingAgencyBase):
    pass


class ConsultingAgencyUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    is_active: bool | None = None
    notes: str | None = None


class ConsultingAgencyRead(IdSchema, TimestampedSchema, ConsultingAgencyBase):
    pass
