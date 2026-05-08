from __future__ import annotations

from pydantic import Field, field_validator

from app.core.schemas import AppSchema
from app.db.enums import UserRole
from app.utils.phone import normalize_phone


# ---------- OTP request/verify ----------
class OtpRequest(AppSchema):
    phone: str = Field(min_length=4, max_length=20)

    @field_validator("phone")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_phone(v)


class OtpRequestResponse(AppSchema):
    phone: str
    expires_in: int = Field(description="Seconds until the code expires")
    resend_after: int = Field(description="Seconds until the next OTP can be requested")
    delivered: bool = Field(default=True, description="True if real SMS was sent; False = dev mode (no SMS gateway)")
    code_length: int = Field(description="Number of digits the code will have (server-configured)")


class OtpVerify(AppSchema):
    phone: str = Field(min_length=4, max_length=20)
    code: str = Field(min_length=4, max_length=8, pattern="^[0-9]+$")

    @field_validator("phone")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_phone(v)


# ---------- Tokens ----------
class TokenPair(AppSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(AppSchema):
    refresh_token: str


# ---------- Password (staff) login ----------
class StaffLogin(AppSchema):
    phone: str = Field(min_length=4, max_length=20)
    password: str = Field(min_length=8, max_length=100)

    @field_validator("phone")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_phone(v)


class AuthSession(AppSchema):
    """Compact identity returned alongside tokens."""

    user_id: str
    phone: str
    role: UserRole
    is_phone_verified: bool


class LoginResponse(AppSchema):
    session: AuthSession
    tokens: TokenPair
