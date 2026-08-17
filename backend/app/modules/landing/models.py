from __future__ import annotations

from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class LandingContent(UUIDPKMixin, TimestampMixin, Base):
    """Single-row store for editable marketing home-page content.

    `data` is a free-form JSON blob whose shape is agreed between the admin
    editor and the Nuxt landing (hero, stats, about, qabul, hamkorlik,
    contact). Empty keys fall back to the landing's built-in defaults, so a
    partially-filled row is safe.
    """

    __tablename__ = "landing_content"

    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
