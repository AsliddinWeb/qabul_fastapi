from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.core.schemas import MessageResponse, PageResponse
from app.db.enums import UserRole
from app.modules.audit.service import AuditService
from app.modules.users.schemas import (
    UserCreate,
    UserPasswordChange,
    UserRead,
    UserSelfPasswordChange,
    UserUpdate,
)
from app.modules.users.service import UserService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(session)


@router.get("/me", response_model=UserRead)
async def me(
    current: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(_service),
) -> UserRead:
    user = await svc.get(UUID(current.user_id))
    return UserRead.model_validate(user)


# NOTE: must be declared before "/{user_id}/password" so "me" isn't parsed
# as a UUID path param. Any authenticated staff can change their OWN password
# (no admin permission needed) — the current password is the authorisation.
@router.put("/me/password", response_model=MessageResponse)
async def change_own_password(
    payload: UserSelfPasswordChange,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(_service),
) -> MessageResponse:
    await svc.change_own_password(UUID(current.user_id), payload)
    await AuditService(svc.session).log(
        "user.change_own_password",
        user_id=UUID(current.user_id),
        entity_type="users",
        entity_id=UUID(current.user_id),
        request=request,
    )
    await svc.session.commit()
    return MessageResponse(message="password_changed")


@router.get("/public-lookup")
async def public_user_lookup(
    ids: str | None = Query(default=None, description="Comma-separated UUIDs"),
    role: str | None = Query(default=None, description="Filter by role (e.g. 'operator')"),
    limit: int = Query(default=200, ge=1, le=500),
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Bulk minimal user info ({id, full_name, phone, role}) — auth-only.

    Two query shapes:
      - ?ids=u1,u2,u3 → exact lookup. Used by detail pages to resolve
        actor names (registered_by_id / reviewed_by_id / created_by_id)
        without forcing operators to also hold USERS_LIST.
      - ?role=operator → list-by-role. Used to populate the "Operator"
        filter dropdown on the applications / contracts / leads list
        pages; operators don't have users.list permission, so they
        used to get a 403 even when the dropdown was the only thing
        the page needed.

    Both shapes return ONLY public-safe fields (no permissions,
    no audit timestamps, no password state). Up to 500 rows per call.
    """
    from sqlalchemy import select as _select
    from app.modules.users.models import User as _UserModel

    stmt = _select(
        _UserModel.id, _UserModel.full_name, _UserModel.phone,
        _UserModel.role, _UserModel.referral_code,
    )

    if ids:
        raw = [s.strip() for s in ids.split(",") if s.strip()]
        parsed: list[UUID] = []
        for token in raw:
            try:
                parsed.append(UUID(token))
            except (TypeError, ValueError):
                continue
        if not parsed:
            return []
        stmt = stmt.where(_UserModel.id.in_(parsed))
    elif role:
        # Don't let arbitrary strings through to the enum — enumerate.
        try:
            from app.db.enums import UserRole
            role_enum = UserRole(role)
        except ValueError:
            return []
        stmt = stmt.where(_UserModel.role == role_enum)
        # Stable order for the dropdown; cheap because rows are few.
        stmt = stmt.order_by(_UserModel.full_name.asc().nulls_last())
    else:
        # Neither filter set — refuse rather than dumping every user.
        return []

    stmt = stmt.limit(limit)

    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": str(uid),
            "full_name": fn,
            "phone": ph,
            "role": r.value if r else None,
            "referral_code": code,
        }
        for uid, fn, ph, r, code in rows
    ]


@router.get(
    "",
    response_model=PageResponse[UserRead],
    dependencies=[Depends(require_permission(Permission.USERS_LIST))],
)
async def list_users(
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    svc: UserService = Depends(_service),
) -> PageResponse[UserRead]:
    items, total = await svc.list(
        role=role, is_active=is_active, search=search, page=page, size=size
    )
    return PageResponse[UserRead].build(
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/export.csv",
    dependencies=[Depends(require_permission(Permission.USERS_LIST))],
)
async def export_users_csv(
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    svc: UserService = Depends(_service),
) -> Response:
    """Export filtered users to CSV."""
    items, _ = await svc.list(
        role=role, is_active=is_active, search=search, page=1, size=10_000,
    )
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow([
        "F.I.Sh.", "Telefon", "Email", "Rol", "Faol", "Konsalting", "Yaratilgan",
    ])
    for u in items:
        w.writerow([
            u.full_name or "",
            u.phone or "",
            u.email or "",
            (u.role.value if u.role else ""),
            "ha" if u.is_active else "yo'q",
            "ha" if getattr(u, "is_consulting", False) else "",
            u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
        ])
    fn = f"users-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.USERS_CREATE))],
)
async def create_user(
    payload: UserCreate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(_service),
) -> UserRead:
    obj = await svc.create(payload, created_by_id=UUID(current.user_id))
    await AuditService(svc.session).log(
        "user.create",
        user_id=UUID(current.user_id),
        entity_type="users",
        entity_id=obj.id,
        changes={"role": obj.role.value, "phone": obj.phone},
        request=request,
    )
    await svc.session.commit()
    return UserRead.model_validate(obj)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission(Permission.USERS_READ))],
)
async def get_user(user_id: UUID, svc: UserService = Depends(_service)) -> UserRead:
    obj = await svc.get(user_id)
    return UserRead.model_validate(obj)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission(Permission.USERS_UPDATE))],
)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(_service),
) -> UserRead:
    obj = await svc.update(user_id, payload)
    await AuditService(svc.session).log(
        "user.update",
        user_id=UUID(current.user_id),
        entity_type="users",
        entity_id=obj.id,
        changes=payload.model_dump(exclude_unset=True),
        request=request,
    )
    await svc.session.commit()
    return UserRead.model_validate(obj)


@router.post(
    "/{user_id}/password",
    response_model=UserRead,
    dependencies=[Depends(require_permission(Permission.USERS_RESET_PASSWORD))],
)
async def reset_password(
    user_id: UUID,
    payload: UserPasswordChange,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(_service),
) -> UserRead:
    obj = await svc.change_password(user_id, payload)
    await AuditService(svc.session).log(
        "user.reset_password",
        user_id=UUID(current.user_id),
        entity_type="users",
        entity_id=obj.id,
        request=request,
    )
    await svc.session.commit()
    return UserRead.model_validate(obj)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_permission(Permission.USERS_DELETE))],
)
async def delete_user(
    user_id: UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: UserService = Depends(_service),
) -> Response:
    await svc.soft_delete(user_id)
    await AuditService(svc.session).log(
        "user.delete",
        user_id=UUID(current.user_id),
        entity_type="users",
        entity_id=user_id,
        request=request,
    )
    await svc.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/bulk-delete",
    dependencies=[Depends(require_permission(Permission.USERS_DELETE))],
)
async def bulk_delete_users(
    payload: dict,
    svc: UserService = Depends(_service),
) -> dict:
    """Bulk-delete users. Soft-delete via cascade (same as the per-row
    endpoint). Skips IDs that fail (e.g. attempting to delete a
    superadmin — service-layer guard rejects it)."""
    ids_raw = payload.get("ids") or []
    if not isinstance(ids_raw, list) or not ids_raw:
        raise HTTPException(status_code=400, detail="ids list is required")
    try:
        ids = [UUID(str(i)) for i in ids_raw]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid id in list")
    deleted = 0
    skipped = 0
    for uid in ids:
        try:
            await svc.soft_delete(uid)
            deleted += 1
        except Exception:
            skipped += 1
    await svc.session.commit()
    return {"deleted": deleted, "skipped": skipped}


@router.post(
    "/bulk-set-active",
    dependencies=[Depends(require_permission(Permission.USERS_UPDATE))],
)
async def bulk_set_active(
    payload: dict,
    svc: UserService = Depends(_service),
) -> dict:
    """Bulk activate/deactivate users. payload = {ids: [...], active: bool}."""
    from app.modules.users.schemas import UserUpdate
    ids_raw = payload.get("ids") or []
    active = bool(payload.get("active"))
    if not isinstance(ids_raw, list) or not ids_raw:
        raise HTTPException(status_code=400, detail="ids list is required")
    try:
        ids = [UUID(str(i)) for i in ids_raw]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid id in list")
    updated = 0
    skipped = 0
    for uid in ids:
        try:
            await svc.update(uid, UserUpdate(is_active=active))
            updated += 1
        except Exception:
            skipped += 1
    await svc.session.commit()
    return {"updated": updated, "skipped": skipped}
