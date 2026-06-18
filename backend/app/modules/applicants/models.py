from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.enums import Gender, pg_enum


class Applicant(UUIDPKMixin, TimestampMixin, Base):
    """Abituriyent profili — 1:1 with users.role='applicant'.

    Mirrors old Django AbituriyentProfile (passport_series, pinfl,
    region/district FKs to first-class regions module, profile photo).
    """

    __tablename__ = "applicants"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_applicants_user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Shaxsiy ma'lumotlar
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    other_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)

    gender: Mapped[Gender] = mapped_column(
        pg_enum(Gender, "gender"),
        nullable=False,
    )

    # Hujjat ma'lumotlari (XX1234567 va 14 ta raqamli PINFL)
    passport_series: Mapped[str | None] = mapped_column(
        String(9), unique=True, nullable=True, index=True
    )
    pinfl: Mapped[str | None] = mapped_column(
        String(14), unique=True, nullable=True, index=True
    )

    # Manzil — yangi regions modulidagi tablelarga FK
    region_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    district_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("districts.id", ondelete="SET NULL"),
        nullable=True,
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Qo'shimcha
    nationality: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="O'zbek"
    )
    additional_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Email kept as legacy column; UI now collects Telegram username instead.
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Fayllar
    image_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    passport_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    registered_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


# ---------- Diploms catalog (under applicants module) ----------

class EducationType(UUIDPKMixin, TimestampMixin, Base):
    """Bakalavr, Magistratura, O'rta-maxsus, ..."""

    __tablename__ = "education_types"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class InstitutionType(UUIDPKMixin, TimestampMixin, Base):
    """Universitet, Institut, Akademiya, Kollej, ..."""

    __tablename__ = "institution_types"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Course(UUIDPKMixin, TimestampMixin, Base):
    """1-kurs, 2-kurs, ... — used for transfer (perevod) target course."""

    __tablename__ = "courses"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class Diplom(UUIDPKMixin, TimestampMixin, Base):
    """Local diploma (o'rta-maxsus / akademik / Bakalavr).

    Used for both:
      - 1-kurs (yangi qabul) — high school / college diploma →
        is_for_second_specialization = False
      - 2-mutaxassislik — prior Bachelor's degree →
        is_for_second_specialization = True

    Unique on (user_id, is_for_second_specialization) so one user
    can carry at most one of each kind.
    """

    __tablename__ = "diploms"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "is_for_second_specialization",
            name="uq_diploms_user_purpose",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    education_type_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("education_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    institution_type_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("institution_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    university_name: Mapped[str] = mapped_column(Text, nullable=False)
    graduation_year: Mapped[str] = mapped_column(String(4), nullable=False)
    region_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    district_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("districts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    diploma_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    # FALSE → 1-kurs diplomi (default), TRUE → 2-mutaxassislik
    # uchun Bakalavr darajasi diplomi. The composite unique on
    # (user_id, is_for_second_specialization) keeps one of each per user.
    is_for_second_specialization: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )


class TransferDiplom(UUIDPKMixin, TimestampMixin, Base):
    """Perevod (o'qishni ko'chirish) uchun diplom."""

    __tablename__ = "transfer_diploms"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_transfer_diploms_user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    country_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
    )
    university_name: Mapped[str] = mapped_column(Text, nullable=False)
    target_course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    transcript_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
