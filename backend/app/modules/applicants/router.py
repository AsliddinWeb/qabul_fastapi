from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission, require_root_superadmin
from app.core.permissions import Permission
from app.core.schemas import PageResponse
from app.integrations.crm.events import enqueue_applicant_lead
from app.integrations.crm.schemas import LeadSource
from app.modules.applicants.schemas import (
    ApplicantCreate,
    ApplicantCreateForOperator,
    ApplicantDetailed,
    ApplicantRead,
    ApplicantUpdate,
    CourseCreate,
    CourseRead,
    CourseUpdate,
    DiplomCreate,
    DiplomRead,
    DiplomUpdate,
    DiplomWithApplicant,
    EducationTypeCreate,
    EducationTypeRead,
    EducationTypeUpdate,
    InstitutionTypeCreate,
    InstitutionTypeRead,
    InstitutionTypeUpdate,
    TransferDiplomCreate,
    TransferDiplomRead,
    TransferDiplomUpdate,
    TransferDiplomWithApplicant,
)
from app.db.enums import ApplicantContactStatus
from app.modules.applicants.service import ApplicantsService
from app.modules.audit.service import AuditService

router = APIRouter()
require_diploms_write = require_permission(Permission.DIPLOMS_WRITE)


def _service(session: AsyncSession = Depends(get_db)) -> ApplicantsService:
    return ApplicantsService(session)


# ---------- Self ----------
@router.get("/me", response_model=ApplicantDetailed | None)
async def my_profile(
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicantsService = Depends(_service),
) -> ApplicantDetailed | None:
    """Return the current user's applicant profile, or null if not yet created.

    Frontend onboarding wizard treats null as "step 1 — fill in personal data".
    Returning 200 + null is friendlier than 404 for that flow (no scary error
    in the network tab on first login).
    """
    obj = await svc.applicants.get_by_user_id(UUID(current.user_id))
    if not obj:
        return None
    diplom = await svc.diploms.get_by_user_id(obj.user_id)
    transfer = await svc.transfer_diploms.get_by_user_id(obj.user_id)
    detail = ApplicantDetailed.model_validate(obj)
    detail.diplom = DiplomRead.model_validate(diplom) if diplom else None
    detail.transfer_diplom = TransferDiplomRead.model_validate(transfer) if transfer else None
    return detail


@router.post(
    "/me",
    response_model=ApplicantRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_profile(
    payload: ApplicantCreate,
    background: BackgroundTasks,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicantsService = Depends(_service),
) -> ApplicantRead:
    obj = await svc.create_for_user(UUID(current.user_id), payload)
    await svc.session.commit()

    enqueue_applicant_lead(
        background,
        applicant_id=obj.id,
        phone=current.phone or "",
        first_name=obj.first_name,
        last_name=obj.last_name,
        middle_name=obj.other_name,
        birth_date=obj.birth_date,
        gender=obj.gender.value if obj.gender else None,
        email=obj.email,
        source=LeadSource.SELF_REGISTRATION,
        created_at=obj.created_at,
    )
    return ApplicantRead.model_validate(obj)


@router.patch("/me", response_model=ApplicantRead)
async def update_my_profile(
    payload: ApplicantUpdate,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicantsService = Depends(_service),
) -> ApplicantRead:
    me = await svc.get_for_user(UUID(current.user_id))
    obj = await svc.update(me.id, payload)
    await svc.session.commit()
    return ApplicantRead.model_validate(obj)


# ---------- Self: diplom / transfer diplom ----------
@router.put("/me/diplom", response_model=DiplomRead)
async def upsert_my_diplom(
    payload: DiplomCreate,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicantsService = Depends(_service),
) -> DiplomRead:
    # Force payload.user_id to the current user
    data = payload.model_copy(update={"user_id": UUID(current.user_id)})
    obj = await svc.upsert_diplom(data)
    await svc.session.commit()
    return DiplomRead.model_validate(obj)


@router.put("/me/transfer-diplom", response_model=TransferDiplomRead)
async def upsert_my_transfer_diplom(
    payload: TransferDiplomCreate,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicantsService = Depends(_service),
) -> TransferDiplomRead:
    data = payload.model_copy(update={"user_id": UUID(current.user_id)})
    obj = await svc.upsert_transfer_diplom(data)
    await svc.session.commit()
    return TransferDiplomRead.model_validate(obj)


# ---------- Staff (operator/admin) ----------
@router.post(
    "",
    response_model=ApplicantRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_CREATE_BY_OPERATOR))],
    summary="Operator manually registers an applicant by phone",
)
async def operator_create_applicant(
    payload: ApplicantCreateForOperator,
    request: Request,
    background: BackgroundTasks,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicantsService = Depends(_service),
) -> ApplicantRead:
    obj, user = await svc.create_by_operator(payload, operator_id=UUID(current.user_id))
    await AuditService(svc.session).log(
        "applicant.create_by_operator",
        user_id=UUID(current.user_id),
        entity_type="applicants",
        entity_id=obj.id,
        changes={"phone": user.phone, "registered_by_id": current.user_id},
        request=request,
    )
    await svc.session.commit()

    enqueue_applicant_lead(
        background,
        applicant_id=obj.id,
        phone=user.phone,
        first_name=obj.first_name,
        last_name=obj.last_name,
        middle_name=obj.other_name,
        birth_date=obj.birth_date,
        gender=obj.gender.value if obj.gender else None,
        email=obj.email,
        source=LeadSource.OPERATOR_MANUAL,
        created_at=obj.created_at,
        metadata={"operator_id": current.user_id},
    )
    return ApplicantRead.model_validate(obj)


