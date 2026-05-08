from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.core.schemas import PageResponse
from app.db.enums import PaymentStatus
from app.modules.audit.service import AuditService
from app.modules.payments.schemas import PaymentConfirm, PaymentCreate, PaymentRead
from app.modules.payments.service import PaymentsService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> PaymentsService:
    return PaymentsService(session)


@router.get(
    "",
    response_model=PageResponse[PaymentRead],
    dependencies=[Depends(require_permission(Permission.PAYMENTS_READ))],
)
async def list_payments(
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    contract_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    svc: PaymentsService = Depends(_service),
) -> PageResponse[PaymentRead]:
    items, total = await svc.list(
        status=status_filter, contract_id=contract_id,
        limit=size, offset=(page - 1) * size,
    )
    return PageResponse[PaymentRead].build(
        items=[PaymentRead.model_validate(p) for p in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/contracts/{contract_id}",
    response_model=list[PaymentRead],
    dependencies=[Depends(require_permission(Permission.PAYMENTS_READ))],
)
async def list_for_contract(
    contract_id: UUID,
    svc: PaymentsService = Depends(_service),
) -> list[PaymentRead]:
    rows = await svc.list_for_contract(contract_id)
    return [PaymentRead.model_validate(r) for r in rows]


@router.get(
    "/me",
    response_model=list[PaymentRead],
)
async def my_payments(
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[PaymentRead]:
    """Applicant's own payments (linked via contract → application → applicant → user)."""
    from sqlalchemy import select
    from app.modules.applicants.models import Applicant
    from app.modules.applications.models import Application
    from app.modules.contracts.models import Contract
    from app.modules.payments.models import Payment

    stmt = (
        select(Payment)
        .join(Contract, Contract.id == Payment.contract_id)
        .join(Application, Application.id == Contract.application_id)
        .join(Applicant, Applicant.id == Application.applicant_id)
        .where(Applicant.user_id == UUID(current.user_id))
        .order_by(Payment.created_at.desc())
    )
    rows = list((await session.scalars(stmt)).all())
    return [PaymentRead.model_validate(p) for p in rows]


@router.post(
    "",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.PAYMENTS_CREATE))],
)
async def create_payment(
    payload: PaymentCreate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: PaymentsService = Depends(_service),
) -> PaymentRead:
    obj = await svc.create(payload, registered_by_id=UUID(current.user_id))
    await AuditService(svc.session).log(
        "payment.create",
        user_id=UUID(current.user_id),
        entity_type="payments",
        entity_id=obj.id,
        changes={"contract_id": str(obj.contract_id), "amount": str(obj.amount)},
        request=request,
    )
    await svc.session.commit()
    return PaymentRead.model_validate(obj)


@router.post(
    "/{payment_id}/confirm",
    response_model=PaymentRead,
    dependencies=[Depends(require_permission(Permission.PAYMENTS_CONFIRM))],
)
async def confirm_payment(
    payment_id: UUID,
    payload: PaymentConfirm,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: PaymentsService = Depends(_service),
) -> PaymentRead:
    obj = await svc.confirm(payment_id, payload)
    await AuditService(svc.session).log(
        "payment.confirm",
        user_id=UUID(current.user_id),
        entity_type="payments",
        entity_id=obj.id,
        changes={"reference": payload.reference},
        request=request,
    )
    await svc.session.commit()
    return PaymentRead.model_validate(obj)


@router.post(
    "/{payment_id}/fail",
    response_model=PaymentRead,
    dependencies=[Depends(require_permission(Permission.PAYMENTS_FAIL))],
)
async def fail_payment(
    payment_id: UUID,
    request: Request,
    reason: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    svc: PaymentsService = Depends(_service),
) -> PaymentRead:
    obj = await svc.fail(payment_id, reason)
    await AuditService(svc.session).log(
        "payment.fail",
        user_id=UUID(current.user_id),
        entity_type="payments",
        entity_id=obj.id,
        changes={"reason": reason},
        request=request,
    )
    await svc.session.commit()
    return PaymentRead.model_validate(obj)


@router.post(
    "/{payment_id}/refund",
    response_model=PaymentRead,
    dependencies=[Depends(require_permission(Permission.PAYMENTS_REFUND))],
)
async def refund_payment(
    payment_id: UUID,
    request: Request,
    reason: str | None = None,
    current: CurrentUser = Depends(get_current_user),
    svc: PaymentsService = Depends(_service),
) -> PaymentRead:
    obj = await svc.refund(payment_id, reason)
    await AuditService(svc.session).log(
        "payment.refund",
        user_id=UUID(current.user_id),
        entity_type="payments",
        entity_id=obj.id,
        changes={"reason": reason},
        request=request,
    )
    await svc.session.commit()
    return PaymentRead.model_validate(obj)
