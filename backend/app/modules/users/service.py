from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.db.enums import UserRole
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserPasswordChange, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def list(
        self,
        *,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[User], int]:
        offset = (page - 1) * size
        return await self.repo.list_filtered(
            role=role, is_active=is_active, search=search, limit=size, offset=offset
        )

    async def get(self, user_id: UUID) -> User:
        user = await self.repo.get(user_id)
        if not user or user.deleted_at is not None:
            raise NotFoundError("User not found")
        return user

    async def create(self, payload: UserCreate, *, created_by_id: UUID | None = None) -> User:
        if payload.role == UserRole.SUPERADMIN:
            raise ValidationError("Cannot create superadmin via this endpoint")
        if payload.role == UserRole.APPLICANT:
            raise ValidationError(
                "Applicants are created via the applicant flow (Phase 6)"
            )
        if await self.repo.get_by_phone(payload.phone):
            raise ConflictError("User with this phone already exists")
        if payload.email and await self.repo.get_by_email(payload.email):
            raise ConflictError("User with this email already exists")

        data = payload.model_dump(exclude={"password"})
        if payload.password:
            data["password_hash"] = hash_password(payload.password)
        data["created_by_id"] = created_by_id
        # Staff accounts created by admin are pre-verified; they log in with password.
        data["is_phone_verified"] = True

        return await self.repo.create(**data)

    async def update(self, user_id: UUID, payload: UserUpdate) -> User:
        user = await self.get(user_id)
        if user.role == UserRole.SUPERADMIN and payload.role is not None and payload.role != UserRole.SUPERADMIN:
            raise ValidationError("Cannot demote a superadmin")

        data = payload.model_dump(exclude_unset=True)

        # Phone change: ensure uniqueness against other users.
        new_phone = data.get("phone")
        if new_phone and new_phone != user.phone:
            existing = await self.repo.get_by_phone(new_phone)
            if existing and existing.id != user.id:
                raise ValidationError("Bu telefon raqami allaqachon ro'yxatdan o'tgan")

        return await self.repo.update(user, **data)

    async def change_password(self, user_id: UUID, payload: UserPasswordChange) -> User:
        user = await self.get(user_id)
        return await self.repo.update(user, password_hash=hash_password(payload.new_password))

    async def deactivate(self, user_id: UUID) -> User:
        user = await self.get(user_id)
        if user.role == UserRole.SUPERADMIN:
            raise ValidationError("Cannot deactivate superadmin")
        return await self.repo.update(user, is_active=False)

    async def soft_delete(self, user_id: UUID) -> None:
        """Hard-delete the user.

        Despite the legacy name, this fully removes the row so the phone
        becomes available for fresh registration. Cascading FKs:
          • refresh_tokens (CASCADE)  — gone with the user
          • created_by_id, assigned_to_id, registered_by_id (SET NULL)
          • applicants/diploms/applications etc are NOT cascaded — the
            check below blocks the delete if any exist so we don't silently
            orphan or remove real domain data.
        """
        user = await self.get(user_id)
        if user.role == UserRole.SUPERADMIN:
            raise ValidationError("Cannot delete superadmin")

        # Block deletion if applicant data exists — admin must purge those
        # explicitly. Avoids accidental loss of applications/contracts/etc.
        from sqlalchemy import select, func
        from app.modules.applicants.models import Applicant
        applicant_count = await self.session.scalar(
            select(func.count()).select_from(Applicant).where(Applicant.user_id == user.id)
        )
        if applicant_count and applicant_count > 0:
            raise ValidationError(
                "Foydalanuvchini o'chirib bo'lmaydi: bog'liq abituriyent "
                "ma'lumotlari mavjud. Avval abituriyent profilini o'chiring."
            )

        await self.session.delete(user)
        await self.session.flush()
