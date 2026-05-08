"""File storage service.

Stores arbitrary blobs to the local media volume + creates a `files` row.
Layout: <media_root>/<subdir>/<yyyy>/<mm>/<uuid>.<ext>
URL:    /media/<subdir>/<yyyy>/<mm>/<uuid>.<ext>  (served by Nginx)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.repository import BaseRepository
from app.modules.files.models import File


class FileRepository(BaseRepository[File]):
    model = File


class FilesService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FileRepository(session)

    async def store_bytes(
        self,
        content: bytes,
        *,
        original_name: str,
        mime_type: str,
        subdir: str = "uploads",
        uploaded_by_id: UUID | None = None,
    ) -> File:
        ext = Path(original_name).suffix or ""
        now = datetime.now(timezone.utc)
        rel_dir = Path(subdir) / f"{now.year:04d}" / f"{now.month:02d}"
        rel_path = rel_dir / f"{uuid4().hex}{ext}"

        abs_root = Path(settings.media_root)
        abs_path = abs_root / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(content)

        return await self.repo.create(
            original_name=original_name,
            storage_path=str(rel_path),
            mime_type=mime_type,
            size_bytes=len(content),
            uploaded_by_id=uploaded_by_id,
        )

    async def absolute_path(self, file: File) -> Path:
        return Path(settings.media_root) / file.storage_path

    def public_url(self, file: File) -> str:
        return f"{settings.media_url}/{file.storage_path}"
