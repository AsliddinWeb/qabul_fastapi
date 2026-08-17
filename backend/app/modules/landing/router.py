from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_permission
from app.core.permissions import Permission
from app.modules.landing.schemas import LandingContentRead, LandingContentUpdate
from app.modules.landing.service import LandingService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> LandingService:
    return LandingService(session)


@router.get("/content", response_model=LandingContentRead)
async def get_content(svc: LandingService = Depends(_service)) -> LandingContentRead:
    """Public: the Nuxt landing fetches this and merges it over its defaults."""
    return LandingContentRead(data=await svc.get_data())


@router.put(
    "/content",
    response_model=LandingContentRead,
    dependencies=[Depends(require_permission(Permission.LANDING_MANAGE))],
)
async def put_content(
    payload: LandingContentUpdate,
    svc: LandingService = Depends(_service),
) -> LandingContentRead:
    data = await svc.update_data(payload.data)
    await svc.session.commit()
    return LandingContentRead(data=data)
