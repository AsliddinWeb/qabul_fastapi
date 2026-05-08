from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_permission
from app.core.permissions import Permission
from app.core.schemas import MessageResponse
from app.modules.dictionaries.schemas import (
    DictionaryItemCreate,
    DictionaryItemRead,
    DictionaryItemUpdate,
    DictionaryTypeCreate,
    DictionaryTypeRead,
    DictionaryTypeUpdate,
)
from app.modules.dictionaries.service import DictionaryService

router = APIRouter()

require_dict_write = require_permission(Permission.DICTIONARIES_WRITE)


def _service(session: AsyncSession = Depends(get_db)) -> DictionaryService:
    return DictionaryService(session)


# ---------- Types ----------
@router.get("/types", response_model=list[DictionaryTypeRead])
async def list_types(svc: DictionaryService = Depends(_service)) -> list[DictionaryTypeRead]:
    rows = await svc.list_types()
    return [DictionaryTypeRead.model_validate(r) for r in rows]


@router.post(
    "/types",
    response_model=DictionaryTypeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_dict_write)],
)
async def create_type(
    payload: DictionaryTypeCreate,
    svc: DictionaryService = Depends(_service),
) -> DictionaryTypeRead:
    obj = await svc.create_type(payload)
    await svc.session.commit()
    return DictionaryTypeRead.model_validate(obj)


@router.patch(
    "/types/{type_id}",
    response_model=DictionaryTypeRead,
    dependencies=[Depends(require_dict_write)],
)
async def update_type(
    type_id: UUID,
    payload: DictionaryTypeUpdate,
    svc: DictionaryService = Depends(_service),
) -> DictionaryTypeRead:
    obj = await svc.update_type(type_id, payload)
    await svc.session.commit()
    return DictionaryTypeRead.model_validate(obj)


@router.delete(
    "/types/{type_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_dict_write)],
)
async def delete_type(
    type_id: UUID,
    svc: DictionaryService = Depends(_service),
) -> MessageResponse:
    await svc.delete_type(type_id)
    await svc.session.commit()
    return MessageResponse(message="deleted")


# ---------- Items ----------
@router.get("/items", response_model=list[DictionaryItemRead])
async def list_items(
    type_code: str | None = Query(default=None, description="Dictionary type code (e.g. 'regions')"),
    type_id: UUID | None = Query(default=None),
    parent_id: UUID | None = Query(default=None, description="Filter by parent (for hierarchical types)"),
    active_only: bool = Query(default=True),
    svc: DictionaryService = Depends(_service),
) -> list[DictionaryItemRead]:
    rows = await svc.list_items(
        type_code=type_code,
        type_id=type_id,
        parent_id=parent_id,
        active_only=active_only,
    )
    return [DictionaryItemRead.model_validate(r) for r in rows]


@router.post(
    "/types/{type_id}/items",
    response_model=DictionaryItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_dict_write)],
)
async def create_item(
    type_id: UUID,
    payload: DictionaryItemCreate,
    svc: DictionaryService = Depends(_service),
) -> DictionaryItemRead:
    obj = await svc.create_item(type_id, payload)
    await svc.session.commit()
    return DictionaryItemRead.model_validate(obj)


@router.patch(
    "/items/{item_id}",
    response_model=DictionaryItemRead,
    dependencies=[Depends(require_dict_write)],
)
async def update_item(
    item_id: UUID,
    payload: DictionaryItemUpdate,
    svc: DictionaryService = Depends(_service),
) -> DictionaryItemRead:
    obj = await svc.update_item(item_id, payload)
    await svc.session.commit()
    return DictionaryItemRead.model_validate(obj)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_dict_write)],
)
async def delete_item(
    item_id: UUID,
    svc: DictionaryService = Depends(_service),
) -> Response:
    await svc.delete_item(item_id)
    await svc.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
