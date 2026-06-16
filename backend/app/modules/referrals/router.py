"""Referrals HTTP surface."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import Permission
from app.modules.applicants.models import Applicant
from app.modules.referrals.models import Referral, ReferralPayout
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
    ReferralStats,
    RejectPayoutPayload,
    TopReferrer,
)
from app.modules.referrals.service import ReferralService
from app.modules.users.models import User

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> ReferralService:
    return ReferralService(session)


def _build_share_url(code: str) -> str:
    base = (settings.public_base_url or "").rstrip("/")
    # Applicant signup lives on the SPA at /app/auth/login (PhoneLoginPage);
    # the SPA is mounted at /app/ in router.history, so the prefix is
    # mandatory or nginx serves the marketing 404. PhoneLoginPage captures
    # ?ref=CODE into sessionStorage so ProfilePage can forward it on
    # POST /applicants/me.
    if not base:
        return f"/app/auth/login?ref={code}"
    return f"{base}/app/auth/login?ref={code}"


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


@router.get("/me/referrer", response_model=ReferralRead | None)
async def my_referrer(
    current: CurrentUser = Depends(get_current_user),
    svc: ReferralService = Depends(_service),
) -> ReferralRead | None:
    """Return the Referral row where the current user IS the referee.

    Used by the applicant's own profile to show a "Sizni X taklif qildi"
    chip — at most one row per user (referred_applicant_id is UNIQUE).
    Returns null body when nobody referred them, so the frontend can
    render a fallback without dealing with a 404.
    """
    # Resolve the current user's applicant row.
    apl_stmt = select(Applicant.id).where(Applicant.user_id == UUID(current.user_id))
    applicant_id = await svc.session.scalar(apl_stmt)
    if applicant_id is None:
        return None
    row = await svc.referrals.get_by_applicant(applicant_id)
    if row is None:
        return None
    enriched = await _enrich_referrals(svc.session, [row])
    return enriched[0] if enriched else None


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
    referred_applicant_id: UUID | None = None,
    svc: ReferralService = Depends(_service),
) -> list[ReferralRead]:
    stmt = select(Referral)
    if status_filter:
        stmt = stmt.where(Referral.status == status_filter)
    if referrer_user_id is not None:
        stmt = stmt.where(Referral.referrer_user_id == referrer_user_id)
    if referred_applicant_id is not None:
        stmt = stmt.where(Referral.referred_applicant_id == referred_applicant_id)
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
    """Attach joined display fields so the UI doesn't have to re-fetch.

    For each referral row we surface:
      - referred_full_name + referred_phone: from Applicant + its User
        (the one who clicked the share link / was registered with a code)
      - referrer_full_name + referrer_phone: from User (the inviter).
        Referrers are usually existing applicants, but they can also
        be staff who entered the referral manually, so we join on User
        rather than Applicant.

    All four are optional on the schema, so consumers that don't care
    (e.g. the existing referrals dashboard) keep ignoring them.
    """
    if not rows:
        return []

    applicant_ids = {r.referred_applicant_id for r in rows}
    referrer_user_ids = {r.referrer_user_id for r in rows}

    referred_name_by_id: dict[UUID, str] = {}
    referred_user_id_by_applicant: dict[UUID, UUID] = {}
    stmt = select(
        Applicant.id, Applicant.user_id, Applicant.last_name, Applicant.first_name, Applicant.other_name,
    ).where(Applicant.id.in_(applicant_ids))
    for aid, uid, last, first, other in (await session.execute(stmt)).all():
        referred_name_by_id[aid] = " ".join(filter(None, [last, first, other])).strip()
        referred_user_id_by_applicant[aid] = uid

    # Phone lookup for both referrer + referee in one User query.
    user_ids = referrer_user_ids | set(referred_user_id_by_applicant.values())
    user_info_by_id: dict[UUID, tuple[str | None, str]] = {}
    if user_ids:
        ustmt = select(User.id, User.full_name, User.phone).where(User.id.in_(user_ids))
        for uid, full_name, phone in (await session.execute(ustmt)).all():
            user_info_by_id[uid] = (full_name, phone)

    out: list[ReferralRead] = []
    for r in rows:
        rec = ReferralRead.model_validate(r)
        rec.referred_full_name = referred_name_by_id.get(r.referred_applicant_id)
        referee_uid = referred_user_id_by_applicant.get(r.referred_applicant_id)
        if referee_uid and referee_uid in user_info_by_id:
            rec.referred_phone = user_info_by_id[referee_uid][1]
        if r.referrer_user_id in user_info_by_id:
            referrer_name, referrer_phone = user_info_by_id[r.referrer_user_id]
            rec.referrer_full_name = referrer_name
            rec.referrer_phone = referrer_phone
        out.append(rec)
    return out


# ============================================================================
# Admin: stats + CSV export (Phase 5)
# ============================================================================
@router.get(
    "/stats",
    response_model=ReferralStats,
    dependencies=[Depends(require_permission(Permission.REPORTS_VIEW))],
)
async def referral_stats(
    svc: ReferralService = Depends(_service),
) -> ReferralStats:
    """Top-level numbers for the admin dashboard."""
    from sqlalchemy import Integer as _Int, case as _case
    session = svc.session

    by_status_rows = (await session.execute(
        select(Referral.status, func.count(Referral.id)).group_by(Referral.status)
    )).all()
    by_status: dict[str, int] = {s: int(c or 0) for s, c in by_status_rows}
    total = sum(by_status.values())

    discount_total = await session.scalar(
        select(func.coalesce(func.sum(Referral.reward_amount), 0))
        .where(Referral.status == "spent_on_contract")
    ) or Decimal(0)

    cash_paid = await session.scalar(
        select(func.coalesce(func.sum(ReferralPayout.amount), 0))
        .where(ReferralPayout.status == "paid")
    ) or Decimal(0)

    cash_pending_row = (await session.execute(
        select(func.count(ReferralPayout.id), func.coalesce(func.sum(ReferralPayout.amount), 0))
        .where(ReferralPayout.status.in_(("requested", "approved")))
    )).one()

    # Top 10 referrers (count of invitees, plus splits by status)
    top_stmt = (
        select(
            Referral.referrer_user_id,
            func.count(Referral.id).label("total_invited"),
            func.sum(_case((Referral.status == "active", 1), else_=0)).label("active_count"),
            func.sum(_case((Referral.status == "spent_on_contract", 1), else_=0)).label("spent_count"),
            func.sum(_case((Referral.status == "paid_cash", 1), else_=0)).label("paid_count"),
        )
        .group_by(Referral.referrer_user_id)
        .order_by(func.count(Referral.id).desc())
        .limit(10)
    )
    top_rows = (await session.execute(top_stmt)).all()
    top_user_ids = [r[0] for r in top_rows]
    user_info: dict = {}
    if top_user_ids:
        u_rows = (await session.execute(
            select(User.id, User.full_name, User.phone, User.referral_code)
            .where(User.id.in_(top_user_ids))
        )).all()
        user_info = {uid: (n, ph, code) for uid, n, ph, code in u_rows}

    referral_settings = await svc.get_settings()
    reward = Decimal(referral_settings.reward_amount)

    top_referrers: list[TopReferrer] = []
    for uid, total_inv, active_c, spent_c, paid_c in top_rows:
        full, ph, code = user_info.get(uid, (None, None, None))
        earned = reward * Decimal(int((spent_c or 0)) + int((paid_c or 0)))
        top_referrers.append(TopReferrer(
            user_id=uid,
            full_name=full,
            phone=ph,
            referral_code=code,
            total_invited=int(total_inv or 0),
            active_count=int(active_c or 0),
            spent_count=int(spent_c or 0),
            paid_count=int(paid_c or 0),
            earned_amount=earned,
        ))

    # Monthly trend — last 6 calendar months
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    trend: list[dict] = []
    for i in range(5, -1, -1):
        y, m = month_start.year, month_start.month - i
        while m <= 0:
            m += 12; y -= 1
        bucket_start = month_start.replace(year=y, month=m)
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        bucket_end = month_start.replace(year=ny, month=nm)
        cnt = await session.scalar(
            select(func.count(Referral.id))
            .where(Referral.created_at >= bucket_start, Referral.created_at < bucket_end)
        ) or 0
        trend.append({"month": bucket_start.strftime("%Y-%m"), "count": int(cnt)})

    return ReferralStats(
        total_referrals=total,
        by_status=by_status,
        total_discount_amount=discount_total,
        total_cash_paid=cash_paid,
        cash_pending_count=int(cash_pending_row[0] or 0),
        cash_pending_amount=Decimal(cash_pending_row[1] or 0),
        top_referrers=top_referrers,
        monthly_trend=trend,
    )


@router.get(
    "/export.csv",
    dependencies=[Depends(require_permission(Permission.REPORTS_VIEW))],
)
async def export_referrals_csv(
    status_filter: str | None = Query(default=None),
    svc: ReferralService = Depends(_service),
) -> Response:
    """Full referrals export (joined with applicant + referrer)."""
    session = svc.session
    stmt = (
        select(
            Referral.id,
            Referral.status,
            Referral.reward_amount,
            Referral.source,
            Referral.created_at,
            Referral.activated_at,
            Referral.cancelled_at,
            Referral.payout_at,
            User.full_name.label("referrer_name"),
            User.phone.label("referrer_phone"),
            User.referral_code.label("referrer_code"),
            Applicant.last_name,
            Applicant.first_name,
            Applicant.other_name,
        )
        .join(User, User.id == Referral.referrer_user_id)
        .join(Applicant, Applicant.id == Referral.referred_applicant_id)
    )
    if status_filter:
        stmt = stmt.where(Referral.status == status_filter)
    stmt = stmt.order_by(Referral.created_at.desc())
    rows = (await session.execute(stmt)).all()

    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM for Excel
    w = csv.writer(buf)
    w.writerow([
        "ID", "Holat", "Summa", "Manba", "Yaratilgan", "Faollashgan",
        "Bekor qilingan", "To'lov vaqti", "Tavsiya qiluvchi", "Telefon",
        "Kod", "Taklif qilingan F.I.Sh.",
    ])
    for r in rows:
        full_name = " ".join(filter(None, [r.last_name, r.first_name, r.other_name])).strip()
        w.writerow([
            str(r.id),
            r.status or "",
            str(r.reward_amount or 0),
            r.source or "",
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            r.activated_at.strftime("%Y-%m-%d %H:%M") if r.activated_at else "",
            r.cancelled_at.strftime("%Y-%m-%d %H:%M") if r.cancelled_at else "",
            r.payout_at.strftime("%Y-%m-%d %H:%M") if r.payout_at else "",
            r.referrer_name or "",
            r.referrer_phone or "",
            r.referrer_code or "",
            full_name,
        ])
    fn = f"referrals-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )
