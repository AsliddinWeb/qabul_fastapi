from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import and_, func, select
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
    payment_method_id: UUID | None = Query(default=None),
    registered_by_id: UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    svc: PaymentsService = Depends(_service),
) -> PageResponse[PaymentRead]:
    items, total = await svc.list(
        status=status_filter, contract_id=contract_id,
        payment_method_id=payment_method_id,
        registered_by_id=registered_by_id,
        date_from=date_from, date_to=date_to,
        limit=size, offset=(page - 1) * size,
    )
    return PageResponse[PaymentRead].build(
        items=[PaymentRead.model_validate(p) for p in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/export.csv",
    dependencies=[Depends(require_permission(Permission.PAYMENTS_READ))],
)
async def export_payments_csv(
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    contract_id: UUID | None = Query(default=None),
    payment_method_id: UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    svc: PaymentsService = Depends(_service),
) -> Response:
    """Export filtered payments to CSV."""
    items, _ = await svc.list(
        status=status_filter, contract_id=contract_id,
        payment_method_id=payment_method_id,
        date_from=date_from, date_to=date_to,
        limit=10_000, offset=0,
    )
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow([
        "To'lov raqami", "Shartnoma ID", "Summa", "Valyuta", "Holati",
        "Reference", "To'langan vaqt", "Yaratilgan", "Izoh",
    ])
    for p in items:
        w.writerow([
            p.payment_number or "",
            str(p.contract_id) if p.contract_id else "",
            str(p.amount) if p.amount is not None else "",
            p.currency or "",
            (p.status.value if p.status else ""),
            p.reference or "",
            p.paid_at.strftime("%Y-%m-%d %H:%M") if p.paid_at else "",
            p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
            (p.notes or "").replace("\n", " ").strip(),
        ])
    fn = f"payments-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
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
    "/dashboard",
    dependencies=[Depends(require_permission(Permission.PAYMENTS_READ))],
)
async def accountant_dashboard(
    session: AsyncSession = Depends(get_db),
) -> dict:
    """KPI snapshot for the accountant's home page.

    Returns:
      - today_count, today_sum: confirmed payments paid today
      - month_count, month_sum: confirmed payments paid this month
      - pending_count, pending_sum: payments awaiting confirmation
      - outstanding_total: SUM(total_amount - paid_amount) over non-cancelled contracts
      - monthly_trend: last 6 months [{month, sum, count}] of confirmed payments
      - top_debtors: 5 contracts with the largest balance
    """
    from app.modules.applicants.models import Applicant
    from app.modules.applications.models import Application
    from app.modules.contracts.models import Contract
    from app.modules.payments.models import Payment
    from app.db.enums import ContractStatus

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    confirmed_filter = Payment.status == PaymentStatus.CONFIRMED

    today_row = (await session.execute(
        select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
        .where(and_(confirmed_filter, Payment.paid_at >= today_start))
    )).one()
    month_row = (await session.execute(
        select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
        .where(and_(confirmed_filter, Payment.paid_at >= month_start))
    )).one()
    pending_row = (await session.execute(
        select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.status == PaymentStatus.PENDING)
    )).one()

    outstanding_total = await session.scalar(
        select(func.coalesce(func.sum(Contract.total_amount - Contract.paid_amount), 0))
        .where(Contract.status != ContractStatus.CANCELLED)
    ) or 0

    # Monthly trend: walk back 6 calendar months and sum confirmed payments.
    trend: list[dict] = []
    for i in range(5, -1, -1):
        # Compute first-of-month i months back, in calendar terms.
        y = month_start.year
        m = month_start.month - i
        while m <= 0:
            m += 12
            y -= 1
        bucket_start = month_start.replace(year=y, month=m)
        # End: first-of-next-month
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        bucket_end = month_start.replace(year=ny, month=nm)

        row = (await session.execute(
            select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
            .where(and_(
                confirmed_filter,
                Payment.paid_at >= bucket_start,
                Payment.paid_at < bucket_end,
            ))
        )).one()
        trend.append({
            "month": bucket_start.strftime("%Y-%m"),
            "count": int(row[0] or 0),
            "sum": str(row[1] or 0),
        })

    # Top 5 debtors with applicant name + contract number.
    debtors_stmt = (
        select(
            Contract.id,
            Contract.contract_number,
            Contract.total_amount,
            Contract.paid_amount,
            Applicant.last_name,
            Applicant.first_name,
            Applicant.other_name,
        )
        .join(Application, Application.id == Contract.application_id)
        .join(Applicant, Applicant.id == Application.applicant_id)
        .where(
            Contract.status != ContractStatus.CANCELLED,
            (Contract.total_amount - Contract.paid_amount) > 0,
        )
        .order_by((Contract.total_amount - Contract.paid_amount).desc())
        .limit(5)
    )
    top_debtors = []
    for row in (await session.execute(debtors_stmt)).all():
        cid, cnum, total, paid, last, first, other = row
        full_name = " ".join(filter(None, [last, first, other])).strip()
        top_debtors.append({
            "contract_id": str(cid),
            "contract_number": cnum,
            "applicant_full_name": full_name,
            "total_amount": str(total),
            "paid_amount": str(paid),
            "balance": str(total - paid),
        })

    return {
        "today_count":      int(today_row[0] or 0),
        "today_sum":        str(today_row[1] or 0),
        "month_count":      int(month_row[0] or 0),
        "month_sum":        str(month_row[1] or 0),
        "pending_count":    int(pending_row[0] or 0),
        "pending_sum":      str(pending_row[1] or 0),
        "outstanding_total": str(outstanding_total),
        "monthly_trend":    trend,
        "top_debtors":      top_debtors,
    }


@router.get(
    "/breakdown",
    dependencies=[Depends(require_permission(Permission.PAYMENTS_READ))],
)
async def payments_breakdown(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Period summary for the accountant's reports view.

    For confirmed payments inside [date_from, date_to] (paid_at):
      - period_count, period_sum: totals for the window
      - by_method: [{ method_id, method_name, count, sum }]
      - by_branch: [{ branch_id, branch_name, count, sum }]
    """
    from app.modules.applicants.models import Applicant  # noqa: F401
    from app.modules.applications.models import Application
    from app.modules.contracts.models import Contract
    from app.modules.dictionaries.models import DictionaryItem
    from app.modules.payments.models import Payment
    from app.modules.programs.models import Branch

    confirmed = Payment.status == PaymentStatus.CONFIRMED
    clauses = [confirmed]
    ts = func.coalesce(Payment.paid_at, Payment.created_at)
    if date_from is not None:
        clauses.append(ts >= date_from)
    if date_to is not None:
        clauses.append(ts <= date_to)

    # Period totals
    total_row = (await session.execute(
        select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
        .where(and_(*clauses))
    )).one()

    # Breakdown by payment method
    by_method_stmt = (
        select(
            DictionaryItem.id,
            DictionaryItem.name_uz,
            func.count(Payment.id),
            func.coalesce(func.sum(Payment.amount), 0),
        )
        .select_from(Payment)
        .join(DictionaryItem, DictionaryItem.id == Payment.payment_method_id)
        .where(and_(*clauses))
        .group_by(DictionaryItem.id, DictionaryItem.name_uz)
        .order_by(func.sum(Payment.amount).desc())
    )
    by_method = [
        {"method_id": str(mid), "method_name": name, "count": int(cnt or 0), "sum": str(s or 0)}
        for mid, name, cnt, s in (await session.execute(by_method_stmt)).all()
    ]

    # Breakdown by branch (via contract -> application -> branch)
    by_branch_stmt = (
        select(
            Branch.id,
            Branch.name,
            func.count(Payment.id),
            func.coalesce(func.sum(Payment.amount), 0),
        )
        .select_from(Payment)
        .join(Contract, Contract.id == Payment.contract_id)
        .join(Application, Application.id == Contract.application_id)
        .join(Branch, Branch.id == Application.branch_id)
        .where(and_(*clauses))
        .group_by(Branch.id, Branch.name)
        .order_by(func.sum(Payment.amount).desc())
    )
    by_branch = [
        {"branch_id": str(bid), "branch_name": name, "count": int(cnt or 0), "sum": str(s or 0)}
        for bid, name, cnt, s in (await session.execute(by_branch_stmt)).all()
    ]

    return {
        "period_count": int(total_row[0] or 0),
        "period_sum":   str(total_row[1] or 0),
        "by_method":    by_method,
        "by_branch":    by_branch,
    }


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
