from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.db.enums import PaymentStatus
from app.modules.contracts.repository import ContractRepository
from app.modules.payments.models import Payment
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schemas import PaymentConfirm, PaymentCreate


def _generate_payment_number() -> str:
    # Phase 8 will replace with sequence-driven format (e.g. P-2025-000001).
    return f"P-{uuid4().hex[:10].upper()}"


class PaymentsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PaymentRepository(session)
        self.contracts = ContractRepository(session)

    async def list_for_contract(self, contract_id: UUID) -> list[Payment]:
        contract = await self.contracts.get(contract_id)
        if not contract:
            raise NotFoundError("Contract not found")
        return await self.repo.list_for_contract(contract_id)

    async def list(self, **filters) -> tuple[list[Payment], int]:
        return await self.repo.list_filtered(**filters)

    async def get(self, payment_id: UUID) -> Payment:
        obj = await self.repo.get(payment_id)
        if not obj:
            raise NotFoundError("Payment not found")
        return obj

    async def create(self, payload: PaymentCreate, *, registered_by_id: UUID | None = None) -> Payment:
        contract = await self.contracts.get(payload.contract_id)
        if not contract:
            raise NotFoundError("Contract not found")

        return await self.repo.create(
            payment_number=_generate_payment_number(),
            registered_by_id=registered_by_id,
            status=PaymentStatus.PENDING,
            **payload.model_dump(),
        )

    async def confirm(self, payment_id: UUID, payload: PaymentConfirm) -> Payment:
        obj = await self.get(payment_id)
        if obj.status == PaymentStatus.CONFIRMED:
            raise ValidationError("Payment already confirmed")
        if obj.status == PaymentStatus.REFUNDED:
            raise ValidationError("Refunded payments cannot be confirmed")

        updates = {
            "status": PaymentStatus.CONFIRMED,
            "paid_at": payload.paid_at or datetime.now(timezone.utc),
        }
        if payload.reference:
            updates["reference"] = payload.reference

        obj = await self.repo.update(obj, **updates)
        await self._recompute_contract_paid(obj.contract_id)
        return obj

    async def fail(self, payment_id: UUID, reason: str | None = None) -> Payment:
        obj = await self.get(payment_id)
        if obj.status == PaymentStatus.CONFIRMED:
            raise ValidationError("Confirmed payment cannot be failed (use refund)")
        notes = (obj.notes + "\n" if obj.notes else "") + (reason or "failed")
        return await self.repo.update(obj, status=PaymentStatus.FAILED, notes=notes)

    async def refund(self, payment_id: UUID, reason: str | None = None) -> Payment:
        obj = await self.get(payment_id)
        if obj.status != PaymentStatus.CONFIRMED:
            raise ValidationError("Only confirmed payments can be refunded")
        notes = (obj.notes + "\n" if obj.notes else "") + (reason or "refunded")
        obj = await self.repo.update(obj, status=PaymentStatus.REFUNDED, notes=notes)
        await self._recompute_contract_paid(obj.contract_id)
        return obj

    async def _recompute_contract_paid(self, contract_id: UUID) -> None:
        contract = await self.contracts.get(contract_id)
        if not contract:
            return
        total: Decimal = await self.repo.confirmed_total_for_contract(contract_id)
        contract.paid_amount = Decimal(total)
        await self.session.flush()
        # Referral qualification: once confirmed payments cross the 25%
        # threshold, the inviter's bonus flips from pending → active.
        # Same hook reverts active → pending if a refund drops the
        # ratio back below the threshold. Best-effort: a failure here
        # must not roll back the payment update.
        try:
            from app.modules.referrals.service import ReferralService
            await ReferralService(self.session).check_qualification(contract_id)
        except Exception as exc:  # pragma: no cover — defensive only
            from app.core.logging import get_logger
            get_logger("payments").error(
                "referrals.qualification_hook_failed",
                contract_id=str(contract_id), error=str(exc),
            )
