"""Lead funnel (CRM) — pipelines, stages, sources, lost reasons, leads, activities.

Design:
  • A `LeadPipeline` is a configurable funnel (e.g. "Yangi qabul", "Perevod").
  • Each pipeline has ordered `LeadStage` rows — admin-editable.
  • A `Lead` belongs to one pipeline and one stage.
  • `LeadSource` is a catalog (web_form, telegram, instagram, call, walk_in, ...).
  • `LeadLostReason` is a catalog of standard "why did we lose this lead" reasons.
  • `LeadActivity` is a per-lead audit/timeline (stage moves, comments, calls).
  • When a Lead is converted, applicant_id + application_id get filled and
    status becomes 'won' — the lead row stays for analytics.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.enums import LeadStatus, pg_enum


# --------------------------------------------------------------------------- #
#  Pipelines
# --------------------------------------------------------------------------- #

class LeadPipeline(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_pipelines"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")


# --------------------------------------------------------------------------- #
#  Stages (per pipeline)
# --------------------------------------------------------------------------- #

class LeadStage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_stages"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "name", name="uq_lead_stages_pipeline_name"),
        Index("ix_lead_stages_pipeline_order", "pipeline_id", "order_index"),
    )

    pipeline_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lead_pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # The "is_terminal" stage is the one where ✓ converts the lead into an Application.
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


# --------------------------------------------------------------------------- #
#  Source catalog
# --------------------------------------------------------------------------- #

class LeadSource(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_sources"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)  # web_form / telegram / ...
    name: Mapped[str] = mapped_column(String(100), nullable=False)              # display label
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")


# --------------------------------------------------------------------------- #
#  Lost reasons catalog
# --------------------------------------------------------------------------- #

class LeadLostReason(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_lost_reasons"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")


# --------------------------------------------------------------------------- #
#  Lead
# --------------------------------------------------------------------------- #

class Lead(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_phone", "phone"),
        Index("ix_leads_pipeline_stage", "pipeline_id", "stage_id"),
        Index("ix_leads_assigned", "assigned_to_id"),
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    # Email kept as legacy column; form now collects Telegram username instead.
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Funnel position
    pipeline_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lead_pipelines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stage_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lead_stages.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Where the lead came from
    source_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lead_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Free-text source meta (e.g. ad campaign, referrer, IG post id)
    source_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Interest / target program (optional)
    branch_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
    )
    program_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Assignment
    assigned_to_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Notes (operator-editable; activity log keeps history)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status / lifecycle
    status: Mapped[LeadStatus] = mapped_column(
        pg_enum(LeadStatus, "lead_status"),
        nullable=False,
        default=LeadStatus.OPEN,
        server_default=LeadStatus.OPEN.value,
        index=True,
    )

    # When converted → which applicant + application (won)
    applicant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applicants.id", ondelete="SET NULL"),
        nullable=True,
    )
    application_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
    )
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # When lost → reason
    lost_reason_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lead_lost_reasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    lost_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    lost_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Last meaningful contact for SLA computations
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # When the lead entered the current stage (used for SLA)
    stage_entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )
    # Operator-scheduled callback: when to contact this lead next (Phase 3 — tasks)
    next_contact_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )
    next_contact_note: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
#  Activity (timeline)
# --------------------------------------------------------------------------- #

class LeadActivity(UUIDPKMixin, Base):
    """Per-lead timeline: stage moves, manual notes, calls, etc."""

    __tablename__ = "lead_activities"
    __table_args__ = (
        Index("ix_lead_activities_lead_created", "lead_id", "created_at"),
    )

    lead_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Action codes: 'create', 'stage_move', 'assign', 'comment', 'call', 'merge', 'convert', 'lose', 'reopen'
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    from_stage_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lead_stages.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_stage_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lead_stages.id", ondelete="SET NULL"),
        nullable=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), index=True,
    )
