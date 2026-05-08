from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.dictionaries.models import DictionaryItem, DictionaryType
from app.modules.dictionaries.repository import (
    DictionaryItemRepository,
    DictionaryTypeRepository,
)
from app.modules.dictionaries.schemas import (
    DictionaryItemCreate,
    DictionaryItemUpdate,
    DictionaryTypeCreate,
    DictionaryTypeUpdate,
)


class DictionaryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.types = DictionaryTypeRepository(session)
        self.items = DictionaryItemRepository(session)

    # ---------- Types ----------
    async def list_types(self) -> list[DictionaryType]:
        return await self.types.list(limit=200, order_by=DictionaryType.code)

    async def get_type(self, type_id: UUID) -> DictionaryType:
        obj = await self.types.get(type_id)
        if not obj:
            raise NotFoundError("Dictionary type not found")
        return obj

    async def get_type_by_code(self, code: str) -> DictionaryType:
        obj = await self.types.get_by_code(code)
        if not obj:
            raise NotFoundError(f"Dictionary type '{code}' not found")
        return obj

    async def create_type(self, payload: DictionaryTypeCreate) -> DictionaryType:
        if await self.types.get_by_code(payload.code):
            raise ConflictError(f"Dictionary type '{payload.code}' already exists")
        return await self.types.create(**payload.model_dump())

    async def update_type(self, type_id: UUID, payload: DictionaryTypeUpdate) -> DictionaryType:
        obj = await self.get_type(type_id)
        if obj.is_system:
            raise ValidationError("System dictionary types cannot be modified")
        return await self.types.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_type(self, type_id: UUID) -> None:
        obj = await self.get_type(type_id)
        if obj.is_system:
            raise ValidationError("System dictionary types cannot be deleted")
        await self.types.delete(obj)

    # ---------- Items ----------
    async def list_items(
        self,
        *,
        type_code: str | None = None,
        type_id: UUID | None = None,
        parent_id: UUID | None = None,
        active_only: bool = True,
    ) -> list[DictionaryItem]:
        if type_code:
            return await self.items.list_by_type_code(
                type_code, active_only=active_only, parent_id=parent_id
            )
        if type_id:
            return await self.items.list_by_type(
                type_id, active_only=active_only, parent_id=parent_id
            )
        raise ValidationError("Either type_code or type_id must be provided")

    async def get_item(self, item_id: UUID) -> DictionaryItem:
        obj = await self.items.get(item_id)
        if not obj:
            raise NotFoundError("Dictionary item not found")
        return obj

    async def create_item(self, type_id: UUID, payload: DictionaryItemCreate) -> DictionaryItem:
        await self.get_type(type_id)  # ensure type exists

        data = payload.model_dump(by_alias=False)
        # Coerce empty-string `code` to None so the unique (type_id, code) constraint
        # treats blank entries as distinct (Postgres NULLs are not equal to each other).
        if data.get("code") in ("", None):
            data["code"] = None
        else:
            dup = await self.items.get_by(type_id=type_id, code=data["code"])
            if dup:
                raise ConflictError("Bu kod bilan element allaqachon mavjud")

        if data.get("parent_id"):
            parent = await self.items.get(data["parent_id"])
            if not parent:
                raise ValidationError("parent_id does not exist")

        return await self.items.create(type_id=type_id, **data)

    async def update_item(self, item_id: UUID, payload: DictionaryItemUpdate) -> DictionaryItem:
        obj = await self.get_item(item_id)
        data = payload.model_dump(exclude_unset=True, by_alias=False)
        if "code" in data and data["code"] in ("", None):
            data["code"] = None
        return await self.items.update(obj, **data)

    async def delete_item(self, item_id: UUID) -> None:
        obj = await self.get_item(item_id)
        await self.items.delete(obj)
