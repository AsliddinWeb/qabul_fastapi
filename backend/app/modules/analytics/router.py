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

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.permissions import Permission, has_permission
from app.db.enums import UserRole
from app.modules.analytics.schemas import (
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
