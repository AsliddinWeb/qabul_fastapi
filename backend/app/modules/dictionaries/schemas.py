from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema


# ---------- Dictionary Type ----------
class DictionaryTypeBase(AppSchema):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_hierarchical: bool = False


class DictionaryTypeCreate(DictionaryTypeBase):
    pass


class DictionaryTypeUpdate(AppSchema):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    is_hierarchical: bool | None = None


class DictionaryTypeRead(IdSchema, TimestampedSchema, DictionaryTypeBase):
    is_system: bool


# ---------- Dictionary Item ----------
class DictionaryItemBase(AppSchema):
    code: str | None = Field(default=None, max_length=50)
    name_uz: str = Field(min_length=1, max_length=255)
    name_ru: str | None = Field(default=None, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    sort_order: int = 0
    extra: dict[str, Any] | None = None
    is_active: bool = True
    parent_id: UUID | None = None


class DictionaryItemCreate(DictionaryItemBase):
    pass


class DictionaryItemUpdate(AppSchema):
    code: str | None = Field(default=None, max_length=50)
    name_uz: str | None = Field(default=None, max_length=255)
    name_ru: str | None = Field(default=None, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    sort_order: int | None = None
    extra: dict[str, Any] | None = None
    is_active: bool | None = None
    parent_id: UUID | None = None


class DictionaryItemRead(IdSchema, TimestampedSchema, DictionaryItemBase):
    type_id: UUID
