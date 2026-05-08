from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema
from app.db.enums import ContractStatus, ContractType, Language, PartyRole


# ---------- Template ----------
class ContractTemplateBase(AppSchema):
    name: str = Field(min_length=1, max_length=255)
    body_two_party: str | None = None
    body_three_party: str | None = None
    is_active: bool = False


class ContractTemplateCreate(ContractTemplateBase):
    pass


class ContractTemplateUpdate(AppSchema):
    name: str | None = Field(default=None, max_length=255)
    body_two_party: str | None = None
    body_three_party: str | None = None
    is_active: bool | None = None


class ContractTemplateRead(IdSchema, TimestampedSchema, ContractTemplateBase):
    version: int


# ---------- Settings ----------
class ContractSettingsBase(AppSchema):
    default_contract_type: ContractType = ContractType.TWO_PARTY
    auto_generate_pdf: bool = True
    pdf_page_size: str = Field(default="A4", max_length=10)
    company_name: str = Field(default="Ta'lim muassasasi", max_length=200)
    company_address: str | None = None
    director_name: str | None = Field(default=None, max_length=100)


class ContractSettingsUpdate(AppSchema):
    default_contract_type: ContractType | None = None
    auto_generate_pdf: bool | None = None
    pdf_page_size: str | None = Field(default=None, max_length=10)
    company_name: str | None = Field(default=None, max_length=200)
    company_address: str | None = None
    director_name: str | None = Field(default=None, max_length=100)


class ContractSettingsRead(IdSchema, TimestampedSchema, ContractSettingsBase):
    pass


# ---------- Party ----------
class ContractPartyBase(AppSchema):
    party_role: PartyRole
    full_name: str = Field(min_length=1, max_length=255)
    pinfl: str | None = Field(default=None, max_length=14)
    passport_series: str | None = Field(default=None, max_length=2)
    passport_number: str | None = Field(default=None, max_length=7)
    phone: str | None = Field(default=None, max_length=20)
    relationship: str | None = Field(default=None, max_length=100)
    address: str | None = None


class ContractPartyCreate(ContractPartyBase):
    pass


class ContractPartyRead(IdSchema, TimestampedSchema, ContractPartyBase):
    contract_id: UUID


# ---------- Additional party (operator-supplied for 3-party contracts) ----------
class AdditionalParty(AppSchema):
    party_role: PartyRole = PartyRole.SPONSOR  # SPONSOR or PARENT
    full_name: str = Field(min_length=1, max_length=255)
    pinfl: str | None = Field(default=None, max_length=14)
    passport_series: str | None = Field(default=None, max_length=2)
    passport_number: str | None = Field(default=None, max_length=7)
    phone: str | None = Field(default=None, max_length=20)
    relationship: str | None = Field(default=None, max_length=100)
    address: str | None = None


# ---------- Contract ----------
class ContractCreate(AppSchema):
    """Operator-driven contract creation.

    University + student parties are auto-populated from config + applicant
    data. The operator only provides the sponsor/parent for 3-party contracts.
    """

    application_id: UUID
    template_id: UUID
    type: ContractType
    total_amount: Decimal | None = None  # default: offering.tuition_fee
    currency: str = Field(default="UZS", max_length=3)
    additional_party: AdditionalParty | None = None


class ContractSign(AppSchema):
    """No body fields yet — placeholder for future signature payloads."""

    notes: str | None = None


class ContractRead(IdSchema, TimestampedSchema):
    contract_number: str
    application_id: UUID
    template_id: UUID
    type: ContractType
    total_amount: Decimal
    paid_amount: Decimal
    currency: str
    status: ContractStatus
    signed_at: datetime | None = None
    pdf_file_id: UUID | None = None


class ContractDetailed(ContractRead):
    parties: list[ContractPartyRead] = Field(default_factory=list)
