"""Create the initial SuperAdmin (idempotent).

Run inside container:  make superadmin
Run locally:           python -m scripts.create_superadmin

Reads phone/password from env vars OR stdin:
  SUPERADMIN_PHONE      e.g. +998901234567
  SUPERADMIN_PASSWORD   strong password
  SUPERADMIN_NAME       optional, default "Super Admin"

If a user with the given phone already exists, this script ensures they have
role=superadmin and is_active=true; password is updated only if explicitly given.
"""

from __future__ import annotations

import asyncio
import os
import sys
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.enums import UserRole
from app.db.session import async_session_factory

# Register all models so SQLAlchemy can resolve cross-table FK references
import app.db.models_registry  # noqa: F401

from app.modules.users.models import User
from app.utils.phone import normalize_phone

logger = get_logger("superadmin")


def _read(prompt: str, *, secret: bool = False) -> str:
    if not sys.stdin.isatty():
        raise SystemExit(f"Non-interactive: provide via env var instead. ({prompt})")
    return (getpass(prompt) if secret else input(prompt)).strip()


async def upsert_superadmin(
    session: AsyncSession,
    *,
    phone: str,
    password: str,
    full_name: str,
) -> User:
    res = await session.execute(select(User).where(User.phone == phone))
    user = res.scalar_one_or_none()

    if user:
        user.role = UserRole.SUPERADMIN
        user.is_active = True
        user.is_phone_verified = True
        if password:
            user.password_hash = hash_password(password)
        if full_name:
            user.full_name = full_name
        logger.info("superadmin.upserted", user_id=str(user.id), phone=phone)
        return user

    user = User(
        phone=phone,
        full_name=full_name,
        password_hash=hash_password(password),
        role=UserRole.SUPERADMIN,
        is_active=True,
        is_phone_verified=True,
    )
    session.add(user)
    await session.flush()
    logger.info("superadmin.created", user_id=str(user.id), phone=phone)
    return user


async def main() -> None:
    configure_logging(debug=False)

    phone_raw = os.getenv("SUPERADMIN_PHONE") or _read("Phone (E.164, e.g. +998901234567): ")
    phone = normalize_phone(phone_raw)

    password = os.getenv("SUPERADMIN_PASSWORD") or _read("Password: ", secret=True)
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    full_name = os.getenv("SUPERADMIN_NAME") or "Super Admin"

    async with async_session_factory() as session:
        async with session.begin():
            user = await upsert_superadmin(
                session, phone=phone, password=password, full_name=full_name
            )
    print(f"OK — superadmin id={user.id} phone={user.phone}")


if __name__ == "__main__":
    asyncio.run(main())
