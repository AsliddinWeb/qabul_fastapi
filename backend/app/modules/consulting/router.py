"""Consulting agencies CRUD.

Two-tier permission model:
  • require_root_superadmin — full CRUD (create, update, delete).
    This is intentionally locked to the single root user; even other
    superadmins cannot manage agencies.
  • require_consulting_or_root — read-only list, used by consulting-marked
    operators when picking an agency on the application form.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_db,
    require_consulting_or_root,
    require_root_superadmin,
)
from app.modules.consulting.models import ConsultingAgency
from app.modules.consulting.schemas import (
    ConsultingAgencyCreate,
    ConsultingAgencyRead,
    ConsultingAgencyUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=list[ConsultingAgencyRead],
    dependencies=[Depends(require_consulting_or_root)],
)
async def list_agencies(
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> list[ConsultingAgencyRead]:
    stmt = select(ConsultingAgency).order_by(ConsultingAgency.name.asc())
    if active_only:
        stmt = stmt.where(ConsultingAgency.is_active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    return [ConsultingAgencyRead.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=ConsultingAgencyRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_root_superadmin)],
)
async def create_agency(
    payload: ConsultingAgencyCreate,
    db: AsyncSession = Depends(get_db),
) -> ConsultingAgencyRead:
    obj = ConsultingAgency(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return ConsultingAgencyRead.model_validate(obj)


@router.patch(
    "/{agency_id}",
    response_model=ConsultingAgencyRead,
    dependencies=[Depends(require_root_superadmin)],
)
async def update_agency(
    agency_id: UUID,
    payload: ConsultingAgencyUpdate,
    db: AsyncSession = Depends(get_db),
) -> ConsultingAgencyRead:
    res = await db.execute(select(ConsultingAgency).where(ConsultingAgency.id == agency_id))
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Konsalting agentligi topilmadi")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return ConsultingAgencyRead.model_validate(obj)


@router.delete(
    "/{agency_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_root_superadmin)],
)
async def delete_agency(
    agency_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    res = await db.execute(select(ConsultingAgency).where(ConsultingAgency.id == agency_id))
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Konsalting agentligi topilmadi")
    await db.delete(obj)
    await db.commit()
