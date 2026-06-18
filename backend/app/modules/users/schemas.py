from __future__ import annotations

from datetime import datetime

from typing import Any

from pydantic import EmailStr, Field, field_validator

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema
from app.db.enums import UserRole
from app.utils.phone import normalize_phone


def _empty_to_none(v: Any) -> Any:
    """Treat empty/whitespace-only strings as None — needed because EmailStr
    rejects '' as invalid."""
    if isinstance(v, str) and not v.strip():
        return None
    return v


class UserBase(AppSchema):
    phone: str = Field(min_length=4, max_length=20)
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole

    @field_validator("phone")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("email", mode="before")
    @classmethod
    def _email_empty_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)


class UserCreate(UserBase):
    """Used by SuperAdmin/Admin to manually create staff users."""

    password: str | None = Field(default=None, min_length=8, max_length=100)
    is_active: bool = True
    is_consulting: bool = False
    # Operator-only flag — controls lead round-robin eligibility. New
    # operators default to TRUE so they start receiving leads immediately
    # without an extra admin step.
    accepts_leads: bool = True
    # Permissions the admin wants to deny up-front (subset of role defaults).
    # Honored at create time so admins can spin up an operator with reduced
    # rights in one round-trip rather than create-then-edit-revoke.
    permissions_revoked: list[str] = Field(default_factory=list)


class UserUpdate(AppSchema):
    phone: str | None = Field(default=None, min_length=4, max_length=20)
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    is_consulting: bool | None = None
    accepts_leads: bool | None = None
    permissions_revoked: list[str] | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, v: Any) -> Any:
        if v is None:
            return None
        v = _empty_to_none(v)
        if v is None:
            return None
        return normalize_phone(v)

    @field_validator("email", mode="before")
    @classmethod
    def _email_empty_to_none(cls, v: Any) -> Any:
        return _empty_to_none(v)


class UserPasswordChange(AppSchema):
    new_password: str = Field(min_length=8, max_length=100)


class UserRead(IdSchema, TimestampedSchema):
    phone: str
    email: str | None = None
    full_name: str | None = None
    role: UserRole
    is_active: bool
    is_phone_verified: bool
    is_consulting: bool = False
    is_root_superadmin: bool = False
    accepts_leads: bool = True
    permissions_revoked: list[str] = Field(default_factory=list)
    referral_code: str | None = None
    last_login_at: datetime | None = None


class UserPublic(IdSchema):
    """Slim public-facing variant (used in nested responses)."""

    full_name: str | None = None
    role: UserRole
