"""Referral business logic.

Phase 1 — settings, code generation, lookups
Phase 2 — applicant.register hook records `pending` rows
Phase 3 — check_qualification(contract_id) activates / reverts based on 25%
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.modules.referrals.models import Referral, ReferralPayout, ReferralSettings
from app.modules.referrals.repository import (
    ReferralPayoutRepository,
    ReferralRepository,
    ReferralSettingsRepository,
)
from app.modules.users.repository import UserRepository

logger = get_logger("referrals")


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

    # ---------- qualification hook (Phase 3) ----------
    async def check_qualification(self, contract_id: UUID) -> None:
        """Activate or revert referrals tied to this contract.

        Called by PaymentsService after every confirm / refund so the
        referrer's bonus state stays in sync with the actual money in.

        Rules:
          - `paid_amount / total_amount >= qualification_percent`:
              any `pending` referral on the contract's applicant becomes
              `active`. We also stamp `contract_id` and `activated_at` so
              the dashboard can show which contract earned each bonus.
          - Below the threshold (e.g. payment was refunded back down):
              `active` rows we previously stamped revert to `pending`.
              `spent_on_contract` / `paid_cash` / `cancelled` are NEVER
              touched here — those are terminal from the referrer's
              perspective and must be reversed by the payout/discount
              workflow instead.
        """
        # Local import keeps the dependency cycle (referrals → contracts → ...)
        # from blowing up at module load.
        from app.modules.contracts.models import Contract
        from app.modules.applications.models import Application

        contract = await self.session.get(Contract, contract_id)
        if contract is None:
            return
        if not contract.total_amount or contract.total_amount == 0:
            return

        # Walk contract → application → applicant to find which applicant
        # this contract belongs to.
        application = await self.session.get(Application, contract.application_id)
        if application is None:
            return
        applicant_id = application.applicant_id

        settings = await self.get_settings()
        threshold = Decimal(settings.qualification_percent) / Decimal("100")
        paid_ratio = Decimal(contract.paid_amount or 0) / Decimal(contract.total_amount)

        # One referral row per applicant (unique constraint), so just fetch it.
        ref = await self.referrals.get_by_applicant(applicant_id)
        if ref is None:
            return

        now = datetime.now(timezone.utc)

        if paid_ratio >= threshold:
            # Activation path
            if ref.status == "pending":
                ref.status = "active"
                ref.activated_at = now
                if ref.contract_id is None:
                    ref.contract_id = contract_id
                await self.session.flush()
                logger.info(
                    "referrals.activated",
                    referral_id=str(ref.id),
                    referrer_user_id=str(ref.referrer_user_id),
                    applicant_id=str(applicant_id),
                    contract_id=str(contract_id),
                    paid_ratio=str(paid_ratio),
                )
            elif ref.status == "active" and ref.contract_id is None:
                # Backfill the contract pointer for older active rows.
                ref.contract_id = contract_id
                await self.session.flush()
        else:
            # Reversion path — only undo what WE earlier auto-activated for
            # THIS contract. Don't touch other states.
            if ref.status == "active" and ref.contract_id == contract_id:
                ref.status = "pending"
                ref.activated_at = None
                await self.session.flush()
                logger.info(
                    "referrals.reverted",
                    referral_id=str(ref.id),
                    referrer_user_id=str(ref.referrer_user_id),
                    contract_id=str(contract_id),
                    paid_ratio=str(paid_ratio),
                )

    # ---------- Redemption (Phase 4) ----------
    async def apply_to_contract(
        self, *, contract_id: UUID, count: int, actor_user_id: UUID,
    ) -> dict:
        """Spend N of the actor's active referrals on a contract.

        Picks the N oldest active referrals not earmarked for a cash
        payout, marks them `spent_on_contract` with `applied_contract_id`
        and `payout_at = now()`, and subtracts `N × reward_amount` from
        the contract's `total_amount`. Returns a summary dict.
        """
        from app.modules.applications.models import Application
        from app.modules.contracts.models import Contract

        if count <= 0:
            raise ValueError("count must be > 0")

        contract = await self.session.get(Contract, contract_id)
        if contract is None:
            raise NotFoundError("Shartnoma topilmadi")

        # Resolve the contract's owner (applicant user_id) so we can
        # confirm the actor is either the owner OR a staff member.
        from app.modules.applicants.models import Applicant
        owner_user_id = await self.session.scalar(
            select(Applicant.user_id)
            .join(Application, Application.applicant_id == Applicant.id)
            .where(Application.id == contract.application_id)
        )

        # actor must own the contract OR be a staff member calling on the
        # owner's behalf. Staff-permission gating is done at the router
        # level; here we just sanity-check we're spending the right
        # person's bonuses.
        referrer_id = actor_user_id
        if owner_user_id and owner_user_id != actor_user_id:
            # Staff path — credit is debited from the contract owner, not
            # from the operator filling the form.
            referrer_id = owner_user_id

        available = await self.referrals.available_for_referrer(referrer_id, limit=count)
        if len(available) < count:
            raise ValidationError(
                f"Faqat {len(available)} ta faol referal mavjud (talab qilingan: {count})"
            )

        settings = await self.get_settings()
        reward = Decimal(settings.reward_amount)
        total_discount = reward * count
        now = datetime.now(timezone.utc)

        for ref in available[:count]:
            ref.status = "spent_on_contract"
            ref.applied_contract_id = contract_id
            ref.payout_at = now
        contract.total_amount = (Decimal(contract.total_amount or 0) - total_discount)
        if contract.total_amount < 0:
            contract.total_amount = Decimal("0")
        await self.session.flush()

        logger.info(
            "referrals.applied",
            count=count,
            contract_id=str(contract_id),
            referrer_user_id=str(referrer_id),
            discount=str(total_discount),
            new_total=str(contract.total_amount),
        )
        return {
            "count": count,
            "discount": str(total_discount),
            "contract_id": str(contract_id),
            "new_total_amount": str(contract.total_amount),
        }

    # ---------- Cash payout queue ----------
    async def request_cash_payout(
        self, *, referrer_user_id: UUID, count: int, notes: str | None = None,
    ) -> ReferralPayout:
        """Reserve N active referrals into a fresh `requested` payout row."""
        if count <= 0:
            raise ValueError("count must be > 0")
        available = await self.referrals.available_for_referrer(referrer_user_id, limit=count)
        if len(available) < count:
            raise ValidationError(
                f"Faqat {len(available)} ta faol referal mavjud (talab qilingan: {count})"
            )
        settings = await self.get_settings()
        reward = Decimal(settings.reward_amount)
        payout = ReferralPayout(
            referrer_user_id=referrer_user_id,
            amount=reward * count,
            referral_count=count,
            status="requested",
            notes=notes,
        )
        self.session.add(payout)
        await self.session.flush()
        for ref in available[:count]:
            ref.cash_payout_id = payout.id
        await self.session.flush()
        logger.info(
            "referrals.payout_requested",
            payout_id=str(payout.id),
            referrer_user_id=str(referrer_user_id),
            count=count,
            amount=str(payout.amount),
        )
        return payout

    async def approve_payout(self, payout_id: UUID, *, approver_user_id: UUID) -> ReferralPayout:
        payout = await self.payouts.get(payout_id)
        if payout is None:
            raise NotFoundError("To'lov so'rovi topilmadi")
        if payout.status != "requested":
            raise ValidationError(
                f"Faqat 'requested' holatdagi so'rovni tasdiqlash mumkin (hozir: {payout.status})"
            )
        payout.status = "approved"
        payout.approved_by_user_id = approver_user_id
        payout.approved_at = datetime.now(timezone.utc)
        await self.session.flush()
        return payout

    async def mark_payout_paid(
        self, payout_id: UUID, *, payer_user_id: UUID,
    ) -> ReferralPayout:
        """Final step — referrer received the cash; flip referrals to `paid_cash`."""
        payout = await self.payouts.get(payout_id)
        if payout is None:
            raise NotFoundError("To'lov so'rovi topilmadi")
        if payout.status not in ("requested", "approved"):
            raise ValidationError(
                f"'paid' qilish uchun so'rov requested/approved bo'lishi kerak (hozir: {payout.status})"
            )
        # Auto-approve if accountant skipped the review step.
        if payout.status == "requested":
            payout.status = "approved"
            payout.approved_by_user_id = payer_user_id
            payout.approved_at = datetime.now(timezone.utc)
        payout.status = "paid"
        payout.paid_at = datetime.now(timezone.utc)
        # Flip the linked referrals.
        rows = await self.referrals.list_for_payout(payout_id)
        now = datetime.now(timezone.utc)
        for ref in rows:
            ref.status = "paid_cash"
            ref.payout_at = now
        await self.session.flush()
        logger.info(
            "referrals.payout_paid",
            payout_id=str(payout_id),
            referrer_user_id=str(payout.referrer_user_id),
            count=len(rows),
            amount=str(payout.amount),
        )
        return payout

    async def reject_payout(
        self, payout_id: UUID, *, reviewer_user_id: UUID, reason: str,
    ) -> ReferralPayout:
        payout = await self.payouts.get(payout_id)
        if payout is None:
            raise NotFoundError("To'lov so'rovi topilmadi")
        if payout.status not in ("requested", "approved"):
            raise ValidationError(
                f"Rad qilish uchun so'rov requested/approved bo'lishi kerak (hozir: {payout.status})"
            )
        payout.status = "rejected"
        payout.approved_by_user_id = reviewer_user_id
        payout.rejected_reason = (reason or "").strip()[:500] or None
        # Free the reserved referrals so they're spendable again.
        rows = await self.referrals.list_for_payout(payout_id)
        for ref in rows:
            ref.cash_payout_id = None
        await self.session.flush()
        return payout

    async def cancel_for_applicant(self, applicant_id: UUID, *, reason: str) -> None:
        """Mark the applicant's referral row as cancelled.

        Used by contract/application cancellation flows so a bonus that
        never qualifies is removed from the referrer's dashboard. Only
        pending / active rows can be cancelled here — once a bonus has
        been spent or paid out we keep the audit trail intact.
        """
        ref = await self.referrals.get_by_applicant(applicant_id)
        if ref is None:
            return
        if ref.status in ("spent_on_contract", "paid_cash", "cancelled"):
            return
        ref.status = "cancelled"
        ref.cancelled_at = datetime.now(timezone.utc)
        ref.cancelled_reason = reason[:500] if reason else None
        await self.session.flush()
        logger.info(
            "referrals.cancelled",
            referral_id=str(ref.id),
            applicant_id=str(applicant_id),
            reason=reason,
        )
