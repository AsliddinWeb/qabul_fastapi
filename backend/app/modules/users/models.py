from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.enums import UserRole, pg_enum


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(CITEXT, unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    is_phone_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Marker for users who can see/filter the consulting_agency field on
    # applications. Set by the root superadmin via /admin/users.
    is_consulting: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    # Lead intake toggle — only meaningful for OPERATOR users. The lead
    # round-robin filters on this so an operator who's on leave / training
    # / temporarily reassigned can be excluded from new lead distribution
    # without disabling the account. Default TRUE so existing operators
    # keep receiving leads after the migration.
    accepts_leads: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    # Single root user — only this user can manage consulting agencies.
    # Auto-assigned to the first-ever superadmin by migration; never exposed
    # in the regular user CRUD UI.
    is_root_superadmin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Per-user revocation list — string permission codes (e.g. "contracts.sign")
    # that the user's role would normally grant but have been switched off by an
    # admin. require_permission consults this in addition to the role matrix.
    permissions_revoked: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    # Public referral code (6-8 chars, uppercased) — printed on the user's
    # shareable invite link. Backfilled by migration 05_referrals.sql; new
    # users get one assigned by the user service on creation.
    referral_code: Mapped[str | None] = mapped_column(String(8), unique=True, nullable=True, index=True)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
