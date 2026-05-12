"""Response shapes for operator-analytics endpoints.

Phase 1 keeps everything in a single flat schema per operator: leaderboard
callers care about totals + rates, drill-down callers add a daily series.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.core.schemas import AppSchema


class OperatorStats(AppSchema):
    """Aggregate counts for one operator over [from_date, to_date]."""

    operator_id: UUID
    full_name: str | None = None
    phone: str | None = None
    role: str

    # Leads (created_by_id OR assigned_to_id — see service for which path
    # each metric uses; "owned" semantics match what operators see in their
    # own boards).
    leads_created: int = 0
    leads_won: int = 0
    leads_lost: int = 0
    leads_open: int = 0  # snapshot: rows with status=open assigned right now

    # Applicants registered by this operator (registered_by_id).
    applicants_registered: int = 0

    # Applications: created via this operator's applicants + reviewed by them.
    applications_created: int = 0
    applications_reviewed: int = 0
    applications_accepted: int = 0
    applications_rejected: int = 0

    # Contracts.
    contracts_created: int = 0
    contracts_signed: int = 0
    contracts_cancelled: int = 0

    # Payments (operator who registered a payment row).
    payments_registered: int = 0
    payments_confirmed: int = 0
    payments_confirmed_amount: Decimal = Decimal("0")


class OperatorLeaderboard(AppSchema):
    """Top-level response for GET /analytics/operators."""

    from_date: date
    to_date: date
    items: list[OperatorStats]


class TimeseriesPoint(AppSchema):
    date: date
    value: int


class OperatorTimeseries(AppSchema):
    """Per-day counts of the key metrics for one operator.

    Each list contains one entry per day in [from_date, to_date] inclusive;
    days with no activity still show up with value=0 so charts don't have
    holes.
    """

    operator_id: UUID
    from_date: date
    to_date: date

    leads_created: list[TimeseriesPoint]
    leads_won: list[TimeseriesPoint]
    applicants_registered: list[TimeseriesPoint]
    applications_reviewed: list[TimeseriesPoint]
    contracts_created: list[TimeseriesPoint]
    contracts_signed: list[TimeseriesPoint]
    payments_confirmed: list[TimeseriesPoint]


class ActivityRow(AppSchema):
    """One bucket of audit_log activity for an operator: `action` is the
    raw audit action string (e.g. 'leads.move.post'); the frontend maps it
    to a human-friendly label via the shared `tr()` dictionary.
    """

    action: str
    count: int


class OperatorActivity(AppSchema):
    """Activity summary derived from audit_logs.

    Picks up softer engagement that the FK columns don't capture: lead
    comments, calls, stage moves, contract sign clicks, etc. This is the
    "where did the operator actually spend their day" view.
    """

    operator_id: UUID
    from_date: date
    to_date: date
    total: int
    rows: list[ActivityRow]
