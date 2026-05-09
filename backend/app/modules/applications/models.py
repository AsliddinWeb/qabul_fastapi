from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.enums import AdmissionType, ApplicationStatus, pg_enum


class Application(UUIDPKMixin, TimestampMixin, Base):
    """Abituriyent's submission for a specific program (1:1 per applicant per program).

    Mirrors old Django Application: branch, education_level, education_form,
    program, admission_type (yangi_qabul/perevod), diplom OR transfer_diplom.
    """

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("applicant_id", "program_id", name="uq_applications_applicant_program"),
    )

    application_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    applicant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applicants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    admission_type: Mapped[AdmissionType] = mapped_column(
        pg_enum(AdmissionType, "admission_type"),
        nullable=False,
        default=AdmissionType.REGULAR,
        server_default=AdmissionType.REGULAR.value,
        index=True,
    )

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
    )
    education_form_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("education_forms.id", ondelete="RESTRICT"),
        nullable=False,
    )
    program_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    diplom_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("diploms.id", ondelete="SET NULL"),
        nullable=True,
    )
    transfer_diplom_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transfer_diploms.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )

    contract_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        pg_enum(ApplicationStatus, "application_status"),
        nullable=False,
        default=ApplicationStatus.PENDING,
        server_default=ApplicationStatus.PENDING.value,
        index=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # If this application was converted from a Lead — link back for analytics.
    lead_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lead_source_code: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Consulting agency (partner) that brought the applicant in. Optional.
    # Visible/filterable only by users with is_consulting=True (UI-side gate);
    # the column itself is part of the public model.
    consulting_agency_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("consulting_agencies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class ApplicationStatusHistory(UUIDPKMixin, Base):
    """Append-only audit trail of status transitions."""

    __tablename__ = "application_status_history"

    application_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_status: Mapped[ApplicationStatus | None] = mapped_column(
        pg_enum(ApplicationStatus, "application_status", create_type=False),
        nullable=True,
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        pg_enum(ApplicationStatus, "application_status", create_type=False),
        nullable=False,
    )

    changed_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
        index=True,
    )
