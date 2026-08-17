from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.landing.models import LandingContent


class LandingService:
    """Read/write the single landing_content row."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _row(self) -> LandingContent | None:
        return (
            await self.session.execute(select(LandingContent).limit(1))
        ).scalar_one_or_none()

    async def get_data(self) -> dict[str, Any]:
        row = await self._row()
        return row.data if row and row.data else {}

    async def update_data(self, data: dict[str, Any]) -> dict[str, Any]:
        row = await self._row()
        if row is None:
            row = LandingContent(data=data)
            self.session.add(row)
        else:
            row.data = data
        await self.session.flush()
        return row.data
