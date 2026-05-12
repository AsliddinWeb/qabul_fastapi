"""Response shapes for operator-analytics endpoints.

Lead metrics are *action-based*: every row in `lead_activities` is
attributed to the operator who actually performed the action, not the
person who originally created the lead or who happens to be assigned
right now. That makes the leaderboard reflect actual sales work rather
than data-entry credit.

Applicants / applications / contracts / payments stay FK-based — those
domains have a single clear actor per event (registered_by_id /
reviewed_by_id / signed_by_id / cancelled_by_id / registered_by_id) and
don't need an activity log to attribute work.
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

    # ----- Leads (action-based, from lead_activities) -----
    # Distinct leads this operator touched in the range. The truest single
    # "did they work this period?" signal.
    leads_actioned: int = 0
    # Total LeadActivity rows authored by this operator — raw volume.
    lead_activities_total: int = 0
    # Per-action breakdown so the UI can show what KIND of work was done.
    lead_creates: int = 0      # action='create' (lead intake)
    lead_calls: int = 0        # action='call'
    lead_comments: int = 0     # action='comment'
    lead_stage_moves: int = 0  # action='stage_move'
    lead_assigns: int = 0      # action='assign' (re-assignment events)
    lead_converts: int = 0     # action='convert' (lead → application)
    lead_loses: int = 0        # action='lose'
    lead_reopens: int = 0      # action='reopen'
    # Workload snapshot — leads currently assigned to this operator with
    # status=open. Not affected by the date range.
    leads_open_assigned: int = 0

    # ----- Applicants & applications (FK-based) -----
    applicants_registered: int = 0
    applications_created: int = 0
    applications_reviewed: int = 0
    applications_accepted: int = 0
    applications_rejected: int = 0

    # ----- Contracts (FK-based) -----
    contracts_created: int = 0
    contracts_signed: int = 0
    contracts_cancelled: int = 0

    # ----- Payments (FK-based) -----
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

    # Lead work — action-based
    lead_activities_total: list[TimeseriesPoint]
    lead_converts: list[TimeseriesPoint]
    # Downstream funnel
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
