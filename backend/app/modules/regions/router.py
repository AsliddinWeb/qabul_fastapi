from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_permission
from app.core.permissions import Permission
from app.modules.regions.schemas import (
    CountryCreate,
    CountryRead,
    CountryUpdate,
    DistrictCreate,
    DistrictRead,
    DistrictUpdate,
    RegionCreate,
    RegionRead,
    RegionUpdate,
)
from app.modules.regions.service import RegionsService

router = APIRouter()
require_write = require_permission(Permission.REGIONS_WRITE)


def _service(session: AsyncSession = Depends(get_db)) -> RegionsService:
    return RegionsService(session)


# ---------- Countries ----------
@router.get("/countries", response_model=list[CountryRead])
async def list_countries(svc: RegionsService = Depends(_service)) -> list[CountryRead]:
    rows = await svc.list_countries()
    return [CountryRead.model_validate(r) for r in rows]


@router.post(
    "/countries",
    response_model=CountryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
async def create_country(payload: CountryCreate, svc: RegionsService = Depends(_service)) -> CountryRead:
    obj = await svc.create_country(payload)
    await svc.session.commit()
    return CountryRead.model_validate(obj)


@router.patch(
    "/countries/{country_id}",
    response_model=CountryRead,
    dependencies=[Depends(require_write)],
)
async def update_country(
    country_id: UUID,
    payload: CountryUpdate,
    svc: RegionsService = Depends(_service),
) -> CountryRead:
    obj = await svc.update_country(country_id, payload)
    await svc.session.commit()
    return CountryRead.model_validate(obj)


@router.delete(
    "/countries/{country_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write)],
)
async def delete_country(country_id: UUID, svc: RegionsService = Depends(_service)) -> None:
    await svc.delete_country(country_id)
    await svc.session.commit()


# ---------- Regions ----------
@router.get("/regions", response_model=list[RegionRead])
async def list_regions(
    country_id: UUID | None = Query(default=None),
    svc: RegionsService = Depends(_service),
) -> list[RegionRead]:
    rows = await svc.list_regions(country_id=country_id)
    return [RegionRead.model_validate(r) for r in rows]


@router.post(
    "/regions",
    response_model=RegionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
async def create_region(payload: RegionCreate, svc: RegionsService = Depends(_service)) -> RegionRead:
    obj = await svc.create_region(payload)
    await svc.session.commit()
    return RegionRead.model_validate(obj)


@router.patch(
    "/regions/{region_id}",
    response_model=RegionRead,
    dependencies=[Depends(require_write)],
)
async def update_region(
    region_id: UUID,
    payload: RegionUpdate,
    svc: RegionsService = Depends(_service),
) -> RegionRead:
    obj = await svc.update_region(region_id, payload)
    await svc.session.commit()
    return RegionRead.model_validate(obj)


@router.delete(
    "/regions/{region_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write)],
)
async def delete_region(region_id: UUID, svc: RegionsService = Depends(_service)) -> None:
    await svc.delete_region(region_id)
    await svc.session.commit()


# ---------- Districts ----------
@router.get("/districts", response_model=list[DistrictRead])
async def list_districts(
    region_id: UUID | None = Query(default=None),
    svc: RegionsService = Depends(_service),
) -> list[DistrictRead]:
    rows = await svc.list_districts(region_id=region_id)
    return [DistrictRead.model_validate(r) for r in rows]


@router.post(
    "/districts",
    response_model=DistrictRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
async def create_district(
    payload: DistrictCreate,
    svc: RegionsService = Depends(_service),
) -> DistrictRead:
    obj = await svc.create_district(payload)
    await svc.session.commit()
    return DistrictRead.model_validate(obj)


@router.patch(
    "/districts/{district_id}",
    response_model=DistrictRead,
    dependencies=[Depends(require_write)],
)
async def update_district(
    district_id: UUID,
    payload: DistrictUpdate,
    svc: RegionsService = Depends(_service),
) -> DistrictRead:
    obj = await svc.update_district(district_id, payload)
    await svc.session.commit()
    return DistrictRead.model_validate(obj)


@router.delete(
    "/districts/{district_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write)],
)
async def delete_district(district_id: UUID, svc: RegionsService = Depends(_service)) -> None:
    await svc.delete_district(district_id)
    await svc.session.commit()
