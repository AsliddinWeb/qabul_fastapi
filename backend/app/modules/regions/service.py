from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.regions.models import Country, District, Region
from app.modules.regions.repository import CountryRepository, DistrictRepository, RegionRepository
from app.modules.regions.schemas import (
    CountryCreate,
    CountryUpdate,
    DistrictCreate,
    DistrictUpdate,
    RegionCreate,
    RegionUpdate,
)


class RegionsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.countries = CountryRepository(session)
        self.regions = RegionRepository(session)
        self.districts = DistrictRepository(session)

    # ---------- Countries ----------
    async def list_countries(self) -> list[Country]:
        return await self.countries.list(limit=200, order_by=Country.name)

    async def create_country(self, payload: CountryCreate) -> Country:
        if await self.countries.exists(name=payload.name):
            raise ConflictError(f"Country '{payload.name}' already exists")
        return await self.countries.create(**payload.model_dump())

    async def update_country(self, country_id: UUID, payload: CountryUpdate) -> Country:
        obj = await self.countries.get(country_id)
        if not obj:
            raise NotFoundError("Country not found")
        return await self.countries.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_country(self, country_id: UUID) -> None:
        obj = await self.countries.get(country_id)
        if not obj:
            raise NotFoundError("Country not found")
        await self.countries.delete(obj)

    # ---------- Regions ----------
    async def list_regions(self, *, country_id: UUID | None = None) -> list[Region]:
        where = Region.country_id == country_id if country_id else None
        return await self.regions.list(limit=500, order_by=Region.name, where=where)

    async def create_region(self, payload: RegionCreate) -> Region:
        if not await self.countries.exists(id=payload.country_id):
            raise NotFoundError("Country not found")
        if await self.regions.get_by(name=payload.name, country_id=payload.country_id):
            raise ConflictError(f"Region '{payload.name}' already exists in country")
        return await self.regions.create(**payload.model_dump())

    async def update_region(self, region_id: UUID, payload: RegionUpdate) -> Region:
        obj = await self.regions.get(region_id)
        if not obj:
            raise NotFoundError("Region not found")
        return await self.regions.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_region(self, region_id: UUID) -> None:
        obj = await self.regions.get(region_id)
        if not obj:
            raise NotFoundError("Region not found")
        await self.regions.delete(obj)

    # ---------- Districts ----------
    async def list_districts(self, *, region_id: UUID | None = None) -> list[District]:
        where = District.region_id == region_id if region_id else None
        return await self.districts.list(limit=2000, order_by=District.name, where=where)

    async def create_district(self, payload: DistrictCreate) -> District:
        if not await self.regions.exists(id=payload.region_id):
            raise NotFoundError("Region not found")
        if await self.districts.get_by(name=payload.name, region_id=payload.region_id):
            raise ConflictError(f"District '{payload.name}' already exists in region")
        return await self.districts.create(**payload.model_dump())

    async def update_district(self, district_id: UUID, payload: DistrictUpdate) -> District:
        obj = await self.districts.get(district_id)
        if not obj:
            raise NotFoundError("District not found")
        return await self.districts.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_district(self, district_id: UUID) -> None:
        obj = await self.districts.get(district_id)
        if not obj:
            raise NotFoundError("District not found")
        await self.districts.delete(obj)
