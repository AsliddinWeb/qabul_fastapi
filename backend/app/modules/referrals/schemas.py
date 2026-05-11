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


# ---------- Phase 4: redemption ----------
class ApplyToContractPayload(AppSchema):
    contract_id: UUID
    count: int = Field(ge=1, le=100)


class ApplyToContractResponse(AppSchema):
    count: int
    discount: Decimal
    contract_id: UUID
    new_total_amount: Decimal


class CashPayoutRequestPayload(AppSchema):
    count: int = Field(ge=1, le=100)
    notes: str | None = Field(default=None, max_length=1000)


class RejectPayoutPayload(AppSchema):
    reason: str = Field(min_length=2, max_length=500)


class ReferralPayoutRead(IdSchema, TimestampedSchema):
    referrer_user_id: UUID
    amount: Decimal
    referral_count: int
    status: str
    requested_at: datetime
    approved_by_user_id: UUID | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    rejected_reason: str | None = None
    notes: str | None = None

    # Filled by the router for nicer UI: who is the inviter
    referrer_full_name: str | None = None
    referrer_phone: str | None = None


class ReferralAvailableBalance(AppSchema):
    """`GET /referrals/me/available` — what the user can still spend."""

    active_count:        int
    earmarked_count:     int      # tied up in a pending payout
    available_count:     int      # truly spendable right now
    available_amount:    Decimal  # available_count * reward_amount


# ---------- Phase 5: admin stats ----------
class TopReferrer(AppSchema):
    user_id:        UUID
    full_name:      str | None = None
    phone:          str | None = None
    referral_code:  str | None = None
    total_invited:  int
    active_count:   int
    spent_count:    int
    paid_count:     int
    earned_amount:  Decimal      # spent + paid * reward_amount


class ReferralStats(AppSchema):
    total_referrals:        int
    by_status:              dict[str, int]
    total_discount_amount:  Decimal     # SUM(reward_amount) on spent_on_contract rows
    total_cash_paid:        Decimal     # SUM(amount) on referral_payouts where status=paid
    cash_pending_count:     int         # payouts in requested/approved
    cash_pending_amount:    Decimal
    top_referrers:          list[TopReferrer]
    # Monthly trend (last 6 months) — counts of new referrals registered.
    monthly_trend:          list[dict]
