"""Operations endpoints for CRM queue inspection / DLQ recovery.

Surface
-------
GET    /integrations/crm/stats             → counts (pending, dlq)
GET    /integrations/crm/pending           → upcoming entries (next attempt time)
GET    /integrations/crm/dlq               → dead-lettered entries
POST   /integrations/crm/dlq/{id}/retry    → re-queue an entry
DELETE /integrations/crm/dlq/{id}          → drop a dead entry
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis

from app.core.dependencies import get_redis_client, require_permission
from app.core.exceptions import NotFoundError
from app.core.permissions import Permission
from app.core.schemas import AppSchema, MessageResponse
from app.integrations.crm.queue import CrmQueue

router = APIRouter()
_admin = Depends(require_permission(Permission.INTEGRATIONS_ADMIN))


class CrmQueueStats(AppSchema):
    pending: int
    dlq: int


@router.get("/stats", response_model=CrmQueueStats, dependencies=[_admin])
async def stats(redis: Redis = Depends(get_redis_client)) -> CrmQueueStats:
    q = CrmQueue(redis)
    return CrmQueueStats(pending=await q.pending_count(), dlq=await q.dlq_count())


@router.get("/pending", response_model=list[dict], dependencies=[_admin])
async def list_pending(
    limit: int = Query(default=50, ge=1, le=500),
    redis: Redis = Depends(get_redis_client),
) -> list[dict]:
    return await CrmQueue(redis).list_pending(limit=limit)


@router.get("/dlq", response_model=list[dict], dependencies=[_admin])
async def list_dlq(
    limit: int = Query(default=100, ge=1, le=1000),
    redis: Redis = Depends(get_redis_client),
) -> list[dict]:
    return await CrmQueue(redis).list_dlq(limit=limit)


@router.post(
    "/dlq/{item_id}/retry",
    response_model=MessageResponse,
    dependencies=[_admin],
)
async def retry_dlq(item_id: str, redis: Redis = Depends(get_redis_client)) -> MessageResponse:
    ok = await CrmQueue(redis).requeue_dlq(item_id)
    if not ok:
        raise NotFoundError(f"DLQ item '{item_id}' not found")
    return MessageResponse(message="requeued", data={"id": item_id})


@router.delete(
    "/dlq/{item_id}",
    response_model=MessageResponse,
    dependencies=[_admin],
)
async def drop_dlq(item_id: str, redis: Redis = Depends(get_redis_client)) -> MessageResponse:
    ok = await CrmQueue(redis).drop_dlq(item_id)
    if not ok:
        raise NotFoundError(f"DLQ item '{item_id}' not found")
    return MessageResponse(message="dropped", data={"id": item_id})


# Suppress unused import warning if HTTPException, status fall out
_ = HTTPException, status
