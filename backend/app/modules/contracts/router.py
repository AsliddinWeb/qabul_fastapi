from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.core.schemas import PageResponse
from app.db.enums import ContractStatus, ContractType
from app.integrations.crm.events import enqueue_contract_signed_event
from app.modules.audit.service import AuditService
from app.modules.contracts.schemas import (
    ContractCreate,
    ContractDetailed,
    ContractListItem,
    ContractPartyRead,
    ContractRead,
    ContractSettingsRead,
    ContractSettingsUpdate,
    ContractSign,
    ContractTemplateCreate,
    ContractTemplateRead,
    ContractTemplateUpdate,
)
from app.modules.contracts.service import ContractsService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> ContractsService:
    return ContractsService(session)


# ---------- Templates ----------
@router.get(
    "/templates",
    response_model=list[ContractTemplateRead],
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_READ))],
)
async def list_templates(
    active_only: bool = False,
    svc: ContractsService = Depends(_service),
) -> list[ContractTemplateRead]:
    rows = await svc.list_templates(active_only=active_only)
    return [ContractTemplateRead.model_validate(r) for r in rows]


@router.get(
    "/templates/active",
    response_model=ContractTemplateRead | None,
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_READ))],
)
async def get_active_template(svc: ContractsService = Depends(_service)) -> ContractTemplateRead | None:
    obj = await svc.templates.get_active()
    return ContractTemplateRead.model_validate(obj) if obj else None


@router.get(
    "/templates/{template_id}",
    response_model=ContractTemplateRead,
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_READ))],
)
async def get_template(
    template_id: UUID, svc: ContractsService = Depends(_service)
) -> ContractTemplateRead:
    obj = await svc.get_template(template_id)
    return ContractTemplateRead.model_validate(obj)


@router.post(
    "/templates",
    response_model=ContractTemplateRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_WRITE))],
)
async def create_template(
    payload: ContractTemplateCreate,
    svc: ContractsService = Depends(_service),
) -> ContractTemplateRead:
    obj = await svc.create_template(payload)
    await svc.session.commit()
    return ContractTemplateRead.model_validate(obj)


@router.patch(
    "/templates/{template_id}",
    response_model=ContractTemplateRead,
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_WRITE))],
)
async def update_template(
    template_id: UUID,
    payload: ContractTemplateUpdate,
    svc: ContractsService = Depends(_service),
) -> ContractTemplateRead:
    obj = await svc.update_template(template_id, payload)
    await svc.session.commit()
    return ContractTemplateRead.model_validate(obj)


@router.post(
    "/templates/{template_id}/activate",
    response_model=ContractTemplateRead,
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_WRITE))],
    summary="Mark this template as active (deactivates all others)",
)
async def activate_template(
    template_id: UUID, svc: ContractsService = Depends(_service)
) -> ContractTemplateRead:
    obj = await svc.activate_template(template_id)
    await svc.session.commit()
    return ContractTemplateRead.model_validate(obj)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_WRITE))],
)
async def delete_template(
    template_id: UUID, svc: ContractsService = Depends(_service)
) -> Response:
    await svc.delete_template(template_id)
    await svc.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Settings (singleton) ----------
@router.get(
    "/settings",
    response_model=ContractSettingsRead,
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_READ))],
)
async def get_contract_settings(svc: ContractsService = Depends(_service)) -> ContractSettingsRead:
    obj = await svc.get_settings()
    await svc.session.commit()  # may have created singleton
    return ContractSettingsRead.model_validate(obj)


@router.patch(
    "/settings",
    response_model=ContractSettingsRead,
    dependencies=[Depends(require_permission(Permission.CONTRACT_TEMPLATES_WRITE))],
)
async def update_contract_settings(
    payload: ContractSettingsUpdate,
    svc: ContractsService = Depends(_service),
) -> ContractSettingsRead:
    obj = await svc.update_settings(payload)
    await svc.session.commit()
    return ContractSettingsRead.model_validate(obj)


# ---------- Applicant self-service ----------
@router.get(
    "/me",
    response_model=list[ContractDetailed],
)
async def my_contracts(
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    svc: ContractsService = Depends(_service),
) -> list[ContractDetailed]:
    """Applicant's own contracts (linked via application → applicant → user)."""
    from sqlalchemy import select
    from app.modules.applicants.models import Applicant
    from app.modules.applications.models import Application
    from app.modules.contracts.models import Contract

    stmt = (
        select(Contract)
        .join(Application, Application.id == Contract.application_id)
        .join(Applicant, Applicant.id == Application.applicant_id)
        .where(Applicant.user_id == UUID(current.user_id))
        .order_by(Contract.created_at.desc())
    )
    contracts = list((await session.scalars(stmt)).all())
    out: list[ContractDetailed] = []
    for c in contracts:
        parties = await svc.get_parties(c.id)
        d = ContractDetailed.model_validate(c)
        d.parties = [ContractPartyRead.model_validate(p) for p in parties]
        out.append(d)
    return out


