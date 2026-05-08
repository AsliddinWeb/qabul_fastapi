from __future__ import annotations

from sqlalchemy import select

from app.core.repository import BaseRepository
from app.db.enums import UserRole
from app.modules.users.models import User


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_phone(self, phone: str) -> User | None:
        return await self.get_by(phone=phone)

    async def get_by_email(self, email: str) -> User | None:
        return await self.get_by(email=email)

    async def list_filtered(
        self,
        *,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        from sqlalchemy import func, or_

        stmt = select(User).where(User.deleted_at.is_(None))
        count_stmt = select(func.count(User.id)).where(User.deleted_at.is_(None))

        if role is not None:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
            count_stmt = count_stmt.where(User.is_active.is_(is_active))
        if search:
            like = f"%{search}%"
            cond = or_(User.phone.ilike(like), User.full_name.ilike(like))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)

        rows = list((await self.session.scalars(stmt)).all())
        total = await self.session.scalar(count_stmt) or 0
        return rows, total
