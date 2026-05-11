"""Referrals HTTP surface (phase 2)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import Permission
from app.modules.applicants.models import Applicant
from app.modules.referrals.models import Referral
from app.modules.referrals.models import ReferralPayout
from app.modules.referrals.schemas import (
    ApplyToContractPayload,
    ApplyToContractResponse,
    AttachReferrerPayload,
    CashPayoutRequestPayload,
    ReferralAvailableBalance,
    ReferralCodeRead,
    ReferralPayoutRead,
    ReferralRead,
    ReferralSettingsRead,
    RejectPayoutPayload,
)
from app.modules.referrals.service import ReferralService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> ReferralService:
    return ReferralService(session)


def _build_share_url(code: str) -> str:
    base = (settings.public_base_url or "").rstrip("/")
    # Applicant signup lives on the SPA at /auth/applicant; passing
    # ?ref=CODE lets the frontend persist the code and forward it on
    # POST /applicants/me.
    if not base:
        return f"/auth/applicant?ref={code}"
    return f"{base}/auth/applicant?ref={code}"


# ============================================================================
# Code + share link (any authenticated user gets their own)
# ============================================================================
@router.get("/me/code", response_model=ReferralCodeRead)
async def my_referral_code(
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> ReferralCodeRead:
    code = await svc.ensure_code_for_user(UUID(current.user_id))
    await svc.session.commit()
    return ReferralCodeRead(referral_code=code, share_url=_build_share_url(code))


# ============================================================================
# Own referrals (the user looks at who they invited and the bonus status)
# ============================================================================
@router.get("/me", response_model=list[ReferralRead])
async def my_referrals(
    status_filter: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> list[ReferralRead]:
    rows = await svc.list_for_referrer(UUID(current.user_id), status=status_filter)
    return await _enrich_referrals(svc.session, rows)


# ============================================================================
# Staff: list referrals (admin / accountant / operator with leads-list right)
# ============================================================================
@router.get(
    "",
    response_model=list[ReferralRead],
    dependencies=[Depends(require_permission(Permission.APPLICANTS_LIST))],
)
async def list_referrals(
    status_filter: str | None = None,
    referrer_user_id: UUID | None = None,
    svc: ReferralService = Depends(_service),
) -> list[ReferralRead]:
    stmt = select(Referral)
    if status_filter:
        stmt = stmt.where(Referral.status == status_filter)
    if referrer_user_id is not None:
        stmt = stmt.where(Referral.referrer_user_id == referrer_user_id)
    stmt = stmt.order_by(Referral.created_at.desc())
    rows = list((await svc.session.scalars(stmt)).all())
    return await _enrich_referrals(svc.session, rows)


# ============================================================================
# Attach / change referrer on an existing applicant (staff)
# ============================================================================
@router.post(
    "/applicants/{applicant_id}/attach",
    response_model=ReferralRead,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def attach_referrer(
    applicant_id: UUID,
    payload: AttachReferrerPayload,
    svc: ReferralService = Depends(_service),
) -> ReferralRead:
    """Operator/admin links an existing applicant to a referrer by code.

    Fails 409 if a referral row already exists for that applicant — caller
    should DELETE first if they need to swap referrers.
    """
    applicant = await svc.session.get(Applicant, applicant_id)
    if applicant is None:
        raise NotFoundError("Applicant not found")
    referrer_user_id = await svc.find_referrer_by_code(payload.referrer_code)
    if referrer_user_id is None:
        raise ValidationError("Bunday referal kod topilmadi")
    if referrer_user_id == applicant.user_id:
        raise ValidationError("Foydalanuvchi o'z-o'zini taklif qila olmaydi")
    existing = await svc.referrals.get_by_applicant(applicant_id)
    if existing is not None:
        raise ConflictError("Bu abituriyentga allaqachon referrer biriktirilgan")

    ref = Referral(
        referrer_user_id=referrer_user_id,
        referred_applicant_id=applicant_id,
        status="pending",
        source="manual",
    )
    svc.session.add(ref)
    await svc.session.flush()
    await svc.session.commit()

    enriched = await _enrich_referrals(svc.session, [ref])
    return enriched[0]


# ============================================================================
# Detach (admin only — phase 2 doesn't auto-grade reversals)
# ============================================================================
@router.delete(
    "/applicants/{applicant_id}/attach",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def detach_referrer(
    applicant_id: UUID,
    svc: ReferralService = Depends(_service),
):
    existing = await svc.referrals.get_by_applicant(applicant_id)
    if existing is None:
        return
    if existing.status not in ("pending", "cancelled"):
        # active / spent / paid — refuse to silently delete a paid bonus
        raise ForbiddenError(
            f"Bu referal allaqachon '{existing.status}' holatda — avval bekor qiling"
        )
    await svc.session.delete(existing)
    await svc.session.commit()


# ============================================================================
# Settings (admin)
# ============================================================================
@router.get(
    "/settings",
    response_model=ReferralSettingsRead,
    dependencies=[Depends(require_permission(Permission.USERS_UPDATE))],
)
async def get_settings(svc: ReferralService = Depends(_service)) -> ReferralSettingsRead:
    obj = await svc.get_settings()
    await svc.session.commit()
    return ReferralSettingsRead.model_validate(obj)


# ============================================================================
# Available balance (current user)
# ============================================================================
@router.get("/me/available", response_model=ReferralAvailableBalance)
async def my_available_balance(
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> ReferralAvailableBalance:
    user_id = UUID(current.user_id)
    active = await svc.referrals.count_active_for_referrer(user_id)
    available = await svc.referrals.count_available_for_referrer(user_id)
    settings = await svc.get_settings()
    return ReferralAvailableBalance(
        active_count=active,
        earmarked_count=max(0, active - available),
        available_count=available,
        available_amount=settings.reward_amount * available,
    )


# ============================================================================
# Apply N referrals as contract discount
# ============================================================================
@router.post(
    "/apply-to-contract",
    response_model=ApplyToContractResponse,
    dependencies=[Depends(require_permission(Permission.CONTRACTS_CREATE))],
)
async def apply_to_contract(
    payload: ApplyToContractPayload,
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> ApplyToContractResponse:
    """Spend N active referrals against a contract's total_amount.

    Permission: CONTRACTS_CREATE (operator/admin). The bonus is debited
    from the contract OWNER (applicant), not from the operator who
    happens to be filling in the form.
    """
    result = await svc.apply_to_contract(
        contract_id=payload.contract_id,
        count=payload.count,
        actor_user_id=UUID(current.user_id),
    )
    await svc.session.commit()
    return ApplyToContractResponse(**result)


# ============================================================================
# Cash payout — request + queue + accountant flow
# ============================================================================
@router.post("/me/cash-payout", response_model=ReferralPayoutRead)
async def request_cash_payout(
    payload: CashPayoutRequestPayload,
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> ReferralPayoutRead:
    payout = await svc.request_cash_payout(
        referrer_user_id=UUID(current.user_id),
        count=payload.count,
        notes=payload.notes,
    )
    await svc.session.commit()
    return ReferralPayoutRead.model_validate(payout)


@router.get("/me/payouts", response_model=list[ReferralPayoutRead])
async def my_payouts(
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> list[ReferralPayoutRead]:
    rows = await svc.list_payouts_for_referrer(UUID(current.user_id))
    return await _enrich_payouts(svc.session, rows)


@router.get(
    "/payouts",
    response_model=list[ReferralPayoutRead],
    dependencies=[Depends(require_permission(Permission.PAYMENTS_READ))],
)
async def list_payouts(
    status_filter: str | None = None,
    svc: ReferralService = Depends(_service),
) -> list[ReferralPayoutRead]:
    stmt = select(ReferralPayout)
    if status_filter:
        stmt = stmt.where(ReferralPayout.status == status_filter)
    stmt = stmt.order_by(ReferralPayout.created_at.desc())
    rows = list((await svc.session.scalars(stmt)).all())
    return await _enrich_payouts(svc.session, rows)


@router.post(
    "/payouts/{payout_id}/approve",
    response_model=ReferralPayoutRead,
    dependencies=[Depends(require_permission(Permission.PAYMENTS_CONFIRM))],
)
async def approve_payout(
    payout_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> ReferralPayoutRead:
    payout = await svc.approve_payout(payout_id, approver_user_id=UUID(current.user_id))
    await svc.session.commit()
    enriched = await _enrich_payouts(svc.session, [payout])
    return enriched[0]


@router.post(
    "/payouts/{payout_id}/pay",
    response_model=ReferralPayoutRead,
    dependencies=[Depends(require_permission(Permission.PAYMENTS_CONFIRM))],
)
async def mark_payout_paid(
    payout_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> ReferralPayoutRead:
    payout = await svc.mark_payout_paid(payout_id, payer_user_id=UUID(current.user_id))
    await svc.session.commit()
    enriched = await _enrich_payouts(svc.session, [payout])
    return enriched[0]


@router.post(
    "/payouts/{payout_id}/reject",
    response_model=ReferralPayoutRead,
    dependencies=[Depends(require_permission(Permission.PAYMENTS_CONFIRM))],
)
async def reject_payout(
    payout_id: UUID,
    payload: RejectPayoutPayload,
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> ReferralPayoutRead:
    payout = await svc.reject_payout(
        payout_id, reviewer_user_id=UUID(current.user_id), reason=payload.reason,
    )
    await svc.session.commit()
    enriched = await _enrich_payouts(svc.session, [payout])
    return enriched[0]


async def _enrich_payouts(
    session: AsyncSession, rows: list[ReferralPayout],
) -> list[ReferralPayoutRead]:
    if not rows:
        return []
    from app.modules.users.models import User
    ids = {p.referrer_user_id for p in rows}
    name_by_id: dict[UUID, tuple[str | None, str | None]] = {}
    stmt = select(User.id, User.full_name, User.phone).where(User.id.in_(ids))
    for uid, full_name, phone in (await session.execute(stmt)).all():
        name_by_id[uid] = (full_name, phone)
    out: list[ReferralPayoutRead] = []
    for p in rows:
        rec = ReferralPayoutRead.model_validate(p)
        n, ph = name_by_id.get(p.referrer_user_id, (None, None))
        rec.referrer_full_name = n
        rec.referrer_phone = ph
        out.append(rec)
    return out


# ============================================================================
# Helpers
# ============================================================================
async def _enrich_referrals(session: AsyncSession, rows: list[Referral]) -> list[ReferralRead]:
    """Attach the referred applicant's full name so the UI doesn't need a join."""
    if not rows:
        return []
    ids = {r.referred_applicant_id for r in rows}
    name_by_id: dict[UUID, str] = {}
    stmt = select(
        Applicant.id, Applicant.last_name, Applicant.first_name, Applicant.other_name,
    ).where(Applicant.id.in_(ids))
    for aid, last, first, other in (await session.execute(stmt)).all():
        name_by_id[aid] = " ".join(filter(None, [last, first, other])).strip()

    out: list[ReferralRead] = []
    for r in rows:
        rec = ReferralRead.model_validate(r)
        rec.referred_full_name = name_by_id.get(r.referred_applicant_id)
        out.append(rec)
    return out