# ---------- Contracts (staff) ----------
@router.get(
    "",
    response_model=PageResponse[ContractRead],
    dependencies=[Depends(require_permission(Permission.CONTRACTS_READ))],
)
async def list_contracts(
    status_filter: ContractStatus | None = Query(default=None, alias="status"),
    type: ContractType | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    svc: ContractsService = Depends(_service),
) -> PageResponse[ContractRead]:
    items, total = await svc.list(
        status=status_filter, type=type, search=search,
        limit=size, offset=(page - 1) * size,
    )
    return PageResponse[ContractRead].build(
        items=[ContractRead.model_validate(c) for c in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/list-detailed",
    response_model=PageResponse[ContractListItem],
    dependencies=[Depends(require_permission(Permission.CONTRACTS_READ))],
)
async def list_contracts_detailed(
    status_filter: ContractStatus | None = Query(default=None, alias="status"),
    type: ContractType | None = Query(default=None),
    payment_status: Literal["paid", "partial", "unpaid"] | None = Query(default=None),
    branch_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    svc: ContractsService = Depends(_service),
) -> PageResponse[ContractListItem]:
    """Accountant-facing list: contracts joined with applicant + branch + balance.

    Adds `payment_status` (paid/partial/unpaid), `branch_id`, and a search that
    matches contract_number OR any applicant name field.
    """
    items, total = await svc.list_detailed(
        status=status_filter, type=type, payment_status=payment_status,
        branch_id=branch_id, search=search,
        limit=size, offset=(page - 1) * size,
    )
    return PageResponse[ContractListItem].build(
        items=[ContractListItem.model_validate(c) for c in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/export.csv",
    dependencies=[Depends(require_permission(Permission.CONTRACTS_READ))],
)
async def export_contracts_csv(
    status_filter: ContractStatus | None = Query(default=None, alias="status"),
    type: ContractType | None = Query(default=None),
    payment_status: Literal["paid", "partial", "unpaid"] | None = Query(default=None),
    branch_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    svc: ContractsService = Depends(_service),
) -> Response:
    """Export filtered contracts to CSV (Accountant view)."""
    items, _ = await svc.list_detailed(
        status=status_filter, type=type, payment_status=payment_status,
        branch_id=branch_id, search=search,
        limit=10_000, offset=0,
    )
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM for Excel
    w = csv.writer(buf)
    w.writerow([
        "Shartnoma raqami", "F.I.Sh.", "Filial", "Yo'nalish", "Turi", "Holati",
        "Jami summa", "To'langan", "Qoldiq", "Valyuta", "Imzolangan", "Yaratilgan",
    ])
    for c in items:
        st = c.get("status")
        ct = c.get("type")
        signed = c.get("signed_at")
        created = c.get("created_at")
        w.writerow([
            c.get("contract_number") or "",
            c.get("applicant_full_name") or "",
            c.get("branch_name") or "",
            c.get("program_name") or "",
            (ct.value if hasattr(ct, "value") else (ct or "")),
            (st.value if hasattr(st, "value") else (st or "")),
            str(c.get("total_amount") or 0),
            str(c.get("paid_amount") or 0),
            str(c.get("balance") or 0),
            c.get("currency") or "",
            signed.strftime("%Y-%m-%d") if signed else "",
            created.strftime("%Y-%m-%d %H:%M") if created else "",
        ])
    fn = f"contracts-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.post(
    "",
    response_model=ContractDetailed,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.CONTRACTS_CREATE))],
)
async def create_contract(
    payload: ContractCreate,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: ContractsService = Depends(_service),
) -> ContractDetailed:
    base_url = str(request.base_url).rstrip("/")
    obj = await svc.create_contract(
        payload, actor_id=UUID(current.user_id), base_url=base_url,
    )
    parties = await svc.get_parties(obj.id)

    await AuditService(svc.session).log(
        "contract.create",
        user_id=UUID(current.user_id),
        entity_type="contracts",
        entity_id=obj.id,
        changes={
            "application_id": str(obj.application_id),
            "type": obj.type.value,
            "total_amount": str(obj.total_amount),
        },
        request=request,
    )
    await svc.session.commit()

    detail = ContractDetailed.model_validate(obj)
    detail.parties = [ContractPartyRead.model_validate(p) for p in parties]
    return detail


@router.get(
    "/{contract_id}",
    response_model=ContractDetailed,
    dependencies=[Depends(require_permission(Permission.CONTRACTS_READ))],
)
async def get_contract(
    contract_id: UUID,
    svc: ContractsService = Depends(_service),
) -> ContractDetailed:
    obj = await svc.get(contract_id)
    parties = await svc.get_parties(contract_id)
    detail = ContractDetailed.model_validate(obj)
    detail.parties = [ContractPartyRead.model_validate(p) for p in parties]
    return detail