@router.get(
    "",
    response_model=PageResponse[ApplicantRead],
    dependencies=[Depends(require_permission(Permission.APPLICANTS_LIST))],
)
async def list_applicants(
    region_id: UUID | None = Query(default=None),
    registered_by_id: UUID | None = Query(default=None),
    contact_status: ApplicantContactStatus | None = Query(default=None),
    has_contract: bool | None = Query(
        default=None,
        description="true → faqat shartnoma olganlar; false → shartnomasizlar",
    ),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    svc: ApplicantsService = Depends(_service),
) -> PageResponse[ApplicantRead]:
    items, total = await svc.list(
        region_id=region_id,
        registered_by_id=registered_by_id,
        contact_status=contact_status,
        has_contract=has_contract,
        search=search,
        limit=size,
        offset=(page - 1) * size,
    )
    return PageResponse[ApplicantRead].build(
        items=[ApplicantRead.model_validate(a) for a in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/export.csv",
    # Security: export restricted to the root superadmin only.
    dependencies=[Depends(require_root_superadmin)],
)
async def export_applicants_csv(
    region_id: UUID | None = Query(default=None),
    registered_by_id: UUID | None = Query(default=None),
    contact_status: ApplicantContactStatus | None = Query(default=None),
    has_contract: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    svc: ApplicantsService = Depends(_service),
) -> Response:
    """Export filtered applicants to CSV (UTF-8 BOM for Excel)."""
    items, _ = await svc.list(
        region_id=region_id,
        registered_by_id=registered_by_id,
        contact_status=contact_status,
        has_contract=has_contract,
        search=search,
        limit=10_000,
        offset=0,
    )
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow([
        "Familiya", "Ism", "Otasining ismi", "Tug'ilgan sana", "Jinsi",
        "Pasport seriyasi", "JSHSHIR", "Millati", "Email", "Qo'shimcha telefon",
        "Telegram", "Manzil", "Yaratilgan",
    ])
    # Repository now returns list[dict] — switched from attribute access
    # to dict.get() so the same field set keeps exporting cleanly.
    for a in items:
        gender = a.get("gender")
        birth = a.get("birth_date")
        created = a.get("created_at")
        w.writerow([
            a.get("last_name") or "",
            a.get("first_name") or "",
            a.get("other_name") or "",
            birth.strftime("%Y-%m-%d") if birth else "",
            (gender.value if gender else ""),
            a.get("passport_series") or "",
            a.get("pinfl") or "",
            a.get("nationality") or "",
            a.get("email") or "",
            a.get("additional_phone") or "",
            a.get("telegram_username") or "",
            (a.get("address") or "").replace("\n", " ").strip(),
            created.strftime("%Y-%m-%d %H:%M") if created else "",
        ])
    fn = f"applicants-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


# NOTE: /{applicant_id} routes are at the end of this file so that literal-path
# routes like /catalog/* and /diploms* are matched first by FastAPI.

# =============================================================================
# Diploms catalog: education types, institution types, courses
# =============================================================================

# ---------- Education types ----------
@router.get("/catalog/education-types", response_model=list[EducationTypeRead])
async def list_education_types(svc: ApplicantsService = Depends(_service)) -> list[EducationTypeRead]:
    rows = await svc.list_education_types()
    return [EducationTypeRead.model_validate(r) for r in rows]


@router.post(
    "/catalog/education-types",
    response_model=EducationTypeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_diploms_write)],
)
async def create_education_type(
    payload: EducationTypeCreate,
    svc: ApplicantsService = Depends(_service),
) -> EducationTypeRead:
    obj = await svc.create_education_type(payload)
    await svc.session.commit()
    return EducationTypeRead.model_validate(obj)


