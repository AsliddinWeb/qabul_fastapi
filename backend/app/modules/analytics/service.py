"""Operator analytics queries.

Phase 1 — pure aggregate counts grouped by user_id across the operational
tables. Everything in this file is read-only.

Date filtering is inclusive on both ends in calendar-day units; the service
turns (from_date, to_date) into a half-open UTC datetime range
[from_dt, to_dt+1day) before hitting the DB so a same-day range still
captures rows at 23:59.

We deliberately rely on real columns (created_by_id, reviewed_by_id,
registered_by_id, assigned_to_id, etc.) rather than parsing audit_logs.
The trade-off: we lose "leads.comment" / "calls" granularity here, but
the totals are accurate and the queries are O(1) GROUP BY scans against
indexed FKs. Phase 3 can layer audit_logs on top for activity drill-down.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    ApplicationStatus,
    LeadStatus,
    PaymentStatus,
    UserRole,
)
from app.modules.analytics.schemas import (
    ActivityRow,
    OperatorActivity,
    OperatorStats,
    OperatorTimeseries,
    TimeseriesPoint,
)
from app.modules.applicants.models import Applicant
from app.modules.applications.models import Application
from app.modules.audit.models import AuditLog
from app.modules.contracts.models import Contract
from app.modules.leads.models import Lead
from app.modules.payments.models import Payment
from app.modules.users.models import User


# ---------- helpers ----------
def _day_range_utc(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    """Turn (from, to) into half-open [start, end) UTC datetimes.

    The caller passes calendar dates; we want to include all of `to_date`,
    so end = to_date + 1 day at 00:00 UTC.
    """
    start = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return start, end


def _zero_fill(
    rows: list[tuple[date, int]], from_date: date, to_date: date
) -> list[TimeseriesPoint]:
    """Return one TimeseriesPoint per day in [from_date, to_date]; days that
    didn't appear in `rows` get value=0. Chart libraries hate sparse data.
    """
    by_day: dict[date, int] = {d: int(v) for d, v in rows}
    out: list[TimeseriesPoint] = []
    cur = from_date
    while cur <= to_date:
        out.append(TimeseriesPoint(date=cur, value=by_day.get(cur, 0)))
        cur = cur + timedelta(days=1)
    return out


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Leaderboard — one row per operator, all metrics over the range
    # ------------------------------------------------------------------
    async def leaderboard(
        self,
        *,
        from_date: date,
        to_date: date,
        roles: list[UserRole] | None = None,
        operator_id: UUID | None = None,
    ) -> list[OperatorStats]:
        start, end = _day_range_utc(from_date, to_date)

        # Build the operator pool. By default, "operators" = role=operator,
        # but admins also handle leads/applications and want to be visible.
        target_roles = roles or [UserRole.OPERATOR, UserRole.ADMIN]
        user_filter = [User.role.in_(target_roles), User.deleted_at.is_(None)]
        if operator_id is not None:
            user_filter.append(User.id == operator_id)

        users_rows = (await self.session.execute(
            select(User.id, User.full_name, User.phone, User.role)
            .where(and_(*user_filter))
            .order_by(User.full_name.asc().nulls_last())
        )).all()
        if not users_rows:
            return []

        stats: dict[UUID, OperatorStats] = {
            row.id: OperatorStats(
                operator_id=row.id,
                full_name=row.full_name,
                phone=row.phone,
                role=row.role.value,
            )
            for row in users_rows
        }
        user_ids = list(stats.keys())

        # Each helper returns a dict keyed by user_id. We can't asyncio.gather
        # these because AsyncSession isn't safe for concurrent execution over
        # a single connection — but with FK indexes on every group column the
        # ~15 GROUP BYs come back in tens of milliseconds even on production
        # data, so sequential is fine for a dashboard.
        leads_created = await self._count_group(
            Lead.created_by_id, Lead.created_at, start, end, user_ids,
        )
        leads_won = await self._count_group(
            Lead.assigned_to_id, Lead.converted_at, start, end, user_ids,
            extra=[Lead.status == LeadStatus.WON, Lead.converted_at.isnot(None)],
        )
        leads_lost = await self._count_group(
            Lead.assigned_to_id, Lead.lost_at, start, end, user_ids,
            extra=[Lead.status == LeadStatus.LOST, Lead.lost_at.isnot(None)],
        )
        leads_open = await self._count_snapshot(
            Lead.assigned_to_id, user_ids,
            extra=[Lead.status == LeadStatus.OPEN],
        )
        applicants_registered = await self._count_group(
            Applicant.registered_by_id, Applicant.created_at, start, end, user_ids,
        )
        applications_created = await self._count_via_applicant_join(
            Application.created_at, start, end, user_ids,
        )
        applications_reviewed = await self._count_group(
            Application.reviewed_by_id, Application.reviewed_at, start, end, user_ids,
            extra=[Application.reviewed_at.isnot(None)],
        )
        applications_accepted = await self._count_group(
            Application.reviewed_by_id, Application.reviewed_at, start, end, user_ids,
            extra=[Application.status == ApplicationStatus.ACCEPTED, Application.reviewed_at.isnot(None)],
        )
        applications_rejected = await self._count_group(
            Application.reviewed_by_id, Application.reviewed_at, start, end, user_ids,
            extra=[Application.status == ApplicationStatus.REJECTED, Application.reviewed_at.isnot(None)],
        )
        contracts_created = await self._count_group(
            Contract.created_by_id, Contract.created_at, start, end, user_ids,
        )
        contracts_signed = await self._count_group(
            Contract.signed_by_id, Contract.signed_at, start, end, user_ids,
            extra=[Contract.signed_at.isnot(None)],
        )
        contracts_cancelled = await self._count_group(
            Contract.cancelled_by_id, Contract.cancelled_at, start, end, user_ids,
            extra=[Contract.cancelled_at.isnot(None)],
        )
        payments_registered = await self._count_group(
            Payment.registered_by_id, Payment.created_at, start, end, user_ids,
        )
        payments_confirmed_counts = await self._count_group(
            Payment.registered_by_id, Payment.paid_at, start, end, user_ids,
            extra=[Payment.status == PaymentStatus.CONFIRMED, Payment.paid_at.isnot(None)],
        )
        payments_confirmed_amounts = await self._sum_group(
            Payment.registered_by_id, Payment.amount, Payment.paid_at, start, end, user_ids,
            extra=[Payment.status == PaymentStatus.CONFIRMED, Payment.paid_at.isnot(None)],
        )

        for uid, row in stats.items():
            row.leads_created = leads_created.get(uid, 0)
            row.leads_won = leads_won.get(uid, 0)
            row.leads_lost = leads_lost.get(uid, 0)
            row.leads_open = leads_open.get(uid, 0)
            row.applicants_registered = applicants_registered.get(uid, 0)
            row.applications_created = applications_created.get(uid, 0)
            row.applications_reviewed = applications_reviewed.get(uid, 0)
            row.applications_accepted = applications_accepted.get(uid, 0)
            row.applications_rejected = applications_rejected.get(uid, 0)
            row.contracts_created = contracts_created.get(uid, 0)
            row.contracts_signed = contracts_signed.get(uid, 0)
            row.contracts_cancelled = contracts_cancelled.get(uid, 0)
            row.payments_registered = payments_registered.get(uid, 0)
            row.payments_confirmed = payments_confirmed_counts.get(uid, 0)
            row.payments_confirmed_amount = payments_confirmed_amounts.get(uid, Decimal("0"))

        return list(stats.values())

    # ------------------------------------------------------------------
    # Timeseries — per-day counts for one operator
    # ------------------------------------------------------------------
    async def timeseries(
        self,
        *,
        operator_id: UUID,
        from_date: date,
        to_date: date,
    ) -> OperatorTimeseries:
        start, end = _day_range_utc(from_date, to_date)

        # Sequential for the same single-connection reason as `leaderboard`.
        leads_created = await self._daily_count(
            Lead.created_by_id, Lead.created_at, operator_id, start, end,
        )
        leads_won = await self._daily_count(
            Lead.assigned_to_id, Lead.converted_at, operator_id, start, end,
            extra=[Lead.status == LeadStatus.WON, Lead.converted_at.isnot(None)],
        )
        applicants_registered = await self._daily_count(
            Applicant.registered_by_id, Applicant.created_at, operator_id, start, end,
        )
        applications_reviewed = await self._daily_count(
            Application.reviewed_by_id, Application.reviewed_at, operator_id, start, end,
            extra=[Application.reviewed_at.isnot(None)],
        )
        contracts_created = await self._daily_count(
            Contract.created_by_id, Contract.created_at, operator_id, start, end,
        )
        contracts_signed = await self._daily_count(
            Contract.signed_by_id, Contract.signed_at, operator_id, start, end,
            extra=[Contract.signed_at.isnot(None)],
        )
        payments_confirmed = await self._daily_count(
            Payment.registered_by_id, Payment.paid_at, operator_id, start, end,
            extra=[Payment.status == PaymentStatus.CONFIRMED, Payment.paid_at.isnot(None)],
        )

        return OperatorTimeseries(
            operator_id=operator_id,
            from_date=from_date,
            to_date=to_date,
            leads_created=_zero_fill(leads_created, from_date, to_date),
            leads_won=_zero_fill(leads_won, from_date, to_date),
            applicants_registered=_zero_fill(applicants_registered, from_date, to_date),
            applications_reviewed=_zero_fill(applications_reviewed, from_date, to_date),
            contracts_created=_zero_fill(contracts_created, from_date, to_date),
            contracts_signed=_zero_fill(contracts_signed, from_date, to_date),
            payments_confirmed=_zero_fill(payments_confirmed, from_date, to_date),
        )

    # ------------------------------------------------------------------
    # Activity — what the operator actually did, from audit_logs
    # ------------------------------------------------------------------
    async def activity(
        self,
        *,
        operator_id: UUID,
        from_date: date,
        to_date: date,
        limit: int = 30,
    ) -> OperatorActivity:
        """Group audit_log rows by action for one user, ordered by frequency.

        The frontend prints these with `tr()` so raw strings like
        "leads.move.post" become "Lead bosqichi o'zgartirildi". We cap the
        result set at `limit` actions so a noisy day doesn't blow up the
        response — anything past the cap is bundled into a single "..."
        row by the caller if needed.
        """
        start, end = _day_range_utc(from_date, to_date)
        stmt = (
            select(AuditLog.action, func.count())
            .where(and_(
                AuditLog.user_id == operator_id,
                AuditLog.created_at >= start,
                AuditLog.created_at < end,
            ))
            .group_by(AuditLog.action)
            .order_by(func.count().desc(), AuditLog.action.asc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        total_stmt = (
            select(func.count())
            .where(and_(
                AuditLog.user_id == operator_id,
                AuditLog.created_at >= start,
                AuditLog.created_at < end,
            ))
        )
        total = int((await self.session.execute(total_stmt)).scalar() or 0)
        return OperatorActivity(
            operator_id=operator_id,
            from_date=from_date,
            to_date=to_date,
            total=total,
            rows=[ActivityRow(action=a, count=int(c)) for a, c in rows],
        )

    # ------------------------------------------------------------------
    # Internal query helpers
    # ------------------------------------------------------------------
    async def _count_group(
        self,
        group_col,
        date_col,
        start: datetime,
        end: datetime,
        user_ids: list[UUID],
        *,
        extra: list | None = None,
    ) -> dict[UUID, int]:
        """SELECT group_col, COUNT(*) … WHERE date_col ∈ [start,end) GROUP BY."""
        where = [
            group_col.in_(user_ids),
            date_col >= start,
            date_col < end,
        ]
        if extra:
            where.extend(extra)
        stmt = (
            select(group_col, func.count())
            .where(and_(*where))
            .group_by(group_col)
        )
        rows = (await self.session.execute(stmt)).all()
        return {uid: int(cnt) for uid, cnt in rows if uid is not None}

    async def _sum_group(
        self,
        group_col,
        sum_col,
        date_col,
        start: datetime,
        end: datetime,
        user_ids: list[UUID],
        *,
        extra: list | None = None,
    ) -> dict[UUID, Decimal]:
        where = [
            group_col.in_(user_ids),
            date_col >= start,
            date_col < end,
        ]
        if extra:
            where.extend(extra)
        stmt = (
            select(group_col, func.coalesce(func.sum(sum_col), 0))
            .where(and_(*where))
            .group_by(group_col)
        )
        rows = (await self.session.execute(stmt)).all()
        return {uid: Decimal(str(total)) for uid, total in rows if uid is not None}

    async def _count_snapshot(
        self,
        group_col,
        user_ids: list[UUID],
        *,
        extra: list | None = None,
    ) -> dict[UUID, int]:
        """Snapshot count — no date filter (e.g. currently-open leads)."""
        where = [group_col.in_(user_ids)]
        if extra:
            where.extend(extra)
        stmt = (
            select(group_col, func.count())
            .where(and_(*where))
            .group_by(group_col)
        )
        rows = (await self.session.execute(stmt)).all()
        return {uid: int(cnt) for uid, cnt in rows if uid is not None}

    async def _count_via_applicant_join(
        self,
        date_col,
        start: datetime,
        end: datetime,
        user_ids: list[UUID],
    ) -> dict[UUID, int]:
        """Applications don't carry created_by_id directly — attribute them
        to the operator who registered the underlying applicant. Same column
        also powers the "applicants_registered" metric, so totals stay
        consistent when you read both."""
        stmt = (
            select(Applicant.registered_by_id, func.count(Application.id))
            .select_from(Application)
            .join(Applicant, Applicant.id == Application.applicant_id)
            .where(and_(
                Applicant.registered_by_id.in_(user_ids),
                date_col >= start,
                date_col < end,
            ))
            .group_by(Applicant.registered_by_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {uid: int(cnt) for uid, cnt in rows if uid is not None}

    async def _daily_count(
        self,
        group_col,
        date_col,
        user_id: UUID,
        start: datetime,
        end: datetime,
        *,
        extra: list | None = None,
    ) -> list[tuple[date, int]]:
        """SELECT DATE(date_col), COUNT(*) for one operator over the range.

        Postgres `date_trunc('day', ...)` produces a timestamp; we cast to
        date so Python gets clean keys for zero-filling.
        """
        where = [
            group_col == user_id,
            date_col >= start,
            date_col < end,
        ]
        if extra:
            where.extend(extra)
        day_col = func.date(func.timezone("UTC", date_col)).label("day")
        stmt = (
            select(day_col, func.count())
            .where(and_(*where))
            .group_by(day_col)
            .order_by(day_col)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(d, int(c)) for d, c in rows]
