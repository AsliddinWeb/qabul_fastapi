from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

TokenType = Literal["access", "refresh", "file_share"]

_pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")


# ---------- Password hashing ----------
def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd_ctx.verify(password, hashed)


# ---------- JWT ----------
def _create_token(subject: str, token_type: TokenType, ttl: timedelta, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(subject, "access", timedelta(minutes=settings.jwt_access_ttl_min), extra)


def create_refresh_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    return _create_token(subject, "refresh", timedelta(days=settings.jwt_refresh_ttl_days), extra)


def create_file_share_token(file_id: str, ttl_days: int = 90) -> str:
    """Long-lived JWT scoped to a single file_id.

    Used when we ship a download URL out-of-band — e.g. SMS link to
    a freshly-generated contract PDF — where the recipient won't
    have a session cookie or Authorization header. The token's
    `sub` is the file_id itself, and the dedicated "file_share"
    type prevents accidental cross-use with access tokens.
    """
    # subject == file_id so the download endpoint can verify the
    # token applies to the requested file and not some other file
    # the leaked token might match.
    return _create_token(file_id, "file_share", timedelta(days=ttl_days))


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def hash_refresh_token(token: str) -> str:
    """Stable, deterministic hash for refresh-token DB lookup.

    JWT signature already authenticates the token; we only persist a hash so
    revocation works without storing the plaintext.
    """
    salted = f"{settings.app_secret_key}:{token}".encode()
    return hashlib.sha256(salted).hexdigest()
