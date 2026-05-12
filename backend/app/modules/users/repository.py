from __future__ import annotations

import secrets
import string
from typing import Any

from sqlalchemy import select

from app.core.repository import BaseRepository
from app.db.enums import UserRole
from app.modules.users.models import User

# 36^6 ≈ 2.1B combinations — collisions are vanishingly rare; the retry loop
# below handles them just in case.
_REFERRAL_ALPHABET = string.ascii_uppercase + string.digits
_REFERRAL_CODE_LEN = 6


class UserRepository(BaseRepository[User]):
    model = User

    async def create(self, **kwargs: Any) -> User:
        """Wrap BaseRepository.create to guarantee every new user has a
        referral_code. Without this, applicants that signed up after the
        backfill migration (05_referrals.sql) ended up with NULL codes, so
        their personal share link never rendered in the admin UI.
        """
        if not kwargs.get("referral_code"):
            for _ in range(8):
                code = "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(_REFERRAL_CODE_LEN))
                if await self.get_by(referral_code=code) is None:
                    kwargs["referral_code"] = code
                    break
        return await super().create(**kwargs)

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
