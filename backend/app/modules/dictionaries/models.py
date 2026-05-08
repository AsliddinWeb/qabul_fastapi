from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class DictionaryType(UUIDPKMixin, TimestampMixin, Base):
    """Defines a kind of dictionary: 'regions', 'districts', 'nationalities', ..."""

    __tablename__ = "dictionary_types"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_hierarchical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class DictionaryItem(UUIDPKMixin, TimestampMixin, Base):
    """Individual dictionary value. `parent_id` enables tree (region → district)."""

    __tablename__ = "dictionary_items"
    __table_args__ = (
        UniqueConstraint("type_id", "code", name="uq_dictionary_items_type_id_code"),
    )

    type_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dictionary_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dictionary_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name_uz: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # NOTE: column is named `extra` in DB to avoid clashing with SQLAlchemy's
    # built-in `metadata` attribute on instances (which returns Base.metadata).
    extra: Mapped[dict[str, Any] | None] = mapped_column("extra", JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
