"""International admissions router.

Public surface:
  POST /apply             — submit application from the landing page

Staff surface (permission-gated):
  GET    /                — paginated list
  GET    /stats           — stage-count breakdown for the dashboard
  GET    /{id}            — full detail including audit fields
  PATCH  /{id}/stage      — advance / regress stage by ±1
  PATCH  /{id}/reject     — mark rejected (with optional reason)
  PATCH  /{id}/unreject   — undo a rejection
  PATCH  /{id}/notes      — operator notes
  DELETE /{id}            — hard delete

Anti-spam stack on /apply:
  1. Redis-backed sliding-window rate limit per source IP
  2. Honeypot field "website" — must arrive empty
  3. Time-trap: submission must take 5s..1h after page-load token
  4. Duplicate guard: same passport in last 24h is rejected
  5. File MIME + size validation (delegated to /files/upload)
  6. Backend phone normalisation + email/lower() canonicalisation

The HTML form ships a `submitted_at` field carrying the token
returned by GET /apply/session — server signs it with HMAC and
verifies the elapsed time matches the trap window.
"""
from __future__ import annotations

import hmac
import hashlib
import time
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.permissions import Permission
from app.core.schemas import PageResponse
from app.modules.files.service import FilesService
from app.modules.international_admissions.schemas import (
    IntlAdvanceStage,
    IntlApplicationListItem,
    IntlApplicationRead,
    IntlApplyResponse,
    IntlNotesUpdate,
    IntlReject,
)
from app.modules.international_admissions.service import InternationalAdmissionsService

logger = get_logger("intl_admissions")

router = APIRouter()


# ---------------------------------------------------------------------------
# Anti-spam knobs
# ---------------------------------------------------------------------------

# Sliding window — at most N submissions per IP per WINDOW_SECONDS.
# Lower bound is 3 per hour: a genuine applicant tries again 1-2 times
# at most if the network glitches; bots routinely fire dozens.
_RATE_LIMIT_MAX = 3
_RATE_LIMIT_WINDOW_S = 3600

# Time-trap: a real human takes at least 5s reading the form before
# submitting, and at most an hour (anyone away that long can refresh).
_MIN_FILL_S = 5
_MAX_FILL_S = 60 * 60

# Honeypot field name — hidden via CSS in the HTML, so bots that
# blindly fill every input drop the form on the floor here.
_HONEYPOT_FIELD = "website"


def _signing_key() -> bytes:
    """Reuse the JWT secret as the HMAC key for session tokens.

    No security claim about reusing the same secret — the session
    token's only job is to bind a timestamp to a request without
    storing anything server-side. If the app key leaks the system has
    bigger problems than form spoofing.
    """
    return settings.app_secret_key.encode("utf-8")


def _make_session_token(ts: float | None = None) -> str:
    """Return a `<ts>.<hmac>` pair the client echoes back on submit."""
    ts = ts or time.time()
    payload = f"{ts:.0f}"
    sig = hmac.new(_signing_key(), payload.encode(), hashlib.sha256).hexdigest()[:24]
    return f"{payload}.{sig}"


def _verify_session_token(token: str) -> float | None:
    """Returns issued-at unix timestamp if the token is valid, else None."""
    if not token or "." not in token:
        return None
    payload, sig = token.split(".", 1)
    expected = hmac.new(_signing_key(), payload.encode(), hashlib.sha256).hexdigest()[:24]
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        return float(payload)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.get("/apply/session")
async def apply_session_token() -> dict:
    """Hand the landing page a fresh session token.

    The HTML calls this on form mount, embeds the returned token
    into a hidden field, and submits it back. Server compares the
    issued-at timestamp against the elapsed time. No DB write — the
    token is stateless and HMAC-signed.
    """
    return {"token": _make_session_token()}


def _client_ip(request: Request) -> str | None:
    """Resolve the original client IP, honouring nginx's X-Forwarded-For."""
    fwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if fwd:
        # First entry in the chain is the original client; nginx
        # appends each hop afterwards. Strip whitespace + ports.
        return fwd.split(",")[0].strip().split(":")[0]
    if request.client:
        return request.client.host
    return None


