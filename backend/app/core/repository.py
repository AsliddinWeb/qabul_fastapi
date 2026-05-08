"""Generic async repository — thin wrapper over SQLAlchemy 2.0.

Each module's repository inherits from this and adds query methods specific
to its domain. Service layer uses repositories — never sessions directly.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- read ----------
    async def get(self, id: UUID) -> ModelT | None:
        return await self.session.get(self.model, id)

    async def get_by(self, **filters: Any) -> ModelT | None:
        stmt = select(self.model).filter_by(**filters).limit(1)
        return (await self.session.scalars(stmt)).first()

    async def exists(self, **filters: Any) -> bool:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return (await self.session.scalar(stmt)) > 0

    async def count(self, *, where: Any | None = None) -> int:
        stmt = select(func.count()).select_from(self.model)
        if where is not None:
            stmt = stmt.where(where)
        return await self.session.scalar(stmt) or 0

    async def list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        order_by: Any | None = None,
        where: Any | None = None,
    ) -> list[ModelT]:
        stmt: Select[Any] = select(self.model)
        if where is not None:
            stmt = stmt.where(where)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        return list((await self.session.scalars(stmt)).all())

    # ---------- write ----------
    async def create(self, **kwargs: Any) -> ModelT:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        for k, v in kwargs.items():
            setattr(instance, k, v)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def delete_by_id(self, id: UUID) -> int:
        stmt = delete(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.rowcount or 0
