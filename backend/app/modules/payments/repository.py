from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select

from app.core.repository import BaseRepository
from app.db.enums import PaymentStatus
from app.modules.payments.models import Payment


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    async def list_for_contract(self, contract_id: UUID) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.contract_id == contract_id)
            .order_by(Payment.created_at.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def list_filtered(
        self,
        *,
        status: PaymentStatus | None = None,
        contract_id: UUID | None = None,
        payment_method_id: UUID | None = None,
        registered_by_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Payment], int]:
        stmt = select(Payment)
        count_stmt = select(func.count(Payment.id))

        clauses = []
        if status is not None:
            clauses.append(Payment.status == status)
        if contract_id is not None:
            clauses.append(Payment.contract_id == contract_id)
        if payment_method_id is not None:
            clauses.append(Payment.payment_method_id == payment_method_id)
        if registered_by_id is not None:
            clauses.append(Payment.registered_by_id == registered_by_id)
        # Date range matches paid_at when present, else created_at — so a
        # period filter still includes pending/failed rows that have no
        # paid_at yet.
        ts = func.coalesce(Payment.paid_at, Payment.created_at)
        if date_from is not None:
            clauses.append(ts >= date_from)
        if date_to is not None:
            clauses.append(ts <= date_to)

        for c in clauses:
            stmt = stmt.where(c)
            count_stmt = count_stmt.where(c)

        stmt = stmt.order_by(Payment.created_at.desc()).limit(limit).offset(offset)
        rows = list((await self.session.scalars(stmt)).all())
        total = await self.session.scalar(count_stmt) or 0
        return rows, total

    async def confirmed_total_for_contract(self, contract_id: UUID):
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.contract_id == contract_id,
            Payment.status == PaymentStatus.CONFIRMED,
        )
        return await self.session.scalar(stmt) or 0
