"""Referral programme ORM models.

A referrer (an existing user) invites a new applicant. When the referee's
contract has had at least `qualification_percent` confirmed, the referral
flips from `pending` to `active`. From there the referrer can either spend
it as a discount on their own contract (`spent_on_contract`) or request a
cash payout via `referral_payouts` (`paid_cash`).

See migrations/sql/2026-04-rewrite/05_referrals.sql for the schema and
defaults.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class ReferralSettings(UUIDPKMixin, TimestampMixin, Base):
    """Singleton — knobs the admin can tune from /admin."""

    __tablename__ = "referral_settings"

    reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("500000"),
        server_default="500000",
    )
    # Percentage (0..100) of total_amount that must be confirmed via
    # payments before a referral row goes from pending → active.
    qualification_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("25"),
        server_default="25",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
    )


class Referral(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "referrals"

    referrer_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    referred_applicant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applicants.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    contract_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # pending → active → spent_on_contract / paid_cash / cancelled
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="pending", server_default="pending",
    )
    reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("500000"),
        server_default="500000",
    )
    # "link" = via ?ref=CODE, "manual" = typed in by operator/applicant
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual", server_default="manual",
    )

    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payout_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    applied_contract_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    cash_payout_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("referral_payouts.id", ondelete="SET NULL"),
        nullable=True,
    )

    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes:            Mapped[str | None] = mapped_column(Text, nullable=True)


class ReferralPayout(UUIDPKMixin, TimestampMixin, Base):
    """Cash withdrawal queue — accountant processes these."""

    __tablename__ = "referral_payouts"

    referrer_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    amount:          Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    referral_count:  Mapped[int]     = mapped_column(Integer, nullable=False)

    # requested → approved → paid / rejected
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="requested", server_default="requested",
    )

    requested_at:        Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    approved_by_user_id: Mapped[UUID | None]      = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at:         Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at:             Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason:     Mapped[str | None]       = mapped_column(Text, nullable=True)
    notes:               Mapped[str | None]       = mapped_column(Text, nullable=True)