@router.post(
    "/{contract_id}/sign",
    response_model=ContractRead,
    dependencies=[Depends(require_permission(Permission.CONTRACTS_SIGN))],
)
async def sign_contract(
    contract_id: UUID,
    payload: ContractSign,
    request: Request,
    background: BackgroundTasks,
    current: CurrentUser = Depends(get_current_user),
    svc: ContractsService = Depends(_service),
) -> ContractRead:
    obj = await svc.sign(contract_id, actor_id=UUID(current.user_id))
    application = await svc.applications.get(obj.application_id)

    await AuditService(svc.session).log(
        "contract.sign",
        user_id=UUID(current.user_id),
        entity_type="contracts",
        entity_id=obj.id,
        changes={"notes": payload.notes},
        request=request,
    )
    await svc.session.commit()

    if application:
        enqueue_contract_signed_event(
            background,
            applicant_id=application.applicant_id,
            contract_number=obj.contract_number,
            contract_type=obj.type.value,
            total_amount=float(obj.total_amount),
            currency=obj.currency,
            signed_at=obj.signed_at or obj.updated_at,
        )

    return ContractRead.model_validate(obj)


@router.post(
    "/{contract_id}/cancel",
    response_model=ContractRead,
    dependencies=[Depends(require_permission(Permission.CONTRACTS_SIGN))],
)
async def cancel_contract(
    contract_id: UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: ContractsService = Depends(_service),
) -> ContractRead:
    obj = await svc.cancel(contract_id, actor_id=UUID(current.user_id))
    await AuditService(svc.session).log(
        "contract.cancel",
        user_id=UUID(current.user_id),
        entity_type="contracts",
        entity_id=obj.id,
        request=request,
    )
    await svc.session.commit()
    return ContractRead.model_validate(obj)


def _pdf_disposition(filename: str) -> str:
    """RFC 5987 Content-Disposition that survives non-ASCII filenames."""
    from urllib.parse import quote
    ascii_safe = filename.encode("ascii", errors="replace").decode("ascii").replace('"', "_")
    encoded = quote(filename, safe="")
    return f"inline; filename=\"{ascii_safe}\"; filename*=UTF-8''{encoded}"


@router.get(
    "/me/{contract_id}/pdf",
)
async def my_contract_pdf(
    contract_id: UUID,
    request: Request,
    token: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Stream PDF of an applicant's own contract.

    Auth: Authorization header OR `?token=<jwt>` (so the URL works inside
    a plain <iframe> / new tab). Ownership is enforced by walking
    contract -> application -> applicant -> user.
    """
    from sqlalchemy import select as _select
    from app.modules.applicants.models import Applicant
    from app.modules.applications.models import Application
    from app.modules.contracts.models import Contract
    from app.core.security import decode_token
    from app.core.exceptions import UnauthorizedError, ForbiddenError

    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    jwt_str: str | None = None
    if auth_header and auth_header.lower().startswith("bearer "):
        jwt_str = auth_header.split(" ", 1)[1].strip()
    elif token:
        jwt_str = token
    if not jwt_str:
        raise UnauthorizedError("Missing authorization (header or ?token=)")
    try:
        payload = decode_token(jwt_str)
    except ValueError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Wrong token type")
    user_id = UUID(payload["sub"])

    owns = await session.scalar(
        _select(Contract.id)
        .join(Application, Application.id == Contract.application_id)
        .join(Applicant, Applicant.id == Application.applicant_id)
        .where(Contract.id == contract_id, Applicant.user_id == user_id)
    )
    if not owns:
        raise ForbiddenError("Bu shartnoma sizniki emas")

    svc = ContractsService(session)
    pdf_bytes, filename = await svc.get_pdf_bytes(contract_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _pdf_disposition(filename),
            "Cache-Control": "private, no-cache",
        },
    )


@router.get(
    "/{contract_id}/pdf",
    dependencies=[Depends(require_permission(Permission.CONTRACTS_READ))],
)
async def download_pdf(
    contract_id: UUID,
    svc: ContractsService = Depends(_service),
) -> Response:
    pdf_bytes, filename = await svc.get_pdf_bytes(contract_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _pdf_disposition(filename),
            "Cache-Control": "private, no-cache",
        },
    )


@router.get("/public/{contract_id}/pdf")
async def public_download_pdf(
    contract_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Public PDF endpoint — used by QR-code scanners. No auth required."""
    svc = ContractsService(session)
    pdf_bytes, filename = await svc.get_pdf_bytes(contract_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _pdf_disposition(filename),
            "Cache-Control": "public, max-age=3600",
        },
    )
