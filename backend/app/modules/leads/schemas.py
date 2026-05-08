from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import EmailStr, Field

from app.core.schemas import AppSchema, IdSchema
from app.db.enums import LeadStatus


# --------------------------------------------------------------------------- #
#  Pipelines
# --------------------------------------------------------------------------- #

class LeadPipelineCreate(AppSchema):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    is_default: bool = False
    is_active: bool = True
    order_index: int = 0


class LeadPipelineUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    order_index: int | None = None


class LeadPipelineRead(IdSchema):
    name: str
    description: str | None = None
    is_default: bool
    is_active: bool
    order_index: int
    created_at: datetime


# --------------------------------------------------------------------------- #
#  Stages
# --------------------------------------------------------------------------- #

class LeadStageCreate(AppSchema):
    pipeline_id: UUID
    name: str = Field(min_length=1, max_length=100)
    order_index: int = 0
    color: str | None = Field(default=None, max_length=20)
    is_terminal: bool = False
    is_active: bool = True


class LeadStageUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    order_index: int | None = None
    color: str | None = Field(default=None, max_length=20)
    is_terminal: bool | None = None
    is_active: bool | None = None


class LeadStageRead(IdSchema):
    pipeline_id: UUID
    name: str
    order_index: int
    color: str | None = None
    is_terminal: bool
    is_active: bool


# --------------------------------------------------------------------------- #
#  Sources
# --------------------------------------------------------------------------- #

class LeadSourceCreate(AppSchema):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True
    order_index: int = 0


class LeadSourceUpdate(AppSchema):
    code: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    order_index: int | None = None


class LeadSourceRead(IdSchema):
    code: str
    name: str
    is_active: bool
    order_index: int


# --------------------------------------------------------------------------- #
#  Lost reasons
# --------------------------------------------------------------------------- #

class LeadLostReasonCreate(AppSchema):
    name: str = Field(min_length=1, max_length=120)
    is_active: bool = True
    order_index: int = 0


class LeadLostReasonUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None
    order_index: int | None = None


class LeadLostReasonRead(IdSchema):
    name: str
    is_active: bool
    order_index: int


# --------------------------------------------------------------------------- #
#  Lead
# --------------------------------------------------------------------------- #

class LeadCreate(AppSchema):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=4, max_length=20)
    email: EmailStr | None = None
    telegram_username: str | None = Field(default=None, max_length=64)

    pipeline_id: UUID | None = None  # default pipeline if missing
    stage_id: UUID | None = None     # first stage if missing

    source_id: UUID | None = None
    source_meta: dict[str, Any] | None = None

    branch_id: UUID | None = None
    program_id: UUID | None = None

    assigned_to_id: UUID | None = None
    auto_assign: bool = False  # round-robin if true and assigned_to_id is missing

    notes: str | None = None


class LeadPublicCreate(AppSchema):
    """Public landing form payload — minimal fields + anti-spam.

    `hp` is a honeypot (sent as `_hp` from the form) — bots fill it, humans don't.
    `t` is the page-load timestamp (ms since epoch); enforced to be 2s..30min old.
    """
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=4, max_length=20)
    program_id: UUID | None = None
    source_code: str | None = Field(default=None, max_length=50)

    # Anti-spam
    hp: str | None = Field(default=None, max_length=200, alias="_hp")
    t: int | None = None  # page-load timestamp (ms)


class LeadPublicResponse(AppSchema):
    """Response from /leads/public.

    `status` distinguishes between:
      • created   — brand-new lead created at first stage
      • merged    — phone already had an OPEN lead; non-empty fields were merged
      • duplicate — phone already converted (WON) or lost (LOST); no new lead,
                    only an activity log on the existing one
    """
    status: Literal["created", "merged", "duplicate"]
    message: str


class LeadUpdate(AppSchema):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, min_length=4, max_length=20)
    email: EmailStr | None = None
    telegram_username: str | None = Field(default=None, max_length=64)
    source_id: UUID | None = None
    branch_id: UUID | None = None
    program_id: UUID | None = None
    notes: str | None = None


class LeadMove(AppSchema):
    stage_id: UUID
    comment: str | None = None


class LeadAssign(AppSchema):
    user_id: UUID | None = None  # null means auto-assign
    auto_assign: bool = False


class LeadLose(AppSchema):
    reason_id: UUID | None = None
    comment: str | None = None


class LeadConvert(AppSchema):
    """Confirms conversion (creates Application from Lead).

    Optionally allows the operator to override the program/branch on the way out.
    """
    branch_id: UUID | None = None
    program_id: UUID | None = None


class LeadCommentCreate(AppSchema):
    comment: str = Field(min_length=1)


class LeadScheduleContact(AppSchema):
    """Schedule the next callback for this lead (operator-side reminder)."""
    next_contact_at: datetime | None = None  # null clears the reminder
    note: str | None = Field(default=None, max_length=500)


class LeadActivityRead(IdSchema):
    lead_id: UUID
    user_id: UUID | None = None
    user_full_name: str | None = None
    user_phone: str | None = None
    action: str
    from_stage_id: UUID | None = None
    from_stage_name: str | None = None
    to_stage_id: UUID | None = None
    to_stage_name: str | None = None
    comment: str | None = None
    extra: dict[str, Any] | None = None
    created_at: datetime


class LeadRead(IdSchema):
    full_name: str
    phone: str
    email: str | None = None
    telegram_username: str | None = None
    pipeline_id: UUID
    stage_id: UUID
    source_id: UUID | None = None
    source_meta: dict[str, Any] | None = None
    branch_id: UUID | None = None
    program_id: UUID | None = None
    assigned_to_id: UUID | None = None
    created_by_id: UUID | None = None
    notes: str | None = None
    status: LeadStatus
    applicant_id: UUID | None = None
    application_id: UUID | None = None
    converted_at: datetime | None = None
    lost_reason_id: UUID | None = None
    lost_comment: str | None = None
    lost_at: datetime | None = None
    last_contact_at: datetime | None = None
    next_contact_at: datetime | None = None
    next_contact_note: str | None = None
    stage_entered_at: datetime
    created_at: datetime
    updated_at: datetime
    # Embedded display labels
    stage_name: str | None = None
    stage_color: str | None = None
    pipeline_name: str | None = None
    source_name: str | None = None
    source_code: str | None = None
    branch_name: str | None = None
    program_name: str | None = None
    assigned_to_name: str | None = None


class LeadBoardStage(AppSchema):
    id: UUID
    name: str
    color: str | None = None
    is_terminal: bool
    order_index: int
    leads: list[LeadRead]


class LeadBoardResponse(AppSchema):
    pipeline_id: UUID
    pipeline_name: str
    stages: list[LeadBoardStage]
