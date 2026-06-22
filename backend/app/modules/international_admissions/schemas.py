"""Pydantic schemas for the international admissions module."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema


class IntlApplyPayload(AppSchema):
    """Public submission body. Multipart fields come in as form data.

    Honeypot + time-trap fields are NOT in this schema — they're
    inspected at the router level so a bot's response never reaches
    the validator (cheaper rejection, no DB writes).
    """

    full_name:       str = Field(min_length=3, max_length=200)
    country:         str = Field(min_length=2, max_length=60)
    passport_number: str = Field(min_length=4, max_length=40)
    birth_date:      date
    phone:           str = Field(min_length=6, max_length=30)
    email:           EmailStr
    program:         str = Field(min_length=1, max_length=20)   # 'Bachelor' / 'Master'
    faculty_code:    str = Field(min_length=1, max_length=20)
    faculty_text:    str = Field(min_length=1, max_length=120)
    language:        str | None = Field(default=None, max_length=5)


class IntlAdvanceStage(AppSchema):
    """Staff bumps the stage by ±1. Min 0, max 5 in service-level check."""

    direction: str = Field(pattern=r"^(next|back)$")


class IntlReject(AppSchema):
    reason: str | None = Field(default=None, max_length=500)


class IntlNotesUpdate(AppSchema):
    notes: str | None = Field(default=None, max_length=5000)


class IntlApplicationRead(IdSchema, TimestampedSchema):
    ref_number:      str
    full_name:       str
    country:         str
    passport_number: str
    birth_date:      date
    phone:           str
    email:           str
    program:         str
    faculty_code:    str
    faculty_text:    str
    passport_file_id: UUID | None = None
    diploma_file_id:  UUID | None = None
    photo_file_id:    UUID | None = None
    stage:           int
    rejected:        bool
    rejection_reason: str | None = None
    notes:           str | None = None
    language:        str | None = None
    # Audit fields exposed only on the detail view — never on public
    # responses.
    submitter_ip:        str | None = None
    submitter_user_agent: str | None = None


class IntlApplicationListItem(IdSchema, TimestampedSchema):
    """Slim shape for the staff list page — no audit / files / notes."""

    ref_number:   str
    full_name:    str
    country:      str
    passport_number: str
    program:      str
    faculty_text: str
    phone:        str
    email:        str
    stage:        int
    rejected:     bool


class IntlApplyResponse(AppSchema):
    """Returned to the public-form caller. Slim so we don't echo the
    full audit trail back to the browser."""

    id:         UUID
    ref_number: str
    submitted_at: datetime
