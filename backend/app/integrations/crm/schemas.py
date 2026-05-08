"""Outbound payloads sent to the external CRM.

These are NOT internal DB models — they are the wire-format contract.
Keep them stable; version via the URL path on the CRM side.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LeadSource(str, Enum):
    SELF_REGISTRATION = "self_registration"  # abituriyent o'zi ro'yxatdan o'tdi
    OPERATOR_MANUAL = "operator_manual"      # operator qo'lda kiritdi
    LANDING_FORM = "landing_form"            # landing'dagi qo'lda yuborilgan forma


class ApplicantLeadPassport(BaseModel):
    series: str
    number: str
    pinfl: str | None = None


class ApplicantLeadProgram(BaseModel):
    program_id: str
    program_code: str | None = None
    program_name: str | None = None
    education_form: str | None = None  # kunduzgi/sirtqi/...
    language: str | None = None        # uz/ru/en


class ApplicantLead(BaseModel):
    """Payload sent to CRM when a new applicant is created."""

    model_config = ConfigDict(extra="forbid")

    # Idempotency key — CRM must dedupe on this.
    external_id: str = Field(description="Stable applicant UUID from this system")

    source: LeadSource

    # Contact
    phone: str
    email: str | None = None

    # Identity
    first_name: str
    last_name: str
    middle_name: str | None = None
    birth_date: date | None = None
    gender: str | None = None  # male/female

    # Optional structured data (CRM may ignore)
    passport: ApplicantLeadPassport | None = None
    program: ApplicantLeadProgram | None = None

    # Free-form metadata for CRM custom fields
    metadata: dict[str, Any] = Field(default_factory=dict)

    # When the lead was created in our system (UTC)
    created_at: datetime


class ApplicantStatusUpdate(BaseModel):
    """Payload for status changes (e.g. accepted/rejected/enrolled)."""

    model_config = ConfigDict(extra="forbid")

    external_id: str
    status: str  # mirror of internal application_status enum
    changed_at: datetime
    note: str | None = None


class ContractCreatedEvent(BaseModel):
    """Payload when a contract is signed."""

    model_config = ConfigDict(extra="forbid")

    external_id: str  # applicant UUID
    contract_number: str
    contract_type: str  # two_party / three_party
    total_amount: float
    currency: str = "UZS"
    signed_at: datetime
