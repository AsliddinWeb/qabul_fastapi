from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.modules.audit.service import AuditService
from app.modules.journal import excel
from app.modules.journal.service import EVENT_LABELS, JournalService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> JournalService:
    return JournalService(session)


def _codes(raw: str | None) -> list[str] | None:
    return [c.strip() for c in raw.split(",") if c.strip()] if raw else None


@router.get("", dependencies=[Depends(require_permission(Permission.AUDIT_READ))])
async def list_journal(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    codes: str | None = Query(default=None, max_length=300),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    svc: JournalService = Depends(_service),
) -> dict:
    items, total = await svc.list_page(
        date_from=date_from, date_to=date_to, search=search, codes=_codes(codes),
        limit=size, offset=(page - 1) * size,
    )
    stats = await svc.stats(date_from=date_from, date_to=date_to, search=search)
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "stats": stats,
        "labels": EVENT_LABELS,
    }


@router.get("/export.xlsx", dependencies=[Depends(require_permission(Permission.AUDIT_READ))])
async def export_journal(
    view: Literal["dates", "applicants"] = Query(default="dates"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    codes: str | None = Query(default=None, max_length=300),
    request: Request = None,  # type: ignore[assignment]
    current: CurrentUser = Depends(get_current_user),
    svc: JournalService = Depends(_service),
) -> Response:
    period = excel.period_text(date_from, date_to)
    if view == "applicants":
        events = await svc.events_by_applicant(date_from=date_from, date_to=date_to, search=search)
        data = excel.build_by_applicants(events, period)
        slug = "abituriyentlar"
    else:
        events = await svc.events_by_date(date_from=date_from, date_to=date_to,
                                          search=search, codes=_codes(codes))
        data = excel.build_by_dates(events, period)
        slug = "sanalar"

    try:
        await AuditService(svc.session).log(
            "journal.export",
            user_id=UUID(current.user_id),
            entity_type="journal",
            changes={"view": view, "date_from": str(date_from or ""),
                     "date_to": str(date_to or ""), "rows": len(events)},
            request=request,
        )
        await svc.session.commit()
    except Exception:
        await svc.session.rollback()

    fn = f"tizim-daftari-{slug}-{datetime.now().strftime('%Y%m%d-%H%M')}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )
