"""Referral repositories — thin SQL helpers over the three referral tables."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.core.repository import BaseRepository
from app.modules.referrals.models import Referral, ReferralPayout, ReferralSettings


class ReferralSettingsRepository(BaseRepository[ReferralSettings]):
    model = ReferralSettings

    async def get_singleton(self) -> ReferralSettings | None:
        stmt = select(ReferralSettings).limit(1)
        return (await self.session.scalars(stmt)).first()


class ReferralRepository(BaseRepository[Referral]):
    model = Referral

    async def get_by_applicant(self, applicant_id: UUID) -> Referral | None:
        return await self.get_by(referred_applicant_id=applicant_id)

    async def list_for_referrer(
        self, referrer_user_id: UUID, *, status: str | None = None,
    ) -> list[Referral]:
        stmt = select(Referral).where(Referral.referrer_user_id == referrer_user_id)
        if status is not None:
            stmt = stmt.where(Referral.status == status)
        stmt = stmt.order_by(Referral.created_at.desc())
        return list((await self.session.scalars(stmt)).all())

    async def list_for_contract(self, contract_id: UUID) -> list[Referral]:
        """Referrals whose qualification depends on this contract's payments."""
        stmt = select(Referral).where(Referral.contract_id == contract_id)
        return list((await self.session.scalars(stmt)).all())

    async def count_active_for_referrer(self, referrer_user_id: UUID) -> int:
        stmt = (
            select(func.count(Referral.id))
            .where(
                Referral.referrer_user_id == referrer_user_id,
                Referral.status == "active",
            )
        )
        return await self.session.scalar(stmt) or 0

    async def sum_reward_active_for_referrer(self, referrer_user_id: UUID):
        stmt = (
            select(func.coalesce(func.sum(Referral.reward_amount), 0))
            .where(
                Referral.referrer_user_id == referrer_user_id,
                Referral.status == "active",
            )
        )
        return await self.session.scalar(stmt) or 0


class ReferralPayoutRepository(BaseRepository[ReferralPayout]):
    model = ReferralPayout

    async def list_for_referrer(self, referrer_user_id: UUID) -> list[ReferralPayout]:
        stmt = (
            select(ReferralPayout)
            .where(ReferralPayout.referrer_user_id == referrer_user_id)
            .order_by(ReferralPayout.created_at.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def list_pending(self) -> list[ReferralPayout]:
        stmt = (
            select(ReferralPayout)
            .where(ReferralPayout.status.in_(("requested", "approved")))
            .order_by(ReferralPayout.created_at.asc())
        )
        return list((await self.session.scalars(stmt)).all())
