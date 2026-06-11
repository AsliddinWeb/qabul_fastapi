from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, asc, desc, func, or_, select

from app.core.repository import BaseRepository
from app.db.enums import LeadStatus
from app.modules.leads.models import (
    Lead, LeadActivity, LeadLostReason, LeadPipeline, LeadSource, LeadStage,
)
from app.modules.programs.models import Branch, Program
from app.modules.users.models import User


# --------------------------------------------------------------------------- #
#  Catalog repos
# --------------------------------------------------------------------------- #

class LeadPipelineRepository(BaseRepository[LeadPipeline]):
    model = LeadPipeline

    async def list_active(self) -> list[LeadPipeline]:
        stmt = select(LeadPipeline).where(LeadPipeline.is_active.is_(True)).order_by(LeadPipeline.order_index, LeadPipeline.name)
        return list((await self.session.scalars(stmt)).all())

    async def get_default(self) -> LeadPipeline | None:
        stmt = select(LeadPipeline).where(LeadPipeline.is_default.is_(True), LeadPipeline.is_active.is_(True)).limit(1)
        obj = (await self.session.scalars(stmt)).first()
        if obj:
            return obj
        # fallback: any active pipeline
        return (await self.session.scalars(select(LeadPipeline).where(LeadPipeline.is_active.is_(True)).limit(1))).first()


class LeadStageRepository(BaseRepository[LeadStage]):
    model = LeadStage

    async def list_for_pipeline(self, pipeline_id: UUID, *, only_active: bool = True) -> list[LeadStage]:
        stmt = select(LeadStage).where(LeadStage.pipeline_id == pipeline_id)
        if only_active:
            stmt = stmt.where(LeadStage.is_active.is_(True))
        stmt = stmt.order_by(LeadStage.order_index, LeadStage.name)
        return list((await self.session.scalars(stmt)).all())

    async def get_first(self, pipeline_id: UUID) -> LeadStage | None:
        stmt = (
            select(LeadStage)
            .where(LeadStage.pipeline_id == pipeline_id, LeadStage.is_active.is_(True))
            .order_by(LeadStage.order_index, LeadStage.name)
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()


class LeadSourceRepository(BaseRepository[LeadSource]):
    model = LeadSource

    async def list_all(self, *, only_active: bool = True) -> list[LeadSource]:
        stmt = select(LeadSource)
        if only_active:
            stmt = stmt.where(LeadSource.is_active.is_(True))
        stmt = stmt.order_by(LeadSource.order_index, LeadSource.name)
        return list((await self.session.scalars(stmt)).all())

    async def get_by_code(self, code: str) -> LeadSource | None:
        return await self.get_by(code=code)


class LeadLostReasonRepository(BaseRepository[LeadLostReason]):
    model = LeadLostReason

    async def list_all(self, *, only_active: bool = True) -> list[LeadLostReason]:
        stmt = select(LeadLostReason)
        if only_active:
            stmt = stmt.where(LeadLostReason.is_active.is_(True))
        stmt = stmt.order_by(LeadLostReason.order_index, LeadLostReason.name)
        return list((await self.session.scalars(stmt)).all())


# --------------------------------------------------------------------------- #
#  Lead repository
# --------------------------------------------------------------------------- #

class LeadRepository(BaseRepository[Lead]):
    model = Lead

    async def find_by_phone_open(self, phone: str) -> Lead | None:
        """Find an OPEN lead with the given phone (de-dup target)."""
        stmt = (
            select(Lead)
            .where(Lead.phone == phone, Lead.status == LeadStatus.OPEN)
            .order_by(Lead.created_at.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def find_latest_by_phone(self, phone: str) -> Lead | None:
        """Find the most recent lead with the given phone, regardless of status.

        Used by the public capture endpoint to detect repeat submissions from
        already-converted (WON) or lost (LOST) leads, so we don't restart them
        at the top of the funnel.
        """
        stmt = (
            select(Lead)
            .where(Lead.phone == phone)
            .order_by(Lead.created_at.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def list_filtered(
        self,
        *,
        pipeline_id: UUID | None = None,
        stage_id: UUID | None = None,
        status: LeadStatus | None = None,
        source_id: UUID | None = None,
        assigned_to_id: UUID | None = None,
        branch_id: UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        clauses = []
        if pipeline_id is not None:        clauses.append(Lead.pipeline_id == pipeline_id)
        if stage_id is not None:           clauses.append(Lead.stage_id == stage_id)
        if status is not None:             clauses.append(Lead.status == status)
        if source_id is not None:          clauses.append(Lead.source_id == source_id)
        if assigned_to_id is not None:     clauses.append(Lead.assigned_to_id == assigned_to_id)
        if branch_id is not None:          clauses.append(Lead.branch_id == branch_id)
        if search:
            q = f"%{search.strip()}%"
            clauses.append(or_(Lead.full_name.ilike(q), Lead.phone.ilike(q), Lead.email.ilike(q)))

        rows = await self._select_with_labels(clauses, limit=limit, offset=offset)

        count_stmt = select(func.count(Lead.id))
        if clauses:
            count_stmt = count_stmt.where(and_(*clauses))
        total = await self.session.scalar(count_stmt) or 0
        return rows, total

    async def board_for_pipeline(self, pipeline_id: UUID) -> list[dict]:
        """All non-lost leads of a pipeline, with embedded labels.

        We include OPEN + WON so converted leads stay visible on the board
        at the stage they reached before conversion — the user wanted to
        be able to find and edit them after the fact. LOST is still hidden
        because it would clutter the board with failures and the stage_id
        on a lost lead is often noise (the user didn't progress it before
        losing).
        """
        clauses = [
            Lead.pipeline_id == pipeline_id,
            Lead.status.in_([LeadStatus.OPEN, LeadStatus.WON]),
        ]
        return await self._select_with_labels(clauses, limit=None, offset=0)

    async def _select_with_labels(self, clauses: list, *, limit: int | None, offset: int) -> list[dict]:
        stmt = (
            select(
                Lead,
                LeadStage.name.label("stage_name"),
                LeadStage.color.label("stage_color"),
                LeadPipeline.name.label("pipeline_name"),
                LeadSource.name.label("source_name"),
                LeadSource.code.label("source_code"),
                Branch.name.label("branch_name"),
                Program.name.label("program_name"),
                User.full_name.label("assigned_to_name"),
            )
            .join(LeadStage, Lead.stage_id == LeadStage.id)
            .join(LeadPipeline, Lead.pipeline_id == LeadPipeline.id)
            .outerjoin(LeadSource, Lead.source_id == LeadSource.id)
            .outerjoin(Branch, Lead.branch_id == Branch.id)
            .outerjoin(Program, Lead.program_id == Program.id)
            .outerjoin(User, Lead.assigned_to_id == User.id)
        )
        if clauses:
            stmt = stmt.where(and_(*clauses))
        stmt = stmt.order_by(desc(Lead.created_at))
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)

        out: list[dict] = []
        rows = (await self.session.execute(stmt)).all()
        for (
            lead, stage_name, stage_color, pipeline_name, source_name, source_code,
            branch_name, program_name, assigned_to_name,
        ) in rows:
            d = self._lead_to_dict(lead)
            d["stage_name"] = stage_name
            d["stage_color"] = stage_color
            d["pipeline_name"] = pipeline_name
            d["source_name"] = source_name
            d["source_code"] = source_code
            d["branch_name"] = branch_name
            d["program_name"] = program_name
            d["assigned_to_name"] = assigned_to_name
            out.append(d)
        return out

    @staticmethod
    def _lead_to_dict(lead: Lead) -> dict:
        return {
            "id": lead.id,
            "full_name": lead.full_name,
            "phone": lead.phone,
            "email": lead.email,
            "telegram_username": lead.telegram_username,
            "pipeline_id": lead.pipeline_id,
            "stage_id": lead.stage_id,
            "source_id": lead.source_id,
            "source_meta": lead.source_meta,
            "branch_id": lead.branch_id,
            "program_id": lead.program_id,
            "assigned_to_id": lead.assigned_to_id,
            "created_by_id": lead.created_by_id,
            "notes": lead.notes,
            "status": lead.status,
            "applicant_id": lead.applicant_id,
            "application_id": lead.application_id,
            "converted_at": lead.converted_at,
            "lost_reason_id": lead.lost_reason_id,
            "lost_comment": lead.lost_comment,
            "lost_at": lead.lost_at,
            "last_contact_at": lead.last_contact_at,
            "next_contact_at": lead.next_contact_at,
            "next_contact_note": lead.next_contact_note,
            "stage_entered_at": lead.stage_entered_at,
            "created_at": lead.created_at,
            "updated_at": lead.updated_at,
        }

    async def get_with_labels(self, lead_id: UUID) -> dict | None:
        rows = await self._select_with_labels([Lead.id == lead_id], limit=1, offset=0)
        return rows[0] if rows else None

    async def stale_open_leads(self, *, hours: int = 72) -> list[Lead]:
        """Open leads stuck in current stage for more than `hours` (default 72 = 3 days).

        Used by the SLA worker. Filters out:
          • unassigned leads (no operator → no one to alert)
          • leads on terminal stages (final/won stages don't need a poke)
          • leads with a future next_contact_at within 7 days (operator
            already has an explicit plan to follow up)
        Without these the worker fired hundreds of false-positive alerts
        per hour — orphan leads, won leads sitting in done stages, and
        leads operators had already scheduled follow-ups for all got
        flagged as "stuck".
        """
        from datetime import datetime as dt
        cutoff = dt.fromtimestamp(
            datetime.now(timezone.utc).timestamp() - hours * 3600,
            tz=timezone.utc,
        )
        next_contact_horizon = dt.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + 7 * 86400,
            tz=timezone.utc,
        )

        stmt = (
            select(Lead)
            .join(LeadStage, Lead.stage_id == LeadStage.id)
            .where(
                Lead.status == LeadStatus.OPEN,
                Lead.stage_entered_at < cutoff,
                Lead.assigned_to_id.isnot(None),
                LeadStage.is_terminal.is_(False),
                or_(
                    Lead.next_contact_at.is_(None),
                    Lead.next_contact_at > next_contact_horizon,
                ),
            )
            .order_by(Lead.stage_entered_at)
        )
        return list((await self.session.scalars(stmt)).all())

    async def with_recent_sla_alert(self, *, within_hours: int = 24) -> list[dict]:
        """Open leads that received an `sla_alert` activity in the last N hours.

        Returns lead-with-labels dicts (same shape as list_filtered) plus an embedded
        `last_alert_at` timestamp. Used by the notification bell.
        """
        from datetime import datetime as dt
        cutoff = dt.now(timezone.utc).timestamp() - within_hours * 3600
        cutoff_dt = dt.fromtimestamp(cutoff, tz=timezone.utc)

        from sqlalchemy import distinct, func as F  # noqa: N812
        # Subquery: leads with at least one sla_alert in window, with the latest alert ts.
        sub = (
            select(
                LeadActivity.lead_id.label("lid"),
                F.max(LeadActivity.created_at).label("last_alert_at"),
            )
            .where(LeadActivity.action == "sla_alert", LeadActivity.created_at >= cutoff_dt)
            .group_by(LeadActivity.lead_id)
            .subquery()
        )

        stmt = (
            select(
                Lead,
                LeadStage.name.label("stage_name"),
                LeadStage.color.label("stage_color"),
                LeadPipeline.name.label("pipeline_name"),
                LeadSource.name.label("source_name"),
                LeadSource.code.label("source_code"),
                Branch.name.label("branch_name"),
                Program.name.label("program_name"),
                User.full_name.label("assigned_to_name"),
                sub.c.last_alert_at,
            )
            .join(sub, sub.c.lid == Lead.id)
            .join(LeadStage, Lead.stage_id == LeadStage.id)
            .join(LeadPipeline, Lead.pipeline_id == LeadPipeline.id)
            .outerjoin(LeadSource, Lead.source_id == LeadSource.id)
            .outerjoin(Branch, Lead.branch_id == Branch.id)
            .outerjoin(Program, Lead.program_id == Program.id)
            .outerjoin(User, Lead.assigned_to_id == User.id)
            .where(Lead.status == LeadStatus.OPEN)
            .order_by(sub.c.last_alert_at.desc())
        )
        out: list[dict] = []
        for row in (await self.session.execute(stmt)).all():
            (lead, stage_name, stage_color, pipeline_name, source_name, source_code,
             branch_name, program_name, assigned_to_name, last_alert_at) = row
            d = self._lead_to_dict(lead)
            d["stage_name"] = stage_name
            d["stage_color"] = stage_color
            d["pipeline_name"] = pipeline_name
            d["source_name"] = source_name
            d["source_code"] = source_code
            d["branch_name"] = branch_name
            d["program_name"] = program_name
            d["assigned_to_name"] = assigned_to_name
            d["last_alert_at"] = last_alert_at
            out.append(d)
        return out

    async def breakdown_stats(self) -> dict:
        """Per-source and per-operator conversion stats."""
        from sqlalchemy import case, func as F  # noqa: N812

        # Per source
        src_stmt = (
            select(
                LeadSource.id, LeadSource.name,
                F.count(Lead.id).label("total"),
                F.sum(case((Lead.status == LeadStatus.WON, 1), else_=0)).label("won"),
                F.sum(case((Lead.status == LeadStatus.LOST, 1), else_=0)).label("lost"),
                F.sum(case((Lead.status == LeadStatus.OPEN, 1), else_=0)).label("open_"),
            )
            .select_from(LeadSource)
            .outerjoin(Lead, Lead.source_id == LeadSource.id)
            .group_by(LeadSource.id, LeadSource.name)
            .order_by(F.count(Lead.id).desc())
        )
        by_source = []
        for sid, name, total, won, lost, open_ in (await self.session.execute(src_stmt)).all():
            t = int(total or 0); w = int(won or 0)
            by_source.append({
                "source_id": str(sid), "name": name,
                "total": t, "won": w, "lost": int(lost or 0), "open": int(open_ or 0),
                "conversion_rate": round((w / t) * 100) if t else 0,
            })

        # Per operator (assigned_to)
        op_stmt = (
            select(
                User.id, User.full_name, User.phone,
                F.count(Lead.id).label("total"),
                F.sum(case((Lead.status == LeadStatus.WON, 1), else_=0)).label("won"),
                F.sum(case((Lead.status == LeadStatus.LOST, 1), else_=0)).label("lost"),
                F.sum(case((Lead.status == LeadStatus.OPEN, 1), else_=0)).label("open_"),
            )
            .select_from(User)
            .join(Lead, Lead.assigned_to_id == User.id)
            .group_by(User.id, User.full_name, User.phone)
            .order_by(F.count(Lead.id).desc())
        )
        by_operator = []
        for uid, full_name, phone, total, won, lost, open_ in (await self.session.execute(op_stmt)).all():
            t = int(total or 0); w = int(won or 0)
            by_operator.append({
                "user_id": str(uid),
                "name": full_name or phone,
                "phone": phone,
                "total": t, "won": w, "lost": int(lost or 0), "open": int(open_ or 0),
                "conversion_rate": round((w / t) * 100) if t else 0,
            })

        return {"by_source": by_source, "by_operator": by_operator}

    async def export_filtered(
        self,
        *,
        pipeline_id=None, stage_id=None, status=None, source_id=None,
        assigned_to_id=None, branch_id=None, search=None,
    ) -> list[dict]:
        """Same filters as list_filtered but unbounded (used for CSV export)."""
        clauses = []
        if pipeline_id is not None:    clauses.append(Lead.pipeline_id == pipeline_id)
        if stage_id is not None:       clauses.append(Lead.stage_id == stage_id)
        if status is not None:         clauses.append(Lead.status == status)
        if source_id is not None:      clauses.append(Lead.source_id == source_id)
        if assigned_to_id is not None: clauses.append(Lead.assigned_to_id == assigned_to_id)
        if branch_id is not None:      clauses.append(Lead.branch_id == branch_id)
        if search:
            q = f"%{search.strip()}%"
            clauses.append(or_(Lead.full_name.ilike(q), Lead.phone.ilike(q), Lead.email.ilike(q)))
        return await self._select_with_labels(clauses, limit=None, offset=0)


# --------------------------------------------------------------------------- #
#  Activities repo
# --------------------------------------------------------------------------- #

class LeadActivityRepository(BaseRepository[LeadActivity]):
    model = LeadActivity

    async def list_for_lead(self, lead_id: UUID) -> list[dict]:
        """Activities + actor + stage labels, oldest first → newest at end (timeline)."""
        FromStage = LeadStage.__table__.alias("from_stage")
        ToStage = LeadStage.__table__.alias("to_stage")

        stmt = (
            select(
                LeadActivity,
                User.full_name.label("user_full_name"),
                User.phone.label("user_phone"),
                FromStage.c.name.label("from_stage_name"),
                ToStage.c.name.label("to_stage_name"),
            )
            .outerjoin(User, LeadActivity.user_id == User.id)
            .outerjoin(FromStage, LeadActivity.from_stage_id == FromStage.c.id)
            .outerjoin(ToStage, LeadActivity.to_stage_id == ToStage.c.id)
            .where(LeadActivity.lead_id == lead_id)
            .order_by(asc(LeadActivity.created_at))
        )
        rows = (await self.session.execute(stmt)).all()
        out: list[dict] = []
        for act, user_full_name, user_phone, from_stage_name, to_stage_name in rows:
            out.append({
                "id": act.id,
                "lead_id": act.lead_id,
                "user_id": act.user_id,
                "user_full_name": user_full_name,
                "user_phone": user_phone,
                "action": act.action,
                "from_stage_id": act.from_stage_id,
                "from_stage_name": from_stage_name,
                "to_stage_id": act.to_stage_id,
                "to_stage_name": to_stage_name,
                "comment": act.comment,
                "extra": act.extra,
                "created_at": act.created_at,
            })
        return out
