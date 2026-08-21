from __future__ import annotations

from collections.abc import AsyncGenerator, Iterable
from uuid import UUID

from fastapi import Depends, Header
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.permissions import Permission, Role, has_permission
from app.core.redis import get_redis as _get_redis
from app.core.security import decode_token
from app.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_redis_client() -> AsyncGenerator[Redis, None]:
    client = _get_redis()
    try:
        yield client
    finally:
        await client.aclose()


# ---- Auth ----
class CurrentUser:
    """Lightweight identity extracted from JWT.

    Full user record is loaded by services when needed.
    """

    def __init__(self, user_id: str, role: Role, phone: str | None = None) -> None:
        self.user_id = user_id
        self.role = role
        self.phone = phone


def operator_scope(current: CurrentUser) -> UUID | None:
    """The `registered_by_id` an operator is confined to.

    Operators may only see the applicants they themselves registered (and the
    applications / diplomas / transfer-diplomas hanging off them). Every other
    staff role (admin, superadmin, director, accountant) sees everything, so
    this returns None for them — meaning "no ownership filter".
    """
    return UUID(current.user_id) if current.role == Role.OPERATOR else None


def _parse_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    token = _parse_bearer(authorization)
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Wrong token type")

    role_value = payload.get("role")
    user_id = payload.get("sub")
    if not user_id or not role_value:
        raise UnauthorizedError("Malformed token")

    try:
        role = Role(role_value)
    except ValueError as exc:
        raise UnauthorizedError("Unknown role") from exc

    return CurrentUser(user_id=str(user_id), role=role, phone=payload.get("phone"))


def require_roles(*roles: Role | Iterable[Role]):
    """Dependency factory: allow only users whose role is in `roles`.

    Prefer `require_permission` for new endpoints — it's more granular and
    survives role membership changes.
    """
    flat: set[Role] = set()
    for r in roles:
        if isinstance(r, Role):
            flat.add(r)
        else:
            flat.update(r)

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in flat:
            raise ForbiddenError("Insufficient role")
        return user

    return _checker


def require_permission(perm: Permission):
    """Dependency factory: allow only users whose role grants `perm`
    AND who have not had it explicitly revoked by an admin."""

    async def _checker(
        user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CurrentUser:
        if not has_permission(user.role, perm):
            raise ForbiddenError(f"Missing permission: {perm.value}")
        # Per-user revocation override — empty/null array means "no overrides".
        from sqlalchemy import select
        from app.modules.users.models import User as _UserModel
        from uuid import UUID as _UUID
        revoked = await db.scalar(
            select(_UserModel.permissions_revoked).where(_UserModel.id == _UUID(user.user_id))
        )
        if revoked and perm.value in revoked:
            raise ForbiddenError(f"Missing permission: {perm.value}")
        return user

    _checker.__name__ = f"require_permission_{perm.value.replace('.', '_')}"
    return _checker


async def require_root_superadmin(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Allow ONLY the single root superadmin (user.is_root_superadmin=True).

    Other superadmins are rejected — this is a deliberate one-person gate
    for the consulting-agency catalog so partner data stays compartmented.
    """
    from sqlalchemy import select
    from app.modules.users.models import User as UserModel
    from uuid import UUID as _UUID

    res = await db.execute(
        select(UserModel.is_root_superadmin).where(UserModel.id == _UUID(user.user_id))
    )
    is_root = res.scalar_one_or_none() or False
    if not is_root:
        raise ForbiddenError("Only the root superadmin can access this resource")
    return user


async def require_consulting_or_root(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Allow root superadmin OR any user with is_consulting=True.

    Used to gate read-only access to the consulting agencies list (so
    consulting-marked operators can pick an agency when filing/filtering
    applications).
    """
    from sqlalchemy import select
    from app.modules.users.models import User as UserModel
    from uuid import UUID as _UUID

    res = await db.execute(
        select(UserModel.is_root_superadmin, UserModel.is_consulting)
        .where(UserModel.id == _UUID(user.user_id))
    )
    row = res.first()
    if not row or not (row[0] or row[1]):
        raise ForbiddenError("Consulting access required")
    return user


def require_any_permission(*perms: Permission):
    """Dependency factory: allow if user has at least one of the given permissions."""

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(has_permission(user.role, p) for p in perms):
            names = ", ".join(p.value for p in perms)
            raise ForbiddenError(f"Missing any of: {names}")
        return user

    return _checker
