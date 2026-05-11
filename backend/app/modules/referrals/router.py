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
from app.modules.referrals.schemas import (
    AttachReferrerPayload,
    ReferralCodeRead,
    ReferralRead,
    ReferralSettingsRead,
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
