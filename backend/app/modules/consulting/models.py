from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class ConsultingAgency(UUIDPKMixin, TimestampMixin, Base):
    """Consulting agency / source — used to track which agency funneled
    an applicant in. Visible only to users with is_consulting=True.
    Managed exclusively by the root superadmin."""

    __tablename__ = "consulting_agencies"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
