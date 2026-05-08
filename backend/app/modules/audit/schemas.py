from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.schemas import IdSchema


class AuditLogRead(IdSchema):
    user_id: UUID | None = None
    action: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    changes: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    # Embedded actor info from user JOIN
    user_full_name: str | None = None
    user_phone: str | None = None
    user_role: str | None = None