@router.patch(
    "/catalog/education-types/{item_id}",
    response_model=EducationTypeRead,
    dependencies=[Depends(require_diploms_write)],
)
async def update_education_type(
    item_id: UUID,
    payload: EducationTypeUpdate,
    svc: ApplicantsService = Depends(_service),
) -> EducationTypeRead:
    obj = await svc.update_education_type(item_id, payload)
    await svc.session.commit()
    return EducationTypeRead.model_validate(obj)


@router.delete(
    "/catalog/education-types/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_diploms_write)],
)
async def delete_education_type(
    item_id: UUID, svc: ApplicantsService = Depends(_service)
) -> Response:
    await svc.delete_education_type(item_id)
    await svc.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Institution types ----------
@router.get("/catalog/institution-types", response_model=list[InstitutionTypeRead])
async def list_institution_types(svc: ApplicantsService = Depends(_service)) -> list[InstitutionTypeRead]:
    rows = await svc.list_institution_types()
    return [InstitutionTypeRead.model_validate(r) for r in rows]


@router.post(
    "/catalog/institution-types",
    response_model=InstitutionTypeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_diploms_write)],
)
async def create_institution_type(
    payload: InstitutionTypeCreate,
    svc: ApplicantsService = Depends(_service),
) -> InstitutionTypeRead:
    obj = await svc.create_institution_type(payload)
    await svc.session.commit()
    return InstitutionTypeRead.model_validate(obj)


@router.patch(
    "/catalog/institution-types/{item_id}",
    response_model=InstitutionTypeRead,
    dependencies=[Depends(require_diploms_write)],
)
async def update_institution_type(
    item_id: UUID,
    payload: InstitutionTypeUpdate,
    svc: ApplicantsService = Depends(_service),
) -> InstitutionTypeRead:
    obj = await svc.update_institution_type(item_id, payload)
    await svc.session.commit()
    return InstitutionTypeRead.model_validate(obj)


@router.delete(
    "/catalog/institution-types/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_diploms_write)],
)
async def delete_institution_type(
    item_id: UUID, svc: ApplicantsService = Depends(_service)
) -> Response:
    await svc.delete_institution_type(item_id)
    await svc.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Courses ----------
@router.get("/catalog/courses", response_model=list[CourseRead])
async def list_courses(svc: ApplicantsService = Depends(_service)) -> list[CourseRead]:
    rows = await svc.list_courses()
    return [CourseRead.model_validate(r) for r in rows]


@router.post(
    "/catalog/courses",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_diploms_write)],
)
async def create_course(
    payload: CourseCreate, svc: ApplicantsService = Depends(_service)
) -> CourseRead:
    obj = await svc.create_course(payload)
    await svc.session.commit()
    return CourseRead.model_validate(obj)


