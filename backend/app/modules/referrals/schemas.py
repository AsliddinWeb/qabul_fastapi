"""Pydantic surface for the referrals module."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema


class ReferralCodeRead(AppSchema):
    """Returned by GET /referrals/me/code."""

    referral_code: str
    share_url: str


class ReferralRead(IdSchema, TimestampedSchema):
    referrer_user_id: UUID
    referred_applicant_id: UUID
    contract_id: UUID | None = None
    status: str
    reward_amount: Decimal
    source: str
    activated_at: datetime | None = None
    cancelled_at: datetime | None = None
    payout_at:    datetime | None = None
    applied_contract_id: UUID | None = None
    cash_payout_id:      UUID | None = None
    cancelled_reason: str | None = None
    notes: str | None = None

    # Convenience fields filled by the router (joined applicant / contract data)
    referred_full_name: str | None = None


class ReferralSettingsRead(IdSchema, TimestampedSchema):
    reward_amount:         Decimal
    qualification_percent: Decimal
    is_active:             bool


class ReferralSettingsUpdate(AppSchema):
    reward_amount:         Decimal | None = Field(default=None, gt=0)
    qualification_percent: Decimal | None = Field(default=None, ge=0, le=100)
    is_active:             bool | None    = None


class AttachReferrerPayload(AppSchema):
    """Admin/operator attaches a referrer to an existing applicant."""

    referrer_code: str = Field(min_length=4, max_length=8)
