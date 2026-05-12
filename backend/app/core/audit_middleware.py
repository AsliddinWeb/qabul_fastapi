"""Automatic audit logging for every successful write request.

Most modules already call `AuditService.log(...)` explicitly for the
semantically interesting events (application.review, lead.move, ...).
But several CRUD endpoints (DELETE in particular) were never wired up,
so destructive actions silently disappeared from the audit trail.

This middleware fills the gap by recording a generic row for every 2xx
POST / PATCH / PUT / DELETE on the API. Semantic logs from services
keep their own descriptive actions ("application.review"); these
middleware-emitted rows use HTTP-derived actions like
"applications.delete" / "applications.update" so they're easy to tell
apart.

We open a fresh DB session here because the request's session is
already closed by the time we reach the response phase.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID, uuid4

from fastapi import Request, Response
from sqlalchemy import insert

from app.config import settings
from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.session import async_session_factory
from app.modules.audit.models import AuditLog

logger = get_logger("audit_middleware")

# Methods we treat as mutations worth recording.
_WRITE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})

# Paths that produce far too much noise to be useful in audit. Keep this
# minimal — over-filtering defeats the point of the middleware.
_SKIP_PATH_PREFIXES: tuple[str, ...] = (
    "/healthz",
    "/openapi.json",
)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _parse_path(path: str) -> tuple[str | None, UUID | None, str]:
    """Pull (entity_type, entity_id, trailing_action) out of an API path.

    /api/v1/applications/abc-uuid/review → ("applications", abc-uuid, "review")
    /api/v1/applications/abc-uuid       → ("applications", abc-uuid, "")
    /api/v1/applications                → ("applications", None,     "")
    """
    prefix = settings.api_v1_prefix.rstrip("/")
    rel = path
    if prefix and rel.startswith(prefix):
        rel = rel[len(prefix):]
    rel = rel.strip("/")
    if not rel:
        return None, None, ""

    parts = rel.split("/")
    entity_type = parts[0] if parts else None
    entity_id: UUID | None = None
    trailing_parts: list[str] = []
    for p in parts[1:]:
        if _UUID_RE.match(p):
            try:
                entity_id = UUID(p)
                continue
            except ValueError:
                pass
        trailing_parts.append(p)
    return entity_type, entity_id, ".".join(trailing_parts)


def _action_for(method: str, entity_type: str | None, trailing: str) -> str:
    base = entity_type or "request"
    if trailing:
        return f"{base}.{trailing}.{method.lower()}"
    verb = {
        "POST": "create",
        "PATCH": "update",
        "PUT": "update",
        "DELETE": "delete",
    }.get(method.upper(), method.lower())
    return f"{base}.{verb}"


def _extract_user_id(request: Request) -> UUID | None:
    authz = request.headers.get("authorization") or ""
    if not authz.lower().startswith("bearer "):
        # Some endpoints (PDF preview iframe) pass the token as ?token=.
        token = request.query_params.get("token")
    else:
        token = authz.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return UUID(str(sub))
    except (TypeError, ValueError):
        return None


async def audit_writes_middleware(request: Request, call_next):
    """ASGI middleware: log every 2xx mutation after the response is built."""
    response: Response = await call_next(request)

    try:
        method = request.method.upper()
        if method not in _WRITE_METHODS:
            return response
        if response.status_code < 200 or response.status_code >= 300:
            return response

        path = request.url.path
        if any(path.startswith(p) for p in _SKIP_PATH_PREFIXES):
            return response

        # Only API requests should hit audit — anything else is static/health.
        api_prefix = settings.api_v1_prefix.rstrip("/")
        if api_prefix and not path.startswith(api_prefix):
            return response

        # /audit itself is read-only, but be defensive and ignore self-writes.
        if path.startswith(f"{api_prefix}/audit"):
            return response

        # Endpoint code already wrote a semantic audit row for this request
        # (AuditService.log sets this flag). Skip emitting the generic
        # http-derived row so the audit detail page doesn't get a duplicate
        # entry with only {path, method, status}.
        if getattr(request.state, "audit_logged", False):
            return response

        entity_type, entity_id, trailing = _parse_path(path)
        action = _action_for(method, entity_type, trailing)
        user_id = _extract_user_id(request)

        changes = {
            "method": method,
            "path": path,
            "status": response.status_code,
        }
        # Tag rows produced by the middleware so the UI can group them apart
        # from the semantic logs services emit themselves.
        changes["_source"] = "http_middleware"

        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

        async with async_session_factory() as session:
            # NOTE: audit_logs.id is NOT NULL with no server-side DEFAULT in
            # the bootstrap DDL, and `created_at` carries a frozen-timestamp
            # default. SQLAlchemy Core `insert(...).values(...)` doesn't
            # apply the Python-level UUIDPKMixin / TimestampMixin defaults,
            # so we must populate id + created_at explicitly here or the
            # insert silently raises and every middleware-emitted log is
            # lost.
            await session.execute(
                insert(AuditLog).values(
                    id=uuid4(),
                    created_at=datetime.now(timezone.utc),
                    action=action,
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    changes=changes,
                    ip_address=ip,
                    user_agent=ua,
                )
            )
            await session.commit()
    except Exception as exc:  # never break the response over an audit failure
        logger.error("audit_middleware.failed", error=str(exc), path=str(request.url.path))

    return response


__all__: Iterable[str] = ("audit_writes_middleware",)