@router.patch(
    "/catalog/courses/{item_id}",
    response_model=CourseRead,
    dependencies=[Depends(require_diploms_write)],
)
async def update_course(
    item_id: UUID, payload: CourseUpdate, svc: ApplicantsService = Depends(_service)
) -> CourseRead:
    obj = await svc.update_course(item_id, payload)
    await svc.session.commit()
    return CourseRead.model_validate(obj)


@router.delete(
    "/catalog/courses/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_diploms_write)],
)
async def delete_course(
    item_id: UUID, svc: ApplicantsService = Depends(_service)
) -> Response:
    await svc.delete_course(item_id)
    await svc.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Diploms (1-kurs) and Transfer diploms (perevod) — staff endpoints
# =============================================================================

@router.get(
    "/diploms",
    response_model=PageResponse[DiplomWithApplicant],
    dependencies=[Depends(require_permission(Permission.APPLICANTS_READ))],
)
async def list_diploms(
    user_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    is_for_second_specialization: bool | None = Query(
        default=None,
        description="Filter by purpose: false = 1-kurs, true = 2-mutaxassislik",
    ),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    svc: ApplicantsService = Depends(_service),
) -> PageResponse[DiplomWithApplicant]:
    items, total = await svc.list_diploms(
        user_id=user_id, search=search,
        is_for_second_specialization=is_for_second_specialization,
        limit=size, offset=(page - 1) * size,
    )
    return PageResponse[DiplomWithApplicant].build(
        items=[DiplomWithApplicant.model_validate(d) for d in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/diploms/{diplom_id}",
    response_model=DiplomRead,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_READ))],
)
async def get_diplom(diplom_id: UUID, svc: ApplicantsService = Depends(_service)) -> DiplomRead:
    obj = await svc.get_diplom(diplom_id)
    return DiplomRead.model_validate(obj)


@router.post(
    "/diploms",
    response_model=DiplomRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def create_diplom(
    payload: DiplomCreate, svc: ApplicantsService = Depends(_service)
) -> DiplomRead:
    obj = await svc.upsert_diplom(payload)
    await svc.session.commit()
    return DiplomRead.model_validate(obj)


@router.put(
    "/diploms/by-user/{user_id}",
    response_model=DiplomRead,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def staff_upsert_diplom(
    user_id: UUID, payload: DiplomCreate, svc: ApplicantsService = Depends(_service)
) -> DiplomRead:
    data = payload.model_copy(update={"user_id": user_id})
    obj = await svc.upsert_diplom(data)
    await svc.session.commit()
    return DiplomRead.model_validate(obj)


@router.patch(
    "/diploms/{diplom_id}",
    response_model=DiplomRead,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def staff_update_diplom(
    diplom_id: UUID, payload: DiplomUpdate, svc: ApplicantsService = Depends(_service)
) -> DiplomRead:
    obj = await svc.update_diplom(diplom_id, payload)
    await svc.session.commit()
    return DiplomRead.model_validate(obj)


@router.delete(
    "/diploms/{diplom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def delete_diplom(
    diplom_id: UUID, svc: ApplicantsService = Depends(_service)
) -> Response:
    await svc.delete_diplom(diplom_id)
    await svc.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Transfer diploms ----------
@router.get(
    "/transfer-diploms",
    response_model=PageResponse[TransferDiplomWithApplicant],
    dependencies=[Depends(require_permission(Permission.APPLICANTS_READ))],
)
async def list_transfer_diploms(
    user_id: UUID | None = Query(default=None),
    country_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    svc: ApplicantsService = Depends(_service),
) -> PageResponse[TransferDiplomWithApplicant]:
    items, total = await svc.list_transfer_diploms(
        user_id=user_id, country_id=country_id, search=search,
        limit=size, offset=(page - 1) * size,
    )
    return PageResponse[TransferDiplomWithApplicant].build(
        items=[TransferDiplomWithApplicant.model_validate(d) for d in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/transfer-diploms/{item_id}",
    response_model=TransferDiplomRead,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_READ))],
)
async def get_transfer_diplom(
    item_id: UUID, svc: ApplicantsService = Depends(_service)
) -> TransferDiplomRead:
    obj = await svc.get_transfer_diplom(item_id)
    return TransferDiplomRead.model_validate(obj)


@router.post(
    "/transfer-diploms",
    response_model=TransferDiplomRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def create_transfer_diplom(
    payload: TransferDiplomCreate, svc: ApplicantsService = Depends(_service)
) -> TransferDiplomRead:
    obj = await svc.upsert_transfer_diplom(payload)
    await svc.session.commit()
    return TransferDiplomRead.model_validate(obj)


@router.put(
    "/transfer-diploms/by-user/{user_id}",
    response_model=TransferDiplomRead,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def staff_upsert_transfer_diplom(
    user_id: UUID,
    payload: TransferDiplomCreate,
    svc: ApplicantsService = Depends(_service),
) -> TransferDiplomRead:
    data = payload.model_copy(update={"user_id": user_id})
    obj = await svc.upsert_transfer_diplom(data)
    await svc.session.commit()
    return TransferDiplomRead.model_validate(obj)


@router.patch(
    "/transfer-diploms/{item_id}",
    response_model=TransferDiplomRead,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def staff_update_transfer_diplom(
    item_id: UUID,
    payload: TransferDiplomUpdate,
    svc: ApplicantsService = Depends(_service),
) -> TransferDiplomRead:
    obj = await svc.update_transfer_diplom(item_id, payload)
    await svc.session.commit()
    return TransferDiplomRead.model_validate(obj)


@router.delete(
    "/transfer-diploms/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def delete_transfer_diplom(
    item_id: UUID, svc: ApplicantsService = Depends(_service)
) -> Response:
    await svc.delete_transfer_diplom(item_id)
    await svc.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# /{applicant_id} routes — must come AFTER all literal-path routes above
# (otherwise FastAPI matches /diploms etc. as applicant_id="diploms" and 422s)
# =============================================================================

@router.get(
    "/{applicant_id}",
    response_model=ApplicantDetailed,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_READ))],
)
async def get_applicant(
    applicant_id: UUID,
    svc: ApplicantsService = Depends(_service),
) -> ApplicantDetailed:
    obj = await svc.get(applicant_id)
    diplom = await svc.diploms.get_by_user_id(obj.user_id)
    transfer = await svc.transfer_diploms.get_by_user_id(obj.user_id)
    detail = ApplicantDetailed.model_validate(obj)
    detail.diplom = DiplomRead.model_validate(diplom) if diplom else None
    detail.transfer_diplom = TransferDiplomRead.model_validate(transfer) if transfer else None
    return detail


@router.patch(
    "/{applicant_id}",
    response_model=ApplicantRead,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def staff_update_applicant(
    applicant_id: UUID,
    payload: ApplicantUpdate,
    svc: ApplicantsService = Depends(_service),
) -> ApplicantRead:
    obj = await svc.update(applicant_id, payload)
    await svc.session.commit()
    return ApplicantRead.model_validate(obj)


@router.delete(
    "/{applicant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def staff_delete_applicant(
    applicant_id: UUID,
    svc: ApplicantsService = Depends(_service),
):
    await svc.delete(applicant_id)
    await svc.session.commit()


@router.post(
    "/bulk-delete",
    dependencies=[Depends(require_permission(Permission.APPLICANTS_WRITE))],
)
async def bulk_delete_applicants(
    payload: dict,
    svc: ApplicantsService = Depends(_service),
) -> dict:
    """Bulk-delete applicants. Each delete cascades through the FK chain
    (diploms, applications, contracts, payments) per migration 03 — same
    as the per-row endpoint.
    """
    ids_raw = payload.get("ids") or []
    if not isinstance(ids_raw, list) or not ids_raw:
        raise HTTPException(status_code=400, detail="ids list is required")
    try:
        ids = [UUID(str(i)) for i in ids_raw]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid id in list")
    deleted = 0
    skipped = 0
    for aid in ids:
        try:
            await svc.delete(aid)
            deleted += 1
        except Exception:
            skipped += 1
    await svc.session.commit()
    return {"deleted": deleted, "skipped": skipped}


