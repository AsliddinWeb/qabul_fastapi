from __future__ import annotations

from app.core.repository import BaseRepository
from app.modules.regions.models import Country, District, Region


class CountryRepository(BaseRepository[Country]):
    model = Country


class RegionRepository(BaseRepository[Region]):
    model = Region


class DistrictRepository(BaseRepository[District]):
    model = District
