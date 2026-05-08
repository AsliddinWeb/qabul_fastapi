from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CHAR,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.enums import ContractStatus, ContractType, Language, PartyRole, pg_enum


class ContractTemplate(UUIDPKMixin, TimestampMixin, Base):
    """Contract template — holds two-party AND three-party HTML bodies.

    Old Django pattern: one row, two RichText fields, one row may be active globally.
    Single active template enforced via partial unique index in migration.
    """

    __tablename__ = "contract_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    body_two_party: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_three_party: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Legacy fields (kept nullable for older contracts that referenced them)
    type: Mapped[ContractType | None] = mapped_column(
        pg_enum(ContractType, "contract_type"),
        nullable=True,
    )
    language: Mapped[Language | None] = mapped_column(
        pg_enum(Language, "language"),
        nullable=True,
    )
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class ContractSettings(UUIDPKMixin, TimestampMixin, Base):
    """Singleton — only one row should ever exist."""

    __tablename__ = "contract_settings"

    default_contract_type: Mapped[ContractType] = mapped_column(
        pg_enum(ContractType, "contract_type", create_type=False),
        nullable=False,
        default=ContractType.TWO_PARTY,
        server_default=ContractType.TWO_PARTY.value,
    )

    auto_generate_pdf: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    pdf_page_size: Mapped[str] = mapped_column(
        String(10), nullable=False, default="A4", server_default="A4"
    )

    company_name: Mapped[str] = mapped_column(
        String(200), nullable=False,
        default="Xalqaro Innovatsion Universiteti",
        server_default="Xalqaro Innovatsion Universiteti",
    )
    company_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_inn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    director_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    director_title: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Rektor", server_default="Rektor"
    )


class Contract(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "contracts"
    __table_args__ = (
        # Only one active (non-cancelled) contract per application; cancelled ones are kept as history.
        Index(
            "uq_contracts_application_active",
            "application_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
    )

    contract_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    application_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contract_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )

    type: Mapped[ContractType] = mapped_column(
        pg_enum(ContractType, "contract_type", create_type=False),
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, default="UZS", server_default="UZS")

    status: Mapped[ContractStatus] = mapped_column(
        pg_enum(ContractStatus, "contract_status"),
        nullable=False,
        default=ContractStatus.DRAFT,
        server_default=ContractStatus.DRAFT.value,
        index=True,
    )

    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pdf_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class ContractParty(UUIDPKMixin, TimestampMixin, Base):
    """Contract signatories — university + student always; sponsor/parent for 3-party."""

    __tablename__ = "contract_parties"

    contract_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    party_role: Mapped[PartyRole] = mapped_column(
        pg_enum(PartyRole, "party_role"),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pinfl: Mapped[str | None] = mapped_column(String(14), nullable=True)
    passport_series: Mapped[str | None] = mapped_column(String(2), nullable=True)
    passport_number: Mapped[str | None] = mapped_column(String(7), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    relationship: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
