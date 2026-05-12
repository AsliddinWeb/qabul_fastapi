"""Operator analytics — read-only, served at /api/v1/analytics.

  GET /operators                              leaderboard (per-operator aggregates)
  GET /operators/{operator_id}/timeseries     daily counts for one operator

Permission model:
  • admin / director / superadmin (REPORTS_VIEW) — see every operator
  • operator — sees ONLY their own row (forced operator_id = self)

Date range is required; the frontend's presets ("Bugun" / "7 kun" / "30
kun") all translate to from_date+to_date so we don't carry a separate
"preset" enum in the API.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.permissions import Permission, has_permission
from app.db.enums import UserRole
from app.modules.analytics.schemas import (
    OperatorActivity,
    OperatorLeaderboard,
    OperatorStats,
    OperatorTimeseries,
)
from app.modules.analytics.service import AnalyticsService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(session)


def _validate_range(from_date: date, to_date: date) -> None:
    if to_date < from_date:
        raise ValidationError("to_date must be >= from_date")
    # Bound the window to keep the queries cheap. 366 days covers a full
    # academic year; longer reports should be paginated by year.
    if (to_date - from_date).days > 366:
        raise ValidationError("Date range cannot exceed 366 days")


def _can_see_others(user: CurrentUser) -> bool:
    return has_permission(user.role, Permission.REPORTS_VIEW)


@router.get("/operators", response_model=OperatorLeaderboard)
async def operators_leaderboard(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    role: UserRole | None = Query(default=None, description="Filter operator pool by role"),
    operator_id: UUID | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    svc: AnalyticsService = Depends(_service),
) -> OperatorLeaderboard:
    _validate_range(from_date, to_date)

    # Operators can only inspect themselves. Anyone else is locked out so
    # one operator can't see colleagues' funnels.
    if not _can_see_others(current):
        if current.role != UserRole.OPERATOR:
            raise ForbiddenError("Analytics is restricted to staff with reports.view")
        operator_id = UUID(current.user_id)

    roles = [role] if role is not None else None
    items = await svc.leaderboard(
        from_date=from_date,
        to_date=to_date,
        roles=roles,
        operator_id=operator_id,
    )
    return OperatorLeaderboard(
        from_date=from_date,
        to_date=to_date,
        items=items,
    )


@router.get(
    "/operators/{operator_id}/timeseries",
    response_model=OperatorTimeseries,
)
async def operator_timeseries(
    operator_id: UUID,
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    current: CurrentUser = Depends(get_current_user),
    svc: AnalyticsService = Depends(_service),
) -> OperatorTimeseries:
    _validate_range(from_date, to_date)
    if not _can_see_others(current) and str(operator_id) != current.user_id:
        raise ForbiddenError("Cannot view another operator's timeseries")
    return await svc.timeseries(
        operator_id=operator_id,
        from_date=from_date,
        to_date=to_date,
    )


# Convenience: an operator hitting /operators/me/* shouldn't have to know
# its own UUID. Mirrors the existing /referrals/me/code pattern.
@router.get("/operators/me/summary", response_model=OperatorStats | None)
async def my_summary(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    current: CurrentUser = Depends(get_current_user),
    svc: AnalyticsService = Depends(_service),
) -> OperatorStats | None:
    _validate_range(from_date, to_date)
    items = await svc.leaderboard(
        from_date=from_date,
        to_date=to_date,
        roles=None,
        operator_id=UUID(current.user_id),
    )
    return items[0] if items else None


@router.get(
    "/operators/{operator_id}/activity",
    response_model=OperatorActivity,
)
async def operator_activity(
    operator_id: UUID,
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    limit: int = Query(default=30, ge=1, le=100),
    current: CurrentUser = Depends(get_current_user),
    svc: AnalyticsService = Depends(_service),
) -> OperatorActivity:
    _validate_range(from_date, to_date)
    if not _can_see_others(current) and str(operator_id) != current.user_id:
        raise ForbiddenError("Cannot view another operator's activity")
    return await svc.activity(
        operator_id=operator_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )


# ----------------------------------------------------------------------
# CSV export of the leaderboard. Returns text/csv with a UTF-8 BOM so
# Excel opens it cleanly with Uzbek characters intact. Only callers with
# reports.view may export — operators see their own data inline already.
# ----------------------------------------------------------------------
@router.get("/operators.csv")
async def operators_csv(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    role: UserRole | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    svc: AnalyticsService = Depends(_service),
) -> Response:
    _validate_range(from_date, to_date)
    if not _can_see_others(current):
        raise ForbiddenError("CSV export requires reports.view permission")

    roles = [role] if role is not None else None
    items = await svc.leaderboard(
        from_date=from_date, to_date=to_date, roles=roles,
    )

    buf = io.StringIO()
    buf.write("﻿")  # BOM for Excel
    w = csv.writer(buf)
    w.writerow([
        "F.I.Sh.", "Telefon", "Rol",
        "Lead — faollik (uniq)", "Lead — jami harakat",
        "Lead — yaratdi", "Lead — qo'ng'iroq", "Lead — izoh",
        "Lead — bosqich", "Lead — biriktirdi",
        "Lead — konversiya", "Lead — yo'qotdi", "Lead — qayta ochdi",
        "Lead — ochiq (hozir)",
        "Abituriyent", "Ariza — yaratildi", "Ariza — ko'rib chiqildi",
        "Ariza — qabul", "Ariza — rad",
        "Shartnoma — yaratildi", "Shartnoma — imzo.", "Shartnoma — bekor",
        "To'lov — yaratildi", "To'lov — tasdiqlandi", "To'lov — summa (so'm)",
    ])
    for r in items:
        w.writerow([
            r.full_name or "",
            r.phone or "",
            r.role,
            r.leads_actioned, r.lead_activities_total,
            r.lead_creates, r.lead_calls, r.lead_comments,
            r.lead_stage_moves, r.lead_assigns,
            r.lead_converts, r.lead_loses, r.lead_reopens,
            r.leads_open_assigned,
            r.applicants_registered,
            r.applications_created, r.applications_reviewed,
            r.applications_accepted, r.applications_rejected,
            r.contracts_created, r.contracts_signed, r.contracts_cancelled,
            r.payments_registered, r.payments_confirmed,
            str(r.payments_confirmed_amount),
        ])
    fn = f"operator-analytics-{from_date}_to_{to_date}-{datetime.now().strftime('%H%M')}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )
