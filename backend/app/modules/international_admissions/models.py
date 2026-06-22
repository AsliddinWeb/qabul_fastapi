"""International admissions — abridged applicant pipeline for non-residents.

This is a DIFFERENT funnel from the main Application module:
  - No User/Applicant prerequisite: the lead applies from a public
    landing page without an account.
  - Different document set: passport scan + diploma scan + 3x4 photo;
    no PINFL / region / district / Uzbek-specific stuff.
  - Different stage model: 6-stage Kanban (Application → Doc review →
    Offer → Contract → Payment → Admitted) instead of the standard
    REGULAR/REJECTED enum.

Once an international applicant clears the pipeline (stage 5), staff
can spin up a regular User+Applicant+Application+Contract chain from
this row — that promotion lives in a separate flow and is NOT
modelled here.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class InternationalApplication(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "international_applications"

    # Public-facing reference number printed on the success screen and
    # on every staff-generated document. Format: "XIU-INT-2026-001".
    ref_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)

    # ---- Identity (free-text — no DB-level relations) ----
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    passport_number: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ---- Contact ----
    phone: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    # ---- Program choice ----
    # `program` is just the level — "Bachelor" or "Master" — kept as
    # free text because the system's existing program/level catalogue
    # is intentionally not joined here (intl applicants pick by faculty
    # name first, the formal program assignment happens after the
    # offer is signed).
    program: Mapped[str] = mapped_column(String(20), nullable=False)
    faculty_code: Mapped[str] = mapped_column(String(20), nullable=False)
    faculty_text: Mapped[str] = mapped_column(String(120), nullable=False)

    # ---- Files (FK to the files module; nullable=SET NULL on delete) ----
    passport_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    diploma_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    photo_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---- Pipeline state ----
    # 0: Application Submitted, 1: Document Review,
    # 2: Conditional Offer Sent, 3: Contract Signed,
    # 4: Payment Received, 5: Admitted & Invited
    # We keep this as a small int instead of an enum because the stage
    # set is fixed at 6 and we already advance/regress by ±1 in code.
    stage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", index=True,
    )

    rejected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- Anti-spam audit trail ----
    # These come from the request context at submission time; they're
    # never displayed to the operator, just used for forensics when
    # something coordinated comes through.
    submitter_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    submitter_user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str | None] = mapped_column(String(5), nullable=True)
