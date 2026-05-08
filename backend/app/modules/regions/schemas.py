from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema


# ---------- Country ----------
class CountryBase(AppSchema):
    name: str = Field(min_length=1, max_length=100)


class CountryCreate(CountryBase):
    pass


class CountryUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class CountryRead(IdSchema, TimestampedSchema, CountryBase):
    pass


# ---------- Region ----------
class RegionBase(AppSchema):
    name: str = Field(min_length=1, max_length=100)
    country_id: UUID


class RegionCreate(RegionBase):
    pass


class RegionUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    country_id: UUID | None = None


class RegionRead(IdSchema, TimestampedSchema, RegionBase):
    pass


# ---------- District ----------
class DistrictBase(AppSchema):
    name: str = Field(min_length=1, max_length=100)
    region_id: UUID


class DistrictCreate(DistrictBase):
    pass


class DistrictUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    region_id: UUID | None = None


class DistrictRead(IdSchema, TimestampedSchema, DistrictBase):
    pass
