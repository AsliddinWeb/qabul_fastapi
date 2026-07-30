"""Lead funnel HTTP routes.

Endpoints (all under /api/v1/leads when mounted with prefix='/leads'):

  GET    /                      list with filters
  POST   /                      create (with phone-dedup + optional auto-assign)
  POST   /public                public capture (no auth)
  GET    /board                 kanban grouping for a pipeline
  GET    /stats                 aggregated funnel stats
  GET    /{id}                  detail
  GET    /{id}/activities       timeline
  PATCH  /{id}                  update simple fields
  POST   /{id}/move             change stage
  POST   /{id}/assign           change assignee (or auto)
  POST   /{id}/comment          add comment to timeline
  POST   /{id}/lose             mark as lost
  POST   /{id}/reopen           reopen a lost lead
  POST   /{id}/convert          finalize — creates Applicant+Application from lead

Settings (catalogs):
  GET/POST/PATCH/DELETE /pipelines
  GET/POST/PATCH/DELETE /stages
  GET/POST/PATCH/DELETE /sources
  GET/POST/PATCH/DELETE /lost-reasons
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.core.schemas import PageResponse
from app.db.enums import LeadStatus
from app.modules.audit.service import AuditService
from app.modules.leads.models import Lead, LeadActivity, LeadLostReason, LeadPipeline, LeadSource, LeadStage
from app.modules.leads.repository import (
    LeadActivityRepository,
    LeadLostReasonRepository,
    LeadPipelineRepository,
    LeadRepository,
    LeadSourceRepository,
    LeadStageRepository,
)
from app.modules.leads.schemas import (
    LeadActivityRead,
    LeadAssign,
    LeadBoardResponse,
    LeadBoardStage,
    LeadBoardStagePage,
    LeadCommentCreate,
    LeadConvert,
    LeadCreate,
    LeadCreateResponse,
    LeadLose,
    LeadLostReasonCreate,
    LeadLostReasonRead,
    LeadLostReasonUpdate,
    LeadMove,
    LeadPipelineCreate,
    LeadPipelineRead,
    LeadPipelineUpdate,
    LeadPublicCreate,
    LeadPublicResponse,
    LeadRead,
    LeadScheduleContact,
    LeadSourceCreate,
    LeadSourceRead,
    LeadSourceUpdate,
    LeadStageCreate,
    LeadStageRead,
    LeadStageUpdate,
    LeadUpdate,
)
from app.modules.leads.service import LeadService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> LeadService:
    return LeadService(session)


# --------------------------------------------------------------------------- #
#  PUBLIC capture (no auth) — placed before /{id} dynamic routes.
# --------------------------------------------------------------------------- #

@router.post("/public", response_model=LeadPublicResponse, status_code=status.HTTP_200_OK)
async def public_capture(
    payload: LeadPublicCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> LeadPublicResponse:
    """Public lead capture endpoint — used by landing form.

    Anti-spam:
      • Honeypot field (`_hp`) must be empty — bots fill it.
      • Time gate: `t` (page-load timestamp ms) must be 2s..30min old.
      • IP rate limit (Redis): max 3 successful submissions per 10 min, 10 per hour.

    De-duplication strategy (a lead in the funnel never restarts):
      • If an OPEN lead exists for this phone → soft-merge new fields, keep stage.
      • If a WON or LOST lead exists for this phone (already converted/dropped)
        → DO NOT create a new lead. Append a "duplicate landing submission"
        activity onto the latest lead so the assigned operator sees it.
      • Otherwise → create a fresh lead at the first stage. This includes the
        case where a User/applicant exists for this phone but has never been
        in the lead funnel (e.g. registered directly via SMS-OTP) — a new lead
        is desired so an operator can follow up on the new interest.

    The response shape is intentionally minimal so the landing form gets a
    user-friendly status without leaking lead internals.
    """
    import time
    from app.core.redis import get_redis

    # ---- Honeypot ----
    hp = (payload.hp or "").strip()
    if hp:
        raise HTTPException(status_code=429, detail="Too many requests")

    # ---- Time gate ----
    now_ms = int(time.time() * 1000)
    if payload.t is not None:
        elapsed = now_ms - int(payload.t)
        if elapsed < 2_000:
            raise HTTPException(status_code=429, detail="Too fast")
        if elapsed > 30 * 60_000:
            raise HTTPException(status_code=410, detail="Form expired, please reload")
    else:
        # No timestamp at all → strongly suspect non-form submission.
        # Real visitors always carry `t` because it's injected at page-load.
        raise HTTPException(status_code=400, detail="Invalid submission")

    # ---- Phone format ----
    # Strict UZ mobile format: +998 + 9 digits, mobile prefixes only. Drops
    # the most common "spam by raw curl with garbage phone" pattern that's
    # been hitting the form.
    import re as _re
    raw_phone = payload.phone.strip()
    phone_digits = "".join(c for c in raw_phone if c.isdigit())
    if not _re.match(r"^998(33|55|61|66|71|77|78|88|90|91|93|94|95|97|98|99)\d{7}$", phone_digits):
        raise HTTPException(status_code=400, detail="Telefon raqami noto'g'ri")
    # Re-normalise so downstream sees the canonical "+998..." form.
    payload.phone = "+" + phone_digits

    # ---- Name sanity ----
    # Bots like to flood with single-word/glued names. Real applicants give
    # at least F + I (two words). Also reject digits or URLs in the name.
    fn = payload.full_name.strip()
    if len(fn.split()) < 2:
        raise HTTPException(status_code=400, detail="To'liq ism va familiyani kiriting")
    if _re.search(r"\d|https?://|<|>", fn):
        raise HTTPException(status_code=400, detail="Ismda raqam yoki havola bo'lmasin")

    # ---- IP rate limit + per-phone limit ----
    ip = (request.headers.get("x-forwarded-for") or request.client.host if request.client else "unknown").split(",")[0].strip()
    redis = get_redis()
    k_min   = f"lead_pub:ip:{ip}:10m"
    k_hr    = f"lead_pub:ip:{ip}:1h"
    k_phone = f"lead_pub:phone:{phone_digits}:1h"
    try:
        n_min = await redis.incr(k_min)
        if n_min == 1: await redis.expire(k_min, 600)
        n_hr  = await redis.incr(k_hr)
        if n_hr == 1: await redis.expire(k_hr, 3600)
        # Per-phone cap: anything more than 2 submissions/hour on the same
        # number is overwhelmingly bot retry / form-spam. Real users don't
        # resubmit that often.
        n_phone = await redis.incr(k_phone)
        if n_phone == 1: await redis.expire(k_phone, 3600)
        if n_min > 3 or n_hr > 10 or n_phone > 2:
            raise HTTPException(status_code=429, detail="Too many requests, try later")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis down — degrade gracefully

    # ---- Resolve source by code (default 'web_form' matches the dictionary seed) ----
    source_id = None
    source_code = (payload.source_code or "web_form").strip().lower()
    if source_code:
        row = (await session.execute(select(LeadSource).where(LeadSource.code == source_code))).scalar_one_or_none()
        if row:
            source_id = row.id

    svc = LeadService(session)
    phone = payload.phone.strip()

    # ---- De-dup: WON or LOST lead → activity-only, don't restart funnel ----
    latest = await svc.leads.find_latest_by_phone(phone)
    if latest is not None and latest.status != LeadStatus.OPEN:
        await svc.activities.create(
            lead_id=latest.id,
            user_id=None,
            action="duplicate_submission",
            comment=(
                f"Saytdan qayta murojaat (status: {latest.status.value}). "
                f"Yangi lead yaratilmadi."
            ),
            extra={
                "ip": ip,
                "ua": request.headers.get("user-agent", "")[:200],
                "source_code": source_code,
                "submitted_full_name": payload.full_name.strip(),
                "submitted_program_id": str(payload.program_id) if payload.program_id else None,
            },
        )
        await session.commit()
        return LeadPublicResponse(
            status="duplicate",
            message=(
                "Sizning arizangiz allaqachon ro'yxatda. "
                "Operator siz bilan tez orada bog'lanadi."
            ),
        )

    # ---- Create or merge into OPEN ----
    internal = LeadCreate(
        full_name=payload.full_name.strip(),
        phone=phone,
        program_id=payload.program_id,
        source_id=source_id,
        source_meta={"ip": ip, "ua": request.headers.get("user-agent", "")[:200]},
        auto_assign=True,
    )

    was_merge = latest is not None and latest.status == LeadStatus.OPEN
    await svc.create_lead(internal, actor_id=None)  # public flow ignores the (lead, merged) flag
    await session.commit()

    if was_merge:
        return LeadPublicResponse(
            status="merged",
            message="Arizangiz qabul qilindi, ma'lumotlar yangilandi.",
        )
    return LeadPublicResponse(
        status="created",
        message="Arizangiz qabul qilindi. Operator yaqin orada bog'lanadi.",
    )


# --------------------------------------------------------------------------- #
#  STAFF endpoints
# --------------------------------------------------------------------------- #

@router.get(
    "/check-phone",
    dependencies=[Depends(require_permission(Permission.LEADS_CREATE))],
)
async def check_phone(
    phone: str = Query(..., min_length=4, max_length=20),
    svc: LeadService = Depends(_service),
) -> dict:
    """Pre-submit dedup probe for the LeadNewPage form.

    Returns the existing OPEN lead's identity (id + assignee name) if a
    match is found, or `{exists: false}` otherwise. Lets the UI warn the
    operator before they submit instead of after, saving an unintended
    silent merge into someone else's funnel.
    """
    cleaned = phone.strip()
    if not cleaned:
        return {"exists": False}
    existing = await svc.leads.find_by_phone_open(cleaned)
    if existing is None:
        return {"exists": False}
    # Resolve assignee name in a single hop — find_by_phone_open returns
    # the bare ORM row, so we go through get_with_labels for the joined
    # fields (assigned_to_name in particular).
    full = await svc.leads.get_with_labels(existing.id)
    return {
        "exists": True,
        "lead_id": str(existing.id),
        "full_name": existing.full_name,
        "assigned_to_id": str(existing.assigned_to_id) if existing.assigned_to_id else None,
        "assigned_to_name": (full or {}).get("assigned_to_name"),
        "stage_name": (full or {}).get("stage_name"),
    }


@router.get(
    "",
    response_model=PageResponse[LeadRead],
    dependencies=[Depends(require_permission(Permission.LEADS_LIST))],
)
async def list_leads(
    pipeline_id: UUID | None = Query(default=None),
    stage_id: UUID | None = Query(default=None),
    status_filter: LeadStatus | None = Query(default=None, alias="status"),
    source_id: UUID | None = Query(default=None),
    assigned_to_id: UUID | None = Query(default=None),
    branch_id: UUID | None = Query(default=None),
    has_next_contact: bool | None = Query(
        default=None,
        description="Filter by next_contact_at presence: true = scheduled callbacks only",
    ),
    search: str | None = Query(default=None, max_length=100),
    created_from: datetime | None = Query(default=None, description="created_at >= this UTC timestamp"),
    created_to: datetime | None = Query(default=None, description="created_at <= this UTC timestamp"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    svc: LeadService = Depends(_service),
) -> PageResponse[LeadRead]:
    items, total = await svc.leads.list_filtered(
        pipeline_id=pipeline_id, stage_id=stage_id, status=status_filter,
        source_id=source_id, assigned_to_id=assigned_to_id, branch_id=branch_id,
        has_next_contact=has_next_contact,
        search=search,
        created_from=created_from, created_to=created_to,
        limit=size, offset=(page - 1) * size,
    )
    return PageResponse[LeadRead].build(
        items=[LeadRead.model_validate(i) for i in items],
        total=total, page=page, size=size,
    )


@router.post(
    "",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.LEADS_CREATE))],
)
async def create_lead(
    payload: LeadCreate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadCreateResponse:
    lead, merged = await svc.create_lead(
        payload, actor_id=UUID(current.user_id), block_on_duplicate=True,
    )
    # Only audit fresh creates; merges already get a 'merge' lead_activity row
    # via _merge_into_existing, so duplicating into audit_logs is noise.
    if not merged:
        await AuditService(svc.session).log(
            "lead.create", user_id=UUID(current.user_id),
            entity_type="leads", entity_id=lead.id,
            changes={"phone": lead.phone, "full_name": lead.full_name},
            request=request,
        )
    await svc.session.commit()
    full = await svc.leads.get_with_labels(lead.id)
    return LeadCreateResponse(
        lead=LeadRead.model_validate(full),
        merged=merged,
    )


# Cards loaded per stage on first paint and per "load more" click. Keeping
# this small is what makes the board survive pipelines with tens of thousands
# of leads — the rest are paged in on demand.
BOARD_PAGE_SIZE = 30


@router.get(
    "/board",
    response_model=LeadBoardResponse,
    dependencies=[Depends(require_permission(Permission.LEADS_LIST))],
)
async def board(
    pipeline_id: UUID | None = Query(default=None),
    assigned_to_id: UUID | None = Query(default=None),
    svc: LeadService = Depends(_service),
) -> LeadBoardResponse:
    pipeline = (await svc.pipelines.get(pipeline_id)) if pipeline_id else await svc.pipelines.get_default()
    if not pipeline:
        raise HTTPException(status_code=404, detail="No pipeline configured")
    stages = await svc.stages.list_for_pipeline(pipeline.id)
    counts = await svc.leads.board_stage_counts(pipeline.id, assigned_to_id=assigned_to_id)

    board_stages: list[LeadBoardStage] = []
    for s in stages:
        first_page = await svc.leads.board_leads_for_stage(
            pipeline.id, s.id, limit=BOARD_PAGE_SIZE, offset=0,
            assigned_to_id=assigned_to_id,
        )
        board_stages.append(LeadBoardStage(
            id=s.id, name=s.name, color=s.color,
            is_terminal=s.is_terminal, order_index=s.order_index,
            total=counts.get(s.id, 0),
            leads=[LeadRead.model_validate(x) for x in first_page],
        ))

    return LeadBoardResponse(
        pipeline_id=pipeline.id,
        pipeline_name=pipeline.name,
        page_size=BOARD_PAGE_SIZE,
        stages=board_stages,
    )


@router.get(
    "/board/stage/{stage_id}",
    response_model=LeadBoardStagePage,
    dependencies=[Depends(require_permission(Permission.LEADS_LIST))],
)
async def board_stage_page(
    stage_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=BOARD_PAGE_SIZE, ge=1, le=100),
    assigned_to_id: UUID | None = Query(default=None),
    svc: LeadService = Depends(_service),
) -> LeadBoardStagePage:
    """'Load more' for a single board column — the next page of a stage's
    cards, newest first."""
    stage = await svc.stages.get(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    total = (await svc.leads.board_stage_counts(
        stage.pipeline_id, assigned_to_id=assigned_to_id
    )).get(stage_id, 0)
    rows = await svc.leads.board_leads_for_stage(
        stage.pipeline_id, stage_id, limit=limit, offset=offset,
        assigned_to_id=assigned_to_id,
    )
    return LeadBoardStagePage(
        stage_id=stage_id,
        total=total,
        offset=offset,
        leads=[LeadRead.model_validate(x) for x in rows],
        has_more=(offset + len(rows)) < total,
    )


@router.get(
    "/stats",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission(Permission.LEADS_LIST))],
)
async def stats(
    pipeline_id: UUID | None = Query(default=None),
    assigned_to_id: UUID | None = Query(default=None),
    svc: LeadService = Depends(_service),
) -> dict[str, Any]:
    pipeline = (await svc.pipelines.get(pipeline_id)) if pipeline_id else await svc.pipelines.get_default()
    if not pipeline:
        return {"total": 0, "open": 0, "won": 0, "lost": 0, "by_stage": []}
    base = select(func.count(Lead.id)).where(Lead.pipeline_id == pipeline.id)
    if assigned_to_id is not None:
        base = base.where(Lead.assigned_to_id == assigned_to_id)
    total = await svc.session.scalar(base) or 0
    won = await svc.session.scalar(base.where(Lead.status == LeadStatus.WON)) or 0
    lost = await svc.session.scalar(base.where(Lead.status == LeadStatus.LOST)) or 0
    open_ = total - won - lost
    open_join_clauses = [Lead.stage_id == LeadStage.id, Lead.status == LeadStatus.OPEN]
    if assigned_to_id is not None:
        open_join_clauses.append(Lead.assigned_to_id == assigned_to_id)
    by_stage_stmt = (
        select(LeadStage.id, LeadStage.name, LeadStage.order_index, func.count(Lead.id))
        .select_from(LeadStage)
        .outerjoin(Lead, and_(*open_join_clauses))
        .where(LeadStage.pipeline_id == pipeline.id)
        .group_by(LeadStage.id, LeadStage.name, LeadStage.order_index)
        .order_by(LeadStage.order_index)
    )
    by_stage = [
        {"stage_id": str(sid), "name": name, "order_index": oi, "open_leads": cnt}
        for sid, name, oi, cnt in (await svc.session.execute(by_stage_stmt)).all()
    ]
    return {
        "pipeline_id": str(pipeline.id),
        "pipeline_name": pipeline.name,
        "total": total, "open": open_, "won": won, "lost": lost,
        "conversion_rate": round((won / total) * 100) if total else 0,
        "by_stage": by_stage,
    }


@router.get(
    "/sla-alerts",
    response_model=list[dict[str, Any]],
    dependencies=[Depends(require_permission(Permission.LEADS_LIST))],
)
async def sla_alerts(
    within_hours: int = Query(default=24, ge=1, le=168),
    svc: LeadService = Depends(_service),
) -> list[dict[str, Any]]:
    """Open leads that received an `sla_alert` in the last N hours.

    Returns lead-with-labels dicts plus `last_alert_at`. Drives the bell badge.
    """
    rows = await svc.leads.with_recent_sla_alert(within_hours=within_hours)
    # Convert UUID/datetime fields for JSON; reuse LeadRead and append last_alert_at
    out = []
    for r in rows:
        item = LeadRead.model_validate(r).model_dump(mode="json")
        item["last_alert_at"] = r["last_alert_at"].isoformat() if r.get("last_alert_at") else None
        out.append(item)
    return out


@router.get(
    "/stats/breakdown",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission(Permission.LEADS_LIST))],
)
async def stats_breakdown(svc: LeadService = Depends(_service)) -> dict[str, Any]:
    """Per-source + per-operator conversion stats. Drives dashboard widget."""
    return await svc.leads.breakdown_stats()


@router.get(
    "/export.csv",
    dependencies=[Depends(require_permission(Permission.LEADS_LIST))],
)
async def export_csv(
    pipeline_id: UUID | None = Query(default=None),
    stage_id: UUID | None = Query(default=None),
    status_filter: LeadStatus | None = Query(default=None, alias="status"),
    source_id: UUID | None = Query(default=None),
    assigned_to_id: UUID | None = Query(default=None),
    branch_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    svc: LeadService = Depends(_service),
) -> Response:
    """Export filtered leads to CSV (UTF-8 BOM for Excel compatibility)."""
    rows = await svc.leads.export_filtered(
        pipeline_id=pipeline_id, stage_id=stage_id, status=status_filter,
        source_id=source_id, assigned_to_id=assigned_to_id, branch_id=branch_id,
        search=search,
    )
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM so Excel opens it correctly
    w = csv.writer(buf)
    w.writerow([
        "F.I.Sh.", "Telefon", "Email", "Manba", "Varonka", "Bosqich", "Holat",
        "Filial", "Yo'nalish", "Operator", "Yaratilgan", "Bosqichga kirgan",
        "Ariza ID", "Eslatma",
    ])
    for r in rows:
        w.writerow([
            r.get("full_name") or "",
            r.get("phone") or "",
            r.get("email") or "",
            r.get("source_name") or "",
            r.get("pipeline_name") or "",
            r.get("stage_name") or "",
            (r.get("status").value if hasattr(r.get("status"), "value") else r.get("status") or ""),
            r.get("branch_name") or "",
            r.get("program_name") or "",
            r.get("assigned_to_name") or "",
            r["created_at"].strftime("%Y-%m-%d %H:%M") if r.get("created_at") else "",
            r["stage_entered_at"].strftime("%Y-%m-%d %H:%M") if r.get("stage_entered_at") else "",
            str(r.get("application_id") or ""),
            (r.get("notes") or "").replace("\n", " ").strip(),
        ])
    fn = f"leads-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.get(
    "/{lead_id}",
    response_model=LeadRead,
    dependencies=[Depends(require_permission(Permission.LEADS_READ))],
)
async def get_lead(lead_id: UUID, svc: LeadService = Depends(_service)) -> LeadRead:
    full = await svc.leads.get_with_labels(lead_id)
    if not full:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadRead.model_validate(full)


@router.get(
    "/{lead_id}/activities",
    response_model=list[LeadActivityRead],
    dependencies=[Depends(require_permission(Permission.LEADS_READ))],
)
async def list_activities(lead_id: UUID, svc: LeadService = Depends(_service)) -> list[LeadActivityRead]:
    rows = await svc.activities.list_for_lead(lead_id)
    return [LeadActivityRead.model_validate(r) for r in rows]


@router.get(
    "/{lead_id}/related-applications",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission(Permission.LEADS_READ))],
)
async def lead_related_applications(
    lead_id: UUID, svc: LeadService = Depends(_service),
) -> dict[str, Any]:
    """Return existing applications for the user with this lead's phone.

    Used by the lead detail page to show a "this person already has applications"
    card with deep links into each application — so the operator can see the
    person's history before working the lead.
    """
    from app.modules.applications.models import Application
    from app.modules.applicants.models import Applicant
    from app.modules.programs.models import Program, Branch
    from app.modules.users.models import User as UserModel

    lead = await svc.leads.get(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    user = (await svc.session.execute(
        select(UserModel).where(
            UserModel.phone == lead.phone, UserModel.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if user is None:
        return {"user_id": None, "applicant_id": None, "applications": []}

    applicant = (await svc.session.execute(
        select(Applicant).where(Applicant.user_id == user.id)
    )).scalar_one_or_none()
    if applicant is None:
        return {"user_id": str(user.id), "applicant_id": None, "applications": []}

    rows = (await svc.session.execute(
        select(
            Application.id,
            Application.application_number,
            Application.status,
            Application.admission_type,
            Application.created_at,
            Application.submitted_at,
            Program.name.label("program_name"),
            Branch.name.label("branch_name"),
        )
        .join(Program, Program.id == Application.program_id, isouter=True)
        .join(Branch, Branch.id == Application.branch_id, isouter=True)
        .where(Application.applicant_id == applicant.id)
        .order_by(Application.created_at.desc())
    )).all()

    return {
        "user_id": str(user.id),
        "applicant_id": str(applicant.id),
        "applications": [
            {
                "id": str(r.id),
                "application_number": r.application_number,
                "status": r.status.value if r.status else None,
                "admission_type": r.admission_type.value if r.admission_type else None,
                "program_name": r.program_name,
                "branch_name": r.branch_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            }
            for r in rows
        ],
    }


@router.patch(
    "/{lead_id}",
    response_model=LeadRead,
    dependencies=[Depends(require_permission(Permission.LEADS_UPDATE))],
)
async def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadRead:
    await svc.update_lead(lead_id, payload, actor_id=UUID(current.user_id))
    await svc.session.commit()
    full = await svc.leads.get_with_labels(lead_id)
    return LeadRead.model_validate(full)


@router.post(
    "/{lead_id}/move",
    response_model=LeadRead,
    dependencies=[Depends(require_permission(Permission.LEADS_MOVE))],
)
async def move_lead(
    lead_id: UUID,
    payload: LeadMove,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadRead:
    await svc.move_to_stage(lead_id, payload, actor_id=UUID(current.user_id))
    await svc.session.commit()
    full = await svc.leads.get_with_labels(lead_id)
    return LeadRead.model_validate(full)


@router.post(
    "/{lead_id}/assign",
    response_model=LeadRead,
    dependencies=[Depends(require_permission(Permission.LEADS_ASSIGN))],
)
async def assign_lead(
    lead_id: UUID,
    payload: LeadAssign,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadRead:
    await svc.assign(lead_id, payload, actor_id=UUID(current.user_id))
    await svc.session.commit()
    full = await svc.leads.get_with_labels(lead_id)
    return LeadRead.model_validate(full)


@router.post(
    "/{lead_id}/comment",
    response_model=LeadActivityRead,
    dependencies=[Depends(require_permission(Permission.LEADS_UPDATE))],
)
async def add_comment(
    lead_id: UUID,
    payload: LeadCommentCreate,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadActivityRead:
    await svc.add_comment(lead_id, payload, actor_id=UUID(current.user_id))
    await svc.session.commit()
    rows = await svc.activities.list_for_lead(lead_id)
    return LeadActivityRead.model_validate(rows[-1])


@router.post(
    "/{lead_id}/call",
    response_model=LeadActivityRead,
    dependencies=[Depends(require_permission(Permission.LEADS_UPDATE))],
)
async def log_call(
    lead_id: UUID,
    payload: LeadCommentCreate,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadActivityRead:
    """Log a phone-call activity. Operator clicks 'Qo'ng'iroq qildim' on the
    lead card and optionally adds a note about the conversation."""
    await svc.log_call(lead_id, payload, actor_id=UUID(current.user_id))
    await svc.session.commit()
    rows = await svc.activities.list_for_lead(lead_id)
    return LeadActivityRead.model_validate(rows[-1])


@router.post(
    "/{lead_id}/schedule",
    response_model=LeadRead,
    dependencies=[Depends(require_permission(Permission.LEADS_UPDATE))],
)
async def schedule_contact(
    lead_id: UUID,
    payload: LeadScheduleContact,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadRead:
    """Schedule (or clear) the next-callback reminder for this lead."""
    await svc.schedule_contact(lead_id, payload, actor_id=UUID(current.user_id))
    await svc.session.commit()
    full = await svc.leads.get_with_labels(lead_id)
    return LeadRead.model_validate(full)


@router.post(
    "/{lead_id}/lose",
    response_model=LeadRead,
    dependencies=[Depends(require_permission(Permission.LEADS_LOSE))],
)
async def lose_lead(
    lead_id: UUID,
    payload: LeadLose,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadRead:
    await svc.lose(lead_id, payload, actor_id=UUID(current.user_id))
    await svc.session.commit()
    full = await svc.leads.get_with_labels(lead_id)
    return LeadRead.model_validate(full)


@router.post(
    "/{lead_id}/reopen",
    response_model=LeadRead,
    dependencies=[Depends(require_permission(Permission.LEADS_LOSE))],
)
async def reopen_lead(
    lead_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadRead:
    await svc.reopen(lead_id, actor_id=UUID(current.user_id))
    await svc.session.commit()
    full = await svc.leads.get_with_labels(lead_id)
    return LeadRead.model_validate(full)


# Convert is special — it returns enough info for the frontend to redirect to the
# pre-filled application form. The frontend then submits the application as usual,
# and finishes by calling /{lead_id}/finalize-conversion to attach the new application.

@router.get(
    "/{lead_id}/prefill",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission(Permission.LEADS_CONVERT))],
)
async def get_prefill(lead_id: UUID, svc: LeadService = Depends(_service)) -> dict[str, Any]:
    """Returns a payload suitable for prefilling the ApplicationFormPage."""
    full = await svc.leads.get_with_labels(lead_id)
    if not full:
        raise HTTPException(status_code=404, detail="Lead not found")
    if full["status"] != LeadStatus.OPEN:
        raise HTTPException(status_code=400, detail=f"Lead is {full['status'].value}")
    parts = (full["full_name"] or "").split()
    return {
        "lead_id": str(full["id"]),
        "phone": full["phone"],
        "telegram_username": full.get("telegram_username"),
        "last_name": parts[0] if parts else "",
        "first_name": parts[1] if len(parts) > 1 else "",
        "other_name": " ".join(parts[2:]) if len(parts) > 2 else "",
        "branch_id": str(full["branch_id"]) if full["branch_id"] else None,
        "program_id": str(full["program_id"]) if full["program_id"] else None,
        "source_code": full.get("source_name"),  # display label
        "notes": full["notes"],
    }


@router.post(
    "/{lead_id}/finalize-conversion",
    response_model=LeadRead,
    dependencies=[Depends(require_permission(Permission.LEADS_CONVERT))],
)
async def finalize_conversion(
    lead_id: UUID,
    payload: dict[str, str],  # { applicant_id, application_id }
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> LeadRead:
    if "applicant_id" not in payload or "application_id" not in payload:
        raise HTTPException(status_code=400, detail="applicant_id and application_id are required")
    await svc.mark_converted(
        lead_id,
        applicant_id=UUID(payload["applicant_id"]),
        application_id=UUID(payload["application_id"]),
        actor_id=UUID(current.user_id),
    )
    await svc.session.commit()
    full = await svc.leads.get_with_labels(lead_id)
    return LeadRead.model_validate(full)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.LEADS_DELETE))],
)
async def delete_lead(
    lead_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
):
    obj = await svc.leads.get(lead_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    if obj.application_id is not None:
        raise HTTPException(status_code=400, detail="Konversiya bo'lgan lead'ni o'chirib bo'lmaydi")
    await svc.session.delete(obj)
    await svc.session.commit()
    return None


@router.post(
    "/bulk-delete",
    dependencies=[Depends(require_permission(Permission.LEADS_DELETE))],
)
async def bulk_delete_leads(
    payload: dict,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> dict:
    """Bulk-delete leads. Skips any lead already converted to an
    application (those can't be deleted individually either). Returns
    {deleted, skipped} counts so the UI can show "5 ta o'chirildi, 2 ta
    o'tkazib yuborildi (konversiya bo'lgan)".
    """
    ids_raw = payload.get("ids") or []
    if not isinstance(ids_raw, list) or not ids_raw:
        raise HTTPException(status_code=400, detail="ids list is required")
    try:
        ids = [UUID(str(i)) for i in ids_raw]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid id in list")

    deleted = 0
    skipped = 0
    for lead_id in ids:
        obj = await svc.leads.get(lead_id)
        if not obj:
            skipped += 1
            continue
        if obj.application_id is not None:
            skipped += 1
            continue
        await svc.session.delete(obj)
        deleted += 1
    await svc.session.commit()
    return {"deleted": deleted, "skipped": skipped}


@router.post(
    "/bulk-assign",
    dependencies=[Depends(require_permission(Permission.LEADS_ASSIGN))],
)
async def bulk_assign_leads(
    payload: dict,
    current: CurrentUser = Depends(get_current_user),
    svc: LeadService = Depends(_service),
) -> dict:
    """Bulk-reassign leads to one operator (or auto-assign each
    individually if user_id is null). Skips closed leads — assign is an
    OPEN-only operation, same as the per-row endpoint.
    """
    ids_raw = payload.get("ids") or []
    user_id_raw = payload.get("user_id")
    if not isinstance(ids_raw, list) or not ids_raw:
        raise HTTPException(status_code=400, detail="ids list is required")
    try:
        ids = [UUID(str(i)) for i in ids_raw]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid id in list")
    target_user_id: UUID | None = None
    if user_id_raw:
        try:
            target_user_id = UUID(str(user_id_raw))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid user_id")

    assigned = 0
    skipped = 0
    for lead_id in ids:
        obj = await svc.leads.get(lead_id)
        if not obj or obj.status != LeadStatus.OPEN:
            skipped += 1
            continue
        # Reuse the per-row assign so the activity log gets a row each
        # time — bulk should be just as visible in the timeline as
        # individual reassignment.
        from app.modules.leads.schemas import LeadAssign
        await svc.assign(
            lead_id,
            payload=LeadAssign(user_id=target_user_id, auto_assign=target_user_id is None),
            actor_id=UUID(current.user_id),
        )
        assigned += 1
    await svc.session.commit()
    return {"assigned": assigned, "skipped": skipped}


# --------------------------------------------------------------------------- #
#  Catalog endpoints — pipelines / stages / sources / lost-reasons
# --------------------------------------------------------------------------- #

# ----- Pipelines -----

@router.get("/catalog/pipelines", response_model=list[LeadPipelineRead])
async def list_pipelines(svc: LeadService = Depends(_service)) -> list[LeadPipelineRead]:
    return [LeadPipelineRead.model_validate(p) for p in await svc.list_pipelines()]


@router.post(
    "/catalog/pipelines",
    response_model=LeadPipelineRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def create_pipeline(payload: LeadPipelineCreate, svc: LeadService = Depends(_service)) -> LeadPipelineRead:
    obj = await svc.pipelines.create(**payload.model_dump())
    if obj.is_default:
        await _enforce_single_default(svc, obj.id)
    await svc.session.commit()
    return LeadPipelineRead.model_validate(obj)


@router.patch(
    "/catalog/pipelines/{pipeline_id}",
    response_model=LeadPipelineRead,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def update_pipeline(
    pipeline_id: UUID, payload: LeadPipelineUpdate, svc: LeadService = Depends(_service),
) -> LeadPipelineRead:
    obj = await svc.pipelines.get(pipeline_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await svc.session.flush()
    if obj.is_default:
        await _enforce_single_default(svc, obj.id)
    await svc.session.commit()
    return LeadPipelineRead.model_validate(obj)


@router.delete(
    "/catalog/pipelines/{pipeline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def delete_pipeline(pipeline_id: UUID, svc: LeadService = Depends(_service)):
    obj = await svc.pipelines.get(pipeline_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    in_use = await svc.session.scalar(
        select(func.count(Lead.id)).where(Lead.pipeline_id == pipeline_id),
    )
    if in_use:
        raise HTTPException(status_code=400, detail=f"Pipeline has {in_use} lead(s); cannot delete")
    await svc.session.delete(obj)
    await svc.session.commit()
    return None


async def _enforce_single_default(svc: LeadService, current_id: UUID) -> None:
    others = (await svc.session.scalars(
        select(LeadPipeline).where(LeadPipeline.id != current_id, LeadPipeline.is_default.is_(True)),
    )).all()
    for o in others:
        o.is_default = False
    await svc.session.flush()


# ----- Stages -----

@router.get("/catalog/stages", response_model=list[LeadStageRead])
async def list_stages(
    pipeline_id: UUID = Query(...),
    svc: LeadService = Depends(_service),
) -> list[LeadStageRead]:
    return [LeadStageRead.model_validate(s) for s in await svc.list_stages(pipeline_id)]


@router.post(
    "/catalog/stages",
    response_model=LeadStageRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def create_stage(payload: LeadStageCreate, svc: LeadService = Depends(_service)) -> LeadStageRead:
    obj = await svc.stages.create(**payload.model_dump())
    await svc.session.commit()
    return LeadStageRead.model_validate(obj)


@router.patch(
    "/catalog/stages/{stage_id}",
    response_model=LeadStageRead,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def update_stage(
    stage_id: UUID, payload: LeadStageUpdate, svc: LeadService = Depends(_service),
) -> LeadStageRead:
    obj = await svc.stages.get(stage_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Stage not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await svc.session.commit()
    return LeadStageRead.model_validate(obj)


@router.delete(
    "/catalog/stages/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def delete_stage(stage_id: UUID, svc: LeadService = Depends(_service)):
    obj = await svc.stages.get(stage_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Stage not found")
    in_use = await svc.session.scalar(
        select(func.count(Lead.id)).where(Lead.stage_id == stage_id),
    )
    if in_use:
        raise HTTPException(status_code=400, detail=f"Stage has {in_use} lead(s); cannot delete")
    await svc.session.delete(obj)
    await svc.session.commit()
    return None


# ----- Sources -----

@router.get("/catalog/sources", response_model=list[LeadSourceRead])
async def list_sources(svc: LeadService = Depends(_service)) -> list[LeadSourceRead]:
    return [LeadSourceRead.model_validate(s) for s in await svc.list_sources()]


@router.post(
    "/catalog/sources",
    response_model=LeadSourceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def create_source(payload: LeadSourceCreate, svc: LeadService = Depends(_service)) -> LeadSourceRead:
    obj = await svc.sources.create(**payload.model_dump())
    await svc.session.commit()
    return LeadSourceRead.model_validate(obj)


@router.patch(
    "/catalog/sources/{source_id}",
    response_model=LeadSourceRead,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def update_source(
    source_id: UUID, payload: LeadSourceUpdate, svc: LeadService = Depends(_service),
) -> LeadSourceRead:
    obj = await svc.sources.get(source_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Source not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await svc.session.commit()
    return LeadSourceRead.model_validate(obj)


@router.delete(
    "/catalog/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def delete_source(source_id: UUID, svc: LeadService = Depends(_service)):
    obj = await svc.sources.get(source_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Source not found")
    await svc.session.delete(obj)
    await svc.session.commit()
    return None


# ----- Lost reasons -----

@router.get("/catalog/lost-reasons", response_model=list[LeadLostReasonRead])
async def list_lost_reasons(svc: LeadService = Depends(_service)) -> list[LeadLostReasonRead]:
    return [LeadLostReasonRead.model_validate(r) for r in await svc.list_lost_reasons()]


@router.post(
    "/catalog/lost-reasons",
    response_model=LeadLostReasonRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def create_lost_reason(payload: LeadLostReasonCreate, svc: LeadService = Depends(_service)) -> LeadLostReasonRead:
    obj = await svc.lost_reasons.create(**payload.model_dump())
    await svc.session.commit()
    return LeadLostReasonRead.model_validate(obj)


@router.patch(
    "/catalog/lost-reasons/{reason_id}",
    response_model=LeadLostReasonRead,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def update_lost_reason(
    reason_id: UUID, payload: LeadLostReasonUpdate, svc: LeadService = Depends(_service),
) -> LeadLostReasonRead:
    obj = await svc.lost_reasons.get(reason_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reason not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await svc.session.commit()
    return LeadLostReasonRead.model_validate(obj)


@router.delete(
    "/catalog/lost-reasons/{reason_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.LEADS_SETTINGS))],
)
async def delete_lost_reason(reason_id: UUID, svc: LeadService = Depends(_service)):
    obj = await svc.lost_reasons.get(reason_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reason not found")
    await svc.session.delete(obj)
    await svc.session.commit()
    return None
