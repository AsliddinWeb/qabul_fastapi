"""Referral business logic — kept thin in phase 1.

Surface area today:
  - settings get/update (admin-facing later)
  - referral_code generation for users that don't have one
  - lookup helpers (find_referrer_by_code, list_for_referrer)

Phase-2+ will extend this with:
  - register_referral(referrer_code, applicant_id, source)
  - check_qualification(contract_id)              ← payment-confirmed hook
  - spend_on_contract(referrals, contract_id)
  - request_cash_payout(referrer_user_id, count)
  - approve_payout / mark_paid / reject_payout
"""
from __future__ import annotations

import secrets
import string
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.referrals.models import Referral, ReferralPayout, ReferralSettings
from app.modules.referrals.repository import (
    ReferralPayoutRepository,
    ReferralRepository,
    ReferralSettingsRepository,
)
from app.modules.users.repository import UserRepository


_ALPHABET = string.ascii_uppercase + string.digits  # 26 + 10 = 36 chars
# 6 chars from 36-symbol alphabet = 36^6 ≈ 2.1B combinations — plenty for a
# university and small enough to share over voice / WhatsApp.
_CODE_LEN = 6


def _generate_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LEN))


class ReferralService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.referrals = ReferralRepository(session)
        self.payouts = ReferralPayoutRepository(session)
        self.settings = ReferralSettingsRepository(session)
        self.users = UserRepository(session)

    # ---------- settings ----------
    async def get_settings(self) -> ReferralSettings:
        obj = await self.settings.get_singleton()
        if obj is None:
            obj = ReferralSettings(
                reward_amount=Decimal("500000"),
                qualification_percent=Decimal("25"),
                is_active=True,
            )
            self.session.add(obj)
            await self.session.flush()
        return obj

    # ---------- referral code ----------
    async def ensure_code_for_user(self, user_id: UUID) -> str:
        """Return the user's referral_code, generating one if missing.

        Migration 05 backfilled every existing user; this helper is the
        runtime path for new sign-ups and a safety net if a row somehow
        ended up without a code.
        """
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if user.referral_code:
            return user.referral_code
        # Pick a fresh code; retry on collision (extremely unlikely).
        for _ in range(8):
            code = _generate_code()
            existing = await self.users.get_by(referral_code=code)
            if existing is None:
                user.referral_code = code
                await self.session.flush()
                return code
        raise RuntimeError("Could not allocate a unique referral code after 8 tries")

    async def find_referrer_by_code(self, code: str) -> UUID | None:
        if not code:
            return None
        user = await self.users.get_by(referral_code=code.upper().strip())
        return user.id if user else None

    # ---------- queries ----------
    async def list_for_referrer(
        self, referrer_user_id: UUID, *, status: str | None = None,
    ) -> list[Referral]:
        return await self.referrals.list_for_referrer(referrer_user_id, status=status)

    async def list_payouts_for_referrer(self, referrer_user_id: UUID) -> list[ReferralPayout]:
        return await self.payouts.list_for_referrer(referrer_user_id)
