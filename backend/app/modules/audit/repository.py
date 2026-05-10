from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from app.core.repository import BaseRepository
from app.modules.audit.models import AuditLog
from app.modules.users.models import User


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def list_filtered(
        self,
        *,
        user_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List audit log rows joined with the actor's user info."""
        stmt = (
            select(
                AuditLog,
                User.full_name.label("user_full_name"),
                User.phone.label("user_phone"),
                User.role.label("user_role"),
            )
            .outerjoin(User, AuditLog.user_id == User.id)
        )
        count_stmt = select(func.count(AuditLog.id))

        for col, val in (
            (AuditLog.user_id, user_id),
            (AuditLog.entity_type, entity_type),
            (AuditLog.entity_id, entity_id),
            (AuditLog.action, action),
        ):
            if val is not None:
                stmt = stmt.where(col == val)
                count_stmt = count_stmt.where(col == val)

        if date_from is not None:
            stmt = stmt.where(AuditLog.created_at >= date_from)
            count_stmt = count_stmt.where(AuditLog.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(AuditLog.created_at <= date_to)
            count_stmt = count_stmt.where(AuditLog.created_at <= date_to)

        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        rows = (await self.session.execute(stmt)).all()

        items: list[dict] = []
        for log, name, phone, role in rows:
            d = _audit_to_dict(log)
            d["user_full_name"] = name
            d["user_phone"] = phone
            d["user_role"] = role.value if role else None
            items.append(d)

        total = await self.session.scalar(count_stmt) or 0
        return items, total

    async def get_with_user(self, log_id: UUID) -> dict | None:
        stmt = (
            select(
                AuditLog,
                User.full_name.label("user_full_name"),
                User.phone.label("user_phone"),
                User.role.label("user_role"),
            )
            .outerjoin(User, AuditLog.user_id == User.id)
            .where(AuditLog.id == log_id)
        )
        row = (await self.session.execute(stmt)).first()
        if not row:
            return None
        log, name, phone, role = row
        d = _audit_to_dict(log)
        d["user_full_name"] = name
        d["user_phone"] = phone
        d["user_role"] = role.value if role else None
        return d


def _audit_to_dict(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "changes": log.changes,
        "ip_address": str(log.ip_address) if log.ip_address else None,
        "user_agent": log.user_agent,
        "created_at": log.created_at,
    }
