from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

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
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Payment], int]:
        stmt = select(Payment)
        count_stmt = select(func.count(Payment.id))
        if status is not None:
            stmt = stmt.where(Payment.status == status)
            count_stmt = count_stmt.where(Payment.status == status)
        if contract_id is not None:
            stmt = stmt.where(Payment.contract_id == contract_id)
            count_stmt = count_stmt.where(Payment.contract_id == contract_id)
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
