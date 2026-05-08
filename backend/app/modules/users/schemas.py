from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema
from app.db.enums import UserRole
from app.utils.phone import normalize_phone


class UserBase(AppSchema):
    phone: str = Field(min_length=4, max_length=20)
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole

    @field_validator("phone")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_phone(v)


class UserCreate(UserBase):
    """Used by SuperAdmin/Admin to manually create staff users."""

    password: str | None = Field(default=None, min_length=8, max_length=100)
    is_active: bool = True


class UserUpdate(AppSchema):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserPasswordChange(AppSchema):
    new_password: str = Field(min_length=8, max_length=100)


class UserRead(IdSchema, TimestampedSchema):
    phone: str
    email: str | None = None
    full_name: str | None = None
    role: UserRole
    is_active: bool
    is_phone_verified: bool
    last_login_at: datetime | None = None


class UserPublic(IdSchema):
    """Slim public-facing variant (used in nested responses)."""

    full_name: str | None = None
    role: UserRole
