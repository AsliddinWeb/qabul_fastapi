from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Education(UUIDPKMixin, TimestampMixin, Base):
    """Prior education record (school / lyceum / college / bachelor diploma).
    An applicant can have multiple. Exactly one should have is_primary=true.
    """

    __tablename__ = "educations"

    applicant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applicants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    education_level_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dictionary_items.id", ondelete="RESTRICT"),
        nullable=False,
    )

    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    diploma_series: Mapped[str | None] = mapped_column(String(20), nullable=True)
    diploma_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    start_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    end_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)

    gpa: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    diploma_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
