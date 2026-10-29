from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.core.schemas import AppSchema
from app.modules.audit.service import AuditService
from app.modules.contracts.router import _pdf_disposition
from app.modules.vouchers.models import Voucher
from app.modules.vouchers.service import (
    VoucherService,
    default_valid_until,
    format_number,
    pdf_filename,
    render_voucher_pdf,
)

router = APIRouter()


class VoucherRead(AppSchema):
    id: UUID
    voucher_number: int
    number: str
    application_id: UUID
    contract_id: UUID | None
    discount_percent: int
    student_full_name: str
    program_name: str
    valid_until: date
    status: str
    created_by_id: UUID | None
    created_at: datetime
    cancelled_at: datetime | None
    cancelled_by_id: UUID | None
    cancelled_reason: str | None


class VoucherIssue(AppSchema):
    application_id: UUID
    valid_until: date | None = None


class VoucherCancel(AppSchema):
    reason: str | None = Field(default=None, max_length=1000)


def _read(v: Voucher) -> VoucherRead:
    return VoucherRead(
        id=v.id, voucher_number=v.voucher_number, number=format_number(v.voucher_number),
        application_id=v.application_id, contract_id=v.contract_id,
        discount_percent=v.discount_percent, student_full_name=v.student_full_name,
        program_name=v.program_name, valid_until=v.valid_until, status=v.status,
        created_by_id=v.created_by_id, created_at=v.created_at,
        cancelled_at=v.cancelled_at, cancelled_by_id=v.cancelled_by_id,
        cancelled_reason=v.cancelled_reason,
    )


def _service(session: AsyncSession = Depends(get_db)) -> VoucherService:
    return VoucherService(session)


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


async def _pdf_response(v: Voucher, request: Request, cache: str) -> Response:
    data = await run_in_threadpool(render_voucher_pdf, v, base_url=_base_url(request))
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": _pdf_disposition(pdf_filename(v)), "Cache-Control": cache},
    )


@router.get("/defaults", dependencies=[Depends(require_permission(Permission.CONTRACTS_READ))])
async def voucher_defaults() -> dict:
    return {"valid_until": default_valid_until(), "discount_percent": 50}


@router.get(
    "",
    response_model=list[VoucherRead],
    dependencies=[Depends(require_permission(Permission.CONTRACTS_READ))],
)
async def list_vouchers(
    application_id: UUID = Query(...),
    svc: VoucherService = Depends(_service),
) -> list[VoucherRead]:
    return [_read(v) for v in await svc.list_for_application(application_id)]


@router.post(
    "",
    response_model=VoucherRead,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.CONTRACTS_CREATE))],
)
async def issue_voucher(
    payload: VoucherIssue,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: VoucherService = Depends(_service),
) -> VoucherRead:
    v = await svc.issue_standalone(
        payload.application_id, valid_until=payload.valid_until, actor_id=UUID(current.user_id),
    )
    await AuditService(svc.session).log(
        "voucher.create",
        user_id=UUID(current.user_id), entity_type="vouchers", entity_id=v.id,
        changes={"application_id": str(v.application_id), "number": format_number(v.voucher_number)},
        request=request,
    )
    await svc.session.commit()
    return _read(v)


@router.post(
    "/{voucher_id}/cancel",
    response_model=VoucherRead,
    dependencies=[Depends(require_permission(Permission.CONTRACTS_SIGN))],
)
async def cancel_voucher(
    voucher_id: UUID,
    request: Request,
    payload: VoucherCancel | None = None,
    current: CurrentUser = Depends(get_current_user),
    svc: VoucherService = Depends(_service),
) -> VoucherRead:
    v = await svc.cancel(voucher_id, actor_id=UUID(current.user_id),
                         reason=payload.reason if payload else None)
    await AuditService(svc.session).log(
        "voucher.cancel",
        user_id=UUID(current.user_id), entity_type="vouchers", entity_id=v.id,
        changes={"number": format_number(v.voucher_number), "reason": v.cancelled_reason},
        request=request,
    )
    await svc.session.commit()
    return _read(v)


@router.get(
    "/{voucher_id}/pdf",
    dependencies=[Depends(require_permission(Permission.CONTRACTS_READ))],
)
async def voucher_pdf(
    voucher_id: UUID,
    request: Request,
    svc: VoucherService = Depends(_service),
) -> Response:
    return await _pdf_response(await svc.get(voucher_id), request, "private, no-cache")


@router.get("/public/{voucher_id}/pdf")
async def public_voucher_pdf(
    voucher_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Public PDF — the QR code on the voucher points here. No auth."""
    v = await VoucherService(session).get(voucher_id)
    return await _pdf_response(v, request, "no-cache")
