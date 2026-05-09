from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.modules.files.service import FileRepository, FilesService

router = APIRouter()

ALLOWED_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
MAX_BYTES = 25 * 1024 * 1024  # 25 MB


class FileUploadOut(BaseModel):
    id: UUID
    original_name: str
    mime_type: str
    size_bytes: int
    url: str


@router.post(
    "/upload",
    response_model=FileUploadOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: UploadFile = File(...),
    subdir: str = Form(default="uploads"),
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FileUploadOut:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported mime type: {file.content_type}",
        )

    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 25 MB)",
        )

    svc = FilesService(session)
    saved = await svc.store_bytes(
        content,
        original_name=file.filename or "upload",
        mime_type=file.content_type,
        subdir=subdir or "uploads",
        uploaded_by_id=UUID(current.user_id),
    )
    await session.commit()

    return FileUploadOut(
        id=saved.id,
        original_name=saved.original_name,
        mime_type=saved.mime_type,
        size_bytes=saved.size_bytes,
        url=svc.public_url(saved),
    )


@router.get(
    "/{file_id}/download",
    response_class=Response,
)
async def download_file(
    file_id: UUID,
    request: Request,
    token: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Stream a stored file's bytes.

    Authenticates EITHER via the Authorization header (normal API calls)
    OR via a `?token=<jwt>` query string (so the same URL can be opened
    in a new tab as a regular link, e.g. from an admin's "view file"
    button). Both paths use the same JWT decode.
    """
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    jwt_str: str | None = None
    if auth_header and auth_header.lower().startswith("bearer "):
        jwt_str = auth_header.split(" ", 1)[1].strip()
    elif token:
        jwt_str = token
    if not jwt_str:
        raise UnauthorizedError("Missing authorization (header or ?token=)")

    try:
        payload = decode_token(jwt_str)
    except ValueError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Wrong token type")

    file = await FileRepository(session).get(file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    svc = FilesService(session)
    path = await svc.absolute_path(file)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")
    data = path.read_bytes()

    # Build a Content-Disposition that survives non-ASCII filenames.
    # HTTP headers are latin-1 only, so any non-Latin char (Uzbek apostrophes,
    # Cyrillic, emoji, ...) crashes the response with UnicodeEncodeError.
    # Use RFC 5987: provide an ASCII fallback + UTF-8 encoded filename*.
    from urllib.parse import quote
    raw_name = file.original_name or "file"
    ascii_safe = raw_name.encode("ascii", errors="replace").decode("ascii").replace('"', "_")
    encoded = quote(raw_name, safe="")
    disposition = f"inline; filename=\"{ascii_safe}\"; filename*=UTF-8''{encoded}"

    return Response(
        content=data,
        media_type=file.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": disposition,
            "Cache-Control": "private, no-cache",
        },
    )


@router.get(
    "/{file_id}/public",
    response_class=Response,
)
async def public_download_file(
    file_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Public file streaming — only allows files referenced by an active Program as image_id.

    Used by the public landing to display program icons.
    """
    from sqlalchemy import select
    from app.modules.programs.models import Program

    # Security: file must be linked to an active Program as its icon
    row = (await session.execute(
        select(Program.id).where(Program.image_id == file_id, Program.is_active == True)  # noqa: E712
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file = await FileRepository(session).get(file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    svc = FilesService(session)
    path = await svc.absolute_path(file)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")
    data = path.read_bytes()
    return Response(
        content=data,
        media_type=file.mime_type or "application/octet-stream",
        headers={
            "Cache-Control": "public, max-age=86400",
        },
    )
