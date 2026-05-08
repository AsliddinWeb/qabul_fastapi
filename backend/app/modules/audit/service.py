"""Audit logging service.

Services call `AuditService.log(...)` whenever they perform a meaningful
state change (create / update / delete / status transition / sign / pay).

Reads are NOT audited by default — too much noise. Add specific reads
(e.g. exporting a contract PDF) if you need to.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditRepository

logger = get_logger("audit")


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuditRepository(session)

    async def log(
        self,
        action: str,
        *,
        user_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        changes: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        ip = None
        ua = None
        if request is not None:
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent")

        try:
            return await self.repo.create(
                action=action,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
                ip_address=ip,
                user_agent=ua,
            )
        except Exception as exc:
            # Audit MUST NOT break the main transaction.
            logger.error("audit.log_failed", action=action, error=str(exc))
            raise

    # Read API
    async def list(self, **filters) -> tuple[list[dict], int]:
        return await self.repo.list_filtered(**filters)

    async def get(self, log_id: UUID) -> dict | None:
        return await self.repo.get_with_user(log_id)
