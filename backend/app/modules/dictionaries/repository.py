from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.dictionaries.models import DictionaryItem, DictionaryType


class DictionaryTypeRepository(BaseRepository[DictionaryType]):
    model = DictionaryType

    async def get_by_code(self, code: str) -> DictionaryType | None:
        return await self.get_by(code=code)


class DictionaryItemRepository(BaseRepository[DictionaryItem]):
    model = DictionaryItem

    async def list_by_type(
        self,
        type_id: UUID,
        *,
        active_only: bool = True,
        parent_id: UUID | None = None,
    ) -> list[DictionaryItem]:
        stmt = select(DictionaryItem).where(DictionaryItem.type_id == type_id)
        if active_only:
            stmt = stmt.where(DictionaryItem.is_active.is_(True))
        if parent_id is not None:
            stmt = stmt.where(DictionaryItem.parent_id == parent_id)
        stmt = stmt.order_by(DictionaryItem.sort_order, DictionaryItem.name_uz)
        return list((await self.session.scalars(stmt)).all())

    async def list_by_type_code(
        self,
        type_code: str,
        *,
        active_only: bool = True,
        parent_id: UUID | None = None,
    ) -> list[DictionaryItem]:
        stmt = (
            select(DictionaryItem)
            .join(DictionaryType, DictionaryItem.type_id == DictionaryType.id)
            .where(DictionaryType.code == type_code)
        )
        if active_only:
            stmt = stmt.where(DictionaryItem.is_active.is_(True))
        if parent_id is not None:
            stmt = stmt.where(DictionaryItem.parent_id == parent_id)
        stmt = stmt.order_by(DictionaryItem.sort_order, DictionaryItem.name_uz)
        return list((await self.session.scalars(stmt)).all())
