from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Passport(UUIDPKMixin, TimestampMixin, Base):
    """Passport details — 1:1 with applicants."""

    __tablename__ = "passports"
    __table_args__ = (
        UniqueConstraint("applicant_id", name="uq_passports_applicant_id"),
        UniqueConstraint("series", "number", name="uq_passports_series_number"),
    )

    applicant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applicants.id", ondelete="CASCADE"),
        nullable=False,
    )

    series: Mapped[str] = mapped_column(String(2), nullable=False)
    number: Mapped[str] = mapped_column(String(7), nullable=False)
    pinfl: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)

    issued_by: Mapped[str] = mapped_column(String(255), nullable=False)
    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    expires_date: Mapped[date] = mapped_column(Date, nullable=False)

    scan_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
