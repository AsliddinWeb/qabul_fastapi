from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_permission
from app.core.permissions import Permission
from app.core.schemas import PageResponse
from app.modules.audit.schemas import AuditLogRead
from app.modules.audit.service import AuditService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(session)


@router.get(
    "",
    response_model=PageResponse[AuditLogRead],
    dependencies=[Depends(require_permission(Permission.AUDIT_READ))],
)
async def list_logs(
    user_id: UUID | None = Query(default=None),
    entity_type: str | None = Query(default=None, max_length=100),
    entity_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None, max_length=100),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    svc: AuditService = Depends(_service),
) -> PageResponse[AuditLogRead]:
    items, total = await svc.list(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=size,
        offset=(page - 1) * size,
    )
    return PageResponse[AuditLogRead].build(
        items=[AuditLogRead.model_validate(i) for i in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogRead,
    dependencies=[Depends(require_permission(Permission.AUDIT_READ))],
)
async def get_log(
    log_id: UUID,
    svc: AuditService = Depends(_service),
) -> AuditLogRead:
    item = await svc.get(log_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return AuditLogRead.model_validate(item)
