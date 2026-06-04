"""Lead service — funnel orchestration.

Public operations:
  • create_lead          (with phone-based merge + optional auto-assign)
  • update_lead
  • move_to_stage        (records activity)
  • assign               (manual user_id or round-robin)
  • add_comment
  • lose                 (with reason)
  • convert              (delegates Applicant + Application creation back to caller)
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.enums import LeadStatus, UserRole
from app.modules.leads.models import (
    Lead, LeadActivity, LeadLostReason, LeadPipeline, LeadSource, LeadStage,
)
from app.modules.leads.repository import (
    LeadActivityRepository,
    LeadLostReasonRepository,
    LeadPipelineRepository,
    LeadRepository,
    LeadSourceRepository,
    LeadStageRepository,
)
from app.modules.leads.schemas import (
    LeadAssign,
    LeadCommentCreate,
    LeadCreate,
    LeadLose,
    LeadMove,
    LeadScheduleContact,
    LeadUpdate,
)
from app.modules.users.models import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LeadService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.leads = LeadRepository(session)
        self.pipelines = LeadPipelineRepository(session)
        self.stages = LeadStageRepository(session)
        self.sources = LeadSourceRepository(session)
        self.lost_reasons = LeadLostReasonRepository(session)
        self.activities = LeadActivityRepository(session)

    # ------------------------------------------------------------------ #
    #  Catalog (light wrappers used by routers)
    # ------------------------------------------------------------------ #
    async def list_pipelines(self) -> list[LeadPipeline]:
        return await self.pipelines.list_active()

    async def list_stages(self, pipeline_id: UUID) -> list[LeadStage]:
        return await self.stages.list_for_pipeline(pipeline_id)

    async def list_sources(self) -> list[LeadSource]:
        return await self.sources.list_all()

    async def list_lost_reasons(self) -> list[LeadLostReason]:
        return await self.lost_reasons.list_all()

    # ------------------------------------------------------------------ #
    #  Create (with de-duplication merge)
    # ------------------------------------------------------------------ #
    async def create_lead(
        self, payload: LeadCreate, *, actor_id: UUID | None,
    ) -> tuple[Lead, bool]:
        """Returns (lead, merged_flag). When merged_flag is True the lead is
        an existing OPEN one we deduped into — caller should surface that to
        the operator so they don't think they created a new record.
        """
        phone = payload.phone.strip()
        if not phone:
            raise ValidationError("phone is required")

        # 1) Resolve pipeline + first stage
        pipeline = (
            await self.pipelines.get(payload.pipeline_id) if payload.pipeline_id else None
        )
        if pipeline is None:
            pipeline = await self.pipelines.get_default()
        if pipeline is None:
            raise ValidationError("No active pipeline configured")

        stage = (
            await self.stages.get(payload.stage_id) if payload.stage_id else None
        )
        if stage is None or stage.pipeline_id != pipeline.id:
            stage = await self.stages.get_first(pipeline.id)
        if stage is None:
            raise ValidationError("Pipeline has no stages")

        # 2) De-dup: existing OPEN lead with same phone → merge
        existing = await self.leads.find_by_phone_open(phone)
        if existing:
            merged = await self._merge_into_existing(
                existing, payload=payload, actor_id=actor_id,
            )
            return merged, True

        # 3) Auto-assign (round-robin) if requested and no explicit user
        assigned_to_id = payload.assigned_to_id
        if assigned_to_id is None and payload.auto_assign:
            assigned_to_id = await self._round_robin_operator()

        # 4) Create
        lead = await self.leads.create(
            full_name=payload.full_name.strip(),
            phone=phone,
            email=(payload.email or None),
            telegram_username=(payload.telegram_username.strip().lstrip("@") or None) if payload.telegram_username else None,
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            source_id=payload.source_id,
            source_meta=payload.source_meta,
            branch_id=payload.branch_id,
            program_id=payload.program_id,
            assigned_to_id=assigned_to_id,
            created_by_id=actor_id,
            notes=payload.notes,
            status=LeadStatus.OPEN,
            stage_entered_at=_utcnow(),
        )
        await self._activity(
            lead_id=lead.id, user_id=actor_id, action="create",
            to_stage_id=stage.id,
            comment=payload.notes,
        )
        if assigned_to_id is not None:
            await self._activity(
                lead_id=lead.id, user_id=actor_id, action="assign",
                extra={"to_user_id": str(assigned_to_id)},
            )
        return lead, False

    async def _merge_into_existing(
        self, existing: Lead, *, payload: LeadCreate, actor_id: UUID | None,
    ) -> Lead:
        """De-dup: append non-empty fields and a merge note onto an existing OPEN lead."""
        changes: list[str] = []

        # Soft updates: only fill fields that are missing on the existing record.
        if payload.email and not existing.email:
            existing.email = payload.email; changes.append("email")
        if payload.branch_id and not existing.branch_id:
            existing.branch_id = payload.branch_id; changes.append("branch_id")
        if payload.program_id and not existing.program_id:
            existing.program_id = payload.program_id; changes.append("program_id")
        if payload.source_id and not existing.source_id:
            existing.source_id = payload.source_id; changes.append("source_id")
        if payload.full_name and len(payload.full_name) > len(existing.full_name or ""):
            existing.full_name = payload.full_name; changes.append("full_name")

        # Append notes (don't overwrite)
        merged_notes = []
        if existing.notes:
            merged_notes.append(existing.notes)
        if payload.notes:
            merged_notes.append(f"[Merged {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')}]\n{payload.notes}")
        if merged_notes:
            existing.notes = "\n\n".join(merged_notes)

        await self.session.flush()
        await self._activity(
            lead_id=existing.id, user_id=actor_id, action="merge",
            comment=payload.notes or None,
            extra={"changed_fields": changes, "phone": payload.phone},
        )
        return existing

    async def _round_robin_operator(self) -> UUID | None:
        """Pick an operator uniformly at random from the active pool.

        Originally this preferred the least-loaded operator (with a UUID
        tie-break) which concentrated public-form leads on whoever's
        UUID sorted lowest and worked fastest. We tried "least-loaded +
        random tie-break" next, but the team preferred pure random:
        every active operator has an equal chance regardless of current
        load. That sometimes piles a few extra leads on a busy operator
        for a day, but eliminates the worst-case clustering and is the
        simplest behaviour to reason about.

        Falls back to admins/superadmins if no operator exists.
        """
        import random

        ops_stmt = select(User).where(
            User.role == UserRole.OPERATOR,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        ops = list((await self.session.scalars(ops_stmt)).all())
        if not ops:
            ops_stmt = select(User).where(
                User.role.in_([UserRole.ADMIN, UserRole.SUPERADMIN]),
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
            ops = list((await self.session.scalars(ops_stmt)).all())
        if not ops:
            return None
        return random.choice(ops).id

    # ------------------------------------------------------------------ #
    #  Update simple fields
    # ------------------------------------------------------------------ #
    async def update_lead(self, lead_id: UUID, payload: LeadUpdate, *, actor_id: UUID | None) -> Lead:
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        data = payload.model_dump(exclude_unset=True)
        if not data:
            return lead
        for k, v in data.items():
            setattr(lead, k, v)
        await self.session.flush()
        await self._activity(
            lead_id=lead.id, user_id=actor_id, action="update",
            extra={"fields": list(data.keys())},
        )
        return lead

    # ------------------------------------------------------------------ #
    #  Stage move
    # ------------------------------------------------------------------ #
    async def move_to_stage(self, lead_id: UUID, payload: LeadMove, *, actor_id: UUID | None) -> Lead:
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        if lead.status != LeadStatus.OPEN:
            raise ValidationError("Closed leads cannot be moved")
        stage = await self.stages.get(payload.stage_id)
        if not stage or stage.pipeline_id != lead.pipeline_id:
            raise ValidationError("Stage does not belong to this lead's pipeline")
        if stage.id == lead.stage_id:
            return lead
        from_stage_id = lead.stage_id
        lead.stage_id = stage.id
        lead.stage_entered_at = _utcnow()
        lead.last_contact_at = _utcnow()
        await self.session.flush()
        await self._activity(
            lead_id=lead.id, user_id=actor_id, action="stage_move",
            from_stage_id=from_stage_id, to_stage_id=stage.id,
            comment=payload.comment,
        )
        return lead

    # ------------------------------------------------------------------ #
    #  Assignment
    # ------------------------------------------------------------------ #
    async def assign(self, lead_id: UUID, payload: LeadAssign, *, actor_id: UUID | None) -> Lead:
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        if lead.status != LeadStatus.OPEN:
            raise ValidationError("Closed leads cannot be reassigned")

        new_user_id = payload.user_id
        if new_user_id is None and payload.auto_assign:
            new_user_id = await self._round_robin_operator()
        prev = lead.assigned_to_id
        lead.assigned_to_id = new_user_id
        await self.session.flush()
        await self._activity(
            lead_id=lead.id, user_id=actor_id, action="assign",
            extra={"from_user_id": str(prev) if prev else None,
                   "to_user_id": str(new_user_id) if new_user_id else None},
        )
        return lead

    # ------------------------------------------------------------------ #
    #  Comment (free-text timeline event)
    # ------------------------------------------------------------------ #
    async def add_comment(self, lead_id: UUID, payload: LeadCommentCreate, *, actor_id: UUID | None) -> LeadActivity:
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        lead.last_contact_at = _utcnow()
        await self.session.flush()
        return await self._activity(
            lead_id=lead.id, user_id=actor_id, action="comment",
            comment=payload.comment.strip(),
        )

    async def log_call(
        self, lead_id: UUID, payload: LeadCommentCreate, *, actor_id: UUID | None,
    ) -> LeadActivity:
        """Record a phone-call activity. Same shape as add_comment but with
        action='call' so the timeline can render it with a phone icon and
        operators can filter their call history.
        """
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        lead.last_contact_at = _utcnow()
        await self.session.flush()
        return await self._activity(
            lead_id=lead.id, user_id=actor_id, action="call",
            comment=(payload.comment or "").strip() or None,
        )

    # ------------------------------------------------------------------ #
    #  Schedule next contact (operator-side reminder / task)
    # ------------------------------------------------------------------ #
    async def schedule_contact(
        self, lead_id: UUID, payload: LeadScheduleContact, *, actor_id: UUID | None,
    ) -> Lead:
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        if lead.status != LeadStatus.OPEN:
            raise ValidationError(f"Lead is already {lead.status.value}")
        lead.next_contact_at = payload.next_contact_at
        lead.next_contact_note = (payload.note or "").strip() or None
        await self.session.flush()
        if payload.next_contact_at is None:
            await self._activity(
                lead_id=lead.id, user_id=actor_id, action="schedule_clear",
                comment="Reminder o'chirildi",
            )
        else:
            await self._activity(
                lead_id=lead.id, user_id=actor_id, action="schedule",
                comment=payload.note or None,
                extra={"next_contact_at": payload.next_contact_at.isoformat()},
            )
        return lead

    # ------------------------------------------------------------------ #
    #  Lose
    # ------------------------------------------------------------------ #
    async def lose(self, lead_id: UUID, payload: LeadLose, *, actor_id: UUID | None) -> Lead:
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        if lead.status != LeadStatus.OPEN:
            raise ValidationError(f"Lead is already {lead.status.value}")
        if payload.reason_id:
            r = await self.lost_reasons.get(payload.reason_id)
            if not r:
                raise ValidationError("Unknown lost reason")
        lead.status = LeadStatus.LOST
        lead.lost_reason_id = payload.reason_id
        lead.lost_comment = payload.comment
        lead.lost_at = _utcnow()
        await self.session.flush()
        await self._activity(
            lead_id=lead.id, user_id=actor_id, action="lose",
            comment=payload.comment, extra={"reason_id": str(payload.reason_id) if payload.reason_id else None},
        )
        return lead

    # ------------------------------------------------------------------ #
    #  Reopen (lost or won → open)
    # ------------------------------------------------------------------ #
    async def reopen(self, lead_id: UUID, *, actor_id: UUID | None) -> Lead:
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        if lead.status == LeadStatus.OPEN:
            return lead
        if lead.applicant_id is not None:
            raise ConflictError("Lead is converted to an Application; cannot reopen")
        lead.status = LeadStatus.OPEN
        lead.lost_reason_id = None
        lead.lost_comment = None
        lead.lost_at = None
        lead.stage_entered_at = _utcnow()
        await self.session.flush()
        await self._activity(lead_id=lead.id, user_id=actor_id, action="reopen")
        return lead

    # ------------------------------------------------------------------ #
    #  Convert hook (called by router after Application is created elsewhere)
    # ------------------------------------------------------------------ #
    async def mark_converted(
        self, lead_id: UUID, *, applicant_id: UUID, application_id: UUID, actor_id: UUID | None,
    ) -> Lead:
        lead = await self.leads.get(lead_id)
        if not lead:
            raise NotFoundError("Lead not found")
        if lead.status == LeadStatus.WON:
            return lead  # idempotent
        lead.status = LeadStatus.WON
        lead.applicant_id = applicant_id
        lead.application_id = application_id
        lead.converted_at = _utcnow()
        await self.session.flush()
        await self._activity(
            lead_id=lead.id, user_id=actor_id, action="convert",
            extra={"applicant_id": str(applicant_id), "application_id": str(application_id)},
        )
        return lead

    # ------------------------------------------------------------------ #
    #  Activity helper
    # ------------------------------------------------------------------ #
    async def _activity(
        self,
        *,
        lead_id: UUID,
        user_id: UUID | None,
        action: str,
        from_stage_id: UUID | None = None,
        to_stage_id: UUID | None = None,
        comment: str | None = None,
        extra: dict | None = None,
    ) -> LeadActivity:
        return await self.activities.create(
            lead_id=lead_id,
            user_id=user_id,
            action=action,
            from_stage_id=from_stage_id,
            to_stage_id=to_stage_id,
            comment=comment,
            extra=extra,
        )