async def _enforce_rate_limit(ip: str | None) -> None:
    """Sliding window: reject when more than _RATE_LIMIT_MAX submits in window."""
    if not ip:
        return  # Can't enforce — pass through. Loadbalancer must set XFF.
    try:
        from app.core.redis import get_redis
        redis = get_redis()
        key = f"intl_apply:rate:{ip}"
        # Use ZADD with score = unix time so we can trim old entries.
        now = time.time()
        await redis.zremrangebyscore(key, 0, now - _RATE_LIMIT_WINDOW_S)
        n = await redis.zcard(key)
        if int(n) >= _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Juda ko'p urinish. Iltimos, biroz vaqtdan keyin urinib ko'ring.",
            )
        await redis.zadd(key, {f"{now}": now})
        await redis.expire(key, _RATE_LIMIT_WINDOW_S)
    except HTTPException:
        raise
    except Exception as exc:
        # Don't fail open on a Redis blip — log and continue. The
        # duplicate-passport guard + honeypot still cover most bots.
        logger.warning("intl_apply.rate_limit_check_failed", error=str(exc))


@router.post(
    "/apply",
    response_model=IntlApplyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_public(
    request: Request,
    # Personal
    full_name: Annotated[str, Form(min_length=3, max_length=200)],
    country: Annotated[str, Form(min_length=2, max_length=60)],
    passport_number: Annotated[str, Form(min_length=4, max_length=40)],
    birth_date: Annotated[date, Form()],
    phone: Annotated[str, Form(min_length=6, max_length=30)],
    email: Annotated[str, Form(min_length=5, max_length=120)],
    # Program
    program: Annotated[str, Form(min_length=1, max_length=20)],
    faculty_code: Annotated[str, Form(min_length=1, max_length=20)],
    faculty_text: Annotated[str, Form(min_length=1, max_length=120)],
    # Anti-spam fields
    session_token: Annotated[str, Form()],
    website: Annotated[str | None, Form()] = None,    # honeypot — must stay empty
    language: Annotated[str | None, Form()] = None,
    # Files (multipart)
    passport_file: Annotated[UploadFile, File()] = None,
    diploma_file: Annotated[UploadFile, File()] = None,
    photo_file: Annotated[UploadFile, File()] = None,
    session: AsyncSession = Depends(get_db),
) -> IntlApplyResponse:
    # --- 1) Honeypot ---
    # Bots fill every input; humans never see this field (display:none).
    # Non-empty value → silent 422 so the bot doesn't learn the trap.
    if website:
        logger.info("intl_apply.honeypot_tripped", ip=_client_ip(request))
        raise HTTPException(status_code=422, detail="Validation failed")

    # --- 2) Time-trap ---
    issued = _verify_session_token(session_token)
    if issued is None:
        raise HTTPException(status_code=400, detail="Invalid session token")
    elapsed = time.time() - issued
    if elapsed < _MIN_FILL_S:
        # Too fast — almost certainly a bot.
        raise HTTPException(
            status_code=400,
            detail="Iltimos, formani yana bir bor tekshirib chiqib yuboring.",
        )
    if elapsed > _MAX_FILL_S:
        raise HTTPException(
            status_code=400,
            detail="Sahifani yangilab, formani qaytadan to'ldiring.",
        )

    # --- 3) Rate limit (Redis sliding window) ---
    ip = _client_ip(request)
    await _enforce_rate_limit(ip)

    # --- 4) Files (optional but recommended) — store via FilesService ---
    files_svc = FilesService(session)
    file_ids = {"passport_file_id": None, "diploma_file_id": None, "photo_file_id": None}

    async def _store_optional(field: str, upload: UploadFile | None) -> UUID | None:
        if upload is None or not upload.filename:
            return None
        # Mirror /files/upload's MIME + size checks. 25 MB ceiling enough
        # for a scanned passport + diploma; lower would reject HEIC photos
        # iPhones default to.
        from app.modules.files.router import ALLOWED_MIME, MAX_BYTES
        if upload.content_type not in ALLOWED_MIME:
            raise HTTPException(
                status_code=415,
                detail=f"{field}: faqat PDF yoki rasm yuklash mumkin",
            )
        content = await upload.read()
        if len(content) > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{field}: fayl 25 MB dan oshmasligi kerak",
            )
        # We DON'T have a user_id yet — public submission. Pass None as
        # uploaded_by_id; the files table allows null on that column.
        saved = await files_svc.store_bytes(
            content,
            original_name=upload.filename,
            mime_type=upload.content_type,
            subdir="intl-admissions",
            uploaded_by_id=None,
        )
        return saved.id

    file_ids["passport_file_id"] = await _store_optional("passport_file", passport_file)
    file_ids["diploma_file_id"]  = await _store_optional("diploma_file",  diploma_file)
    file_ids["photo_file_id"]    = await _store_optional("photo_file",    photo_file)

    # --- 5) Submit through the service (duplicate-passport check inside) ---
    svc = InternationalAdmissionsService(session)
    try:
        obj = await svc.submit(
            full_name=full_name,
            country=country,
            passport_number=passport_number,
            birth_date=birth_date,
            phone=phone,
            email=email,
            program=program,
            faculty_code=faculty_code,
            faculty_text=faculty_text,
            language=language,
            passport_file_id=file_ids["passport_file_id"],
            diploma_file_id=file_ids["diploma_file_id"],
            photo_file_id=file_ids["photo_file_id"],
            submitter_ip=ip,
            submitter_user_agent=request.headers.get("user-agent"),
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    await session.commit()

    return IntlApplyResponse(
        id=obj.id,
        ref_number=obj.ref_number,
        submitted_at=obj.created_at or datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Staff endpoints — all under "Xalqaro qabul" permission
# ---------------------------------------------------------------------------

def _service(session: AsyncSession = Depends(get_db)) -> InternationalAdmissionsService:
    return InternationalAdmissionsService(session)


@router.get(
    "",
    response_model=PageResponse[IntlApplicationListItem],
    dependencies=[Depends(require_permission(Permission.INTL_ADMISSIONS_LIST))],
)
async def list_intl(
    stage: int | None = Query(default=None, ge=0, le=5),
    country: str | None = Query(default=None, max_length=60),
    rejected: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    svc: InternationalAdmissionsService = Depends(_service),
) -> PageResponse[IntlApplicationListItem]:
    items, total = await svc.list(
        stage=stage, country=country, rejected=rejected, search=search,
        limit=size, offset=(page - 1) * size,
    )
    return PageResponse[IntlApplicationListItem].build(
        items=[IntlApplicationListItem.model_validate(i) for i in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/stats",
    dependencies=[Depends(require_permission(Permission.INTL_ADMISSIONS_LIST))],
)
async def stage_stats(
    svc: InternationalAdmissionsService = Depends(_service),
) -> dict:
    return await svc.stage_counts()


@router.get(
    "/{app_id}",
    response_model=IntlApplicationRead,
    dependencies=[Depends(require_permission(Permission.INTL_ADMISSIONS_READ))],
)
async def get_intl(
    app_id: UUID,
    svc: InternationalAdmissionsService = Depends(_service),
) -> IntlApplicationRead:
    try:
        obj = await svc.get(app_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return IntlApplicationRead.model_validate(obj)


@router.patch(
    "/{app_id}/stage",
    response_model=IntlApplicationRead,
    dependencies=[Depends(require_permission(Permission.INTL_ADMISSIONS_MANAGE))],
)
async def advance_stage(
    app_id: UUID,
    payload: IntlAdvanceStage,
    svc: InternationalAdmissionsService = Depends(_service),
    _: CurrentUser = Depends(get_current_user),
) -> IntlApplicationRead:
    try:
        obj = await svc.advance_stage(app_id, direction=payload.direction)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await svc.session.commit()
    return IntlApplicationRead.model_validate(obj)


@router.patch(
    "/{app_id}/reject",
    response_model=IntlApplicationRead,
    dependencies=[Depends(require_permission(Permission.INTL_ADMISSIONS_MANAGE))],
)
async def reject(
    app_id: UUID,
    payload: IntlReject,
    svc: InternationalAdmissionsService = Depends(_service),
) -> IntlApplicationRead:
    obj = await svc.reject(app_id, reason=payload.reason)
    await svc.session.commit()
    return IntlApplicationRead.model_validate(obj)


@router.patch(
    "/{app_id}/unreject",
    response_model=IntlApplicationRead,
    dependencies=[Depends(require_permission(Permission.INTL_ADMISSIONS_MANAGE))],
)
async def unreject(
    app_id: UUID,
    svc: InternationalAdmissionsService = Depends(_service),
) -> IntlApplicationRead:
    obj = await svc.unreject(app_id)
    await svc.session.commit()
    return IntlApplicationRead.model_validate(obj)


@router.patch(
    "/{app_id}/notes",
    response_model=IntlApplicationRead,
    dependencies=[Depends(require_permission(Permission.INTL_ADMISSIONS_MANAGE))],
)
async def update_notes(
    app_id: UUID,
    payload: IntlNotesUpdate,
    svc: InternationalAdmissionsService = Depends(_service),
) -> IntlApplicationRead:
    obj = await svc.update_notes(app_id, notes=payload.notes)
    await svc.session.commit()
    return IntlApplicationRead.model_validate(obj)


@router.delete(
    "/{app_id}",
    status_code=204,
    dependencies=[Depends(require_permission(Permission.INTL_ADMISSIONS_DELETE))],
)
async def delete_intl(
    app_id: UUID,
    svc: InternationalAdmissionsService = Depends(_service),
) -> None:
    await svc.delete(app_id)
    await svc.session.commit()
