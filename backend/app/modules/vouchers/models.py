from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Sequence, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin

VOUCHER_ACTIVE = "active"
VOUCHER_CANCELLED = "cancelled"

VOUCHER_NUMBER_SEQ = Sequence("voucher_number_seq", start=1)


class Voucher(UUIDPKMixin, TimestampMixin, Base):
    """Kontrakt to'loviga chegirma vaucheri — issued only on o'qishni
    ko'chirish (perevod) applications, typically when the contract is
    cancelled and re-created.

    Student name / program are SNAPSHOTS taken at issue time, so the PDF
    (rendered on demand) never changes after the fact. At most one active
    voucher per application (partial unique index).
    """

    __tablename__ = "vouchers"
    __table_args__ = (
        Index(
            "uq_vouchers_application_active",
            "application_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    # Human number shown as "№ 0001" — from a DB sequence, so concurrent
    # workers can't collide.
    voucher_number: Mapped[int] = mapped_column(
        Integer, VOUCHER_NUMBER_SEQ, unique=True, nullable=False,
        server_default=VOUCHER_NUMBER_SEQ.next_value(),
    )

    application_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # The contract it was issued together with (cancelling that contract
    # cancels the voucher too).
    contract_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    discount_percent: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="50")
    student_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=VOUCHER_ACTIVE, index=True,
    )

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
