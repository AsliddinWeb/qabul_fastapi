from __future__ import annotations

from uuid import UUID

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Branch(UUIDPKMixin, TimestampMixin, Base):
    """University branch (filial): Toshkent, Andijon, Nukus, ..."""

    __tablename__ = "branches"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class EducationLevel(UUIDPKMixin, TimestampMixin, Base):
    """Bakalavr, Magistr, ..."""

    __tablename__ = "education_levels"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class EducationForm(UUIDPKMixin, TimestampMixin, Base):
    """Kunduzgi, Sirtqi, Kechki, Masofaviy, ..."""

    __tablename__ = "education_forms"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Program(UUIDPKMixin, TimestampMixin, Base):
    """Yo'nalish — branch + edu_level + edu_form + name + tuition fee snapshot."""

    __tablename__ = "programs"

    branch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    education_level_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("education_levels.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    education_form_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("education_forms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)

    image_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    tuition_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    study_duration_years: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    contract_series: Mapped[str] = mapped_column(String(100), nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
