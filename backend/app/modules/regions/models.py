from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Country(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "countries"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Region(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "regions"
    __table_args__ = (
        UniqueConstraint("name", "country_id", name="uq_regions_name_country"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


class District(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "districts"
    __table_args__ = (
        UniqueConstraint("name", "region_id", name="uq_districts_name_region"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    region_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
