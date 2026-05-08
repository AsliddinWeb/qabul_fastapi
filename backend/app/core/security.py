from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

TokenType = Literal["access", "refresh"]

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
