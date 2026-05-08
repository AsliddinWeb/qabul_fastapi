from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema
from app.db.enums import PaymentStatus


class PaymentBase(AppSchema):
    contract_id: UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="UZS", max_length=3)
    payment_method_id: UUID
    reference: str | None = Field(default=None, max_length=100)
    receipt_file_id: UUID | None = None
    notes: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentConfirm(AppSchema):
    paid_at: datetime | None = None
    reference: str | None = Field(default=None, max_length=100)


class PaymentRead(IdSchema, TimestampedSchema):
    payment_number: str
    contract_id: UUID
    amount: Decimal
    currency: str
    payment_method_id: UUID
    status: PaymentStatus
    paid_at: datetime | None = None
    reference: str | None = None
    receipt_file_id: UUID | None = None
    registered_by_id: UUID | None = None
    notes: str | None = None
