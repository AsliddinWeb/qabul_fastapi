from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    CurrentUser,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import ForbiddenError
from app.core.permissions import Permission
from app.core.schemas import PageResponse
from app.db.enums import AdmissionType, ApplicationStatus
from app.integrations.crm.events import enqueue_application_status_event
from app.modules.applicants.repository import ApplicantRepository
from app.modules.applications.schemas import (
    ApplicationCreateForApplicant,
    ApplicationCreateSelf,
    ApplicationDetailed,
    ApplicationRead,
    ApplicationReview,
    ApplicationUpdate,
)
from app.modules.applications.service import ApplicationsService
from app.modules.audit.service import AuditService

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> ApplicationsService:
    return ApplicationsService(session)


# ---------- Self ----------
@router.get(
    "/me",
    response_model=list[ApplicationDetailed],
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_READ_SELF))],
)
async def list_my_applications(
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicationsService = Depends(_service),
) -> list[ApplicationDetailed]:
    applicants = ApplicantRepository(svc.session)
    me = await applicants.get_by_user_id(UUID(current.user_id))
    if not me:
        return []
    rows = await svc.list_detailed_for_applicant(me.id)
    return [ApplicationDetailed.model_validate(r) for r in rows]


@router.post(
    "/me",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_CREATE_SELF))],
)
async def submit_my_application(
    payload: ApplicationCreateSelf,
    request: Request,
    background: BackgroundTasks,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicationsService = Depends(_service),
) -> ApplicationRead:
    applicants = ApplicantRepository(svc.session)
    me = await applicants.get_by_user_id(UUID(current.user_id))
    if not me:
        raise ForbiddenError("Complete your applicant profile before submitting an application")

    obj = await svc.create(
        applicant_id=me.id,
        payload=payload,
        actor_id=UUID(current.user_id),
    )
    await AuditService(svc.session).log(
        "application.create",
        user_id=UUID(current.user_id),
        entity_type="applications",
        entity_id=obj.id,
        changes={
            "applicant_id": str(me.id),
            "program_id": str(payload.program_id),
            "admission_type": payload.admission_type.value,
        },
        request=request,
    )
    await svc.session.commit()

    enqueue_application_status_event(
        background,
        external_id=str(me.id),
        status=obj.status.value,
        note=f"submitted application {obj.application_number}",
    )
    return ApplicationRead.model_validate(obj)


@router.post(
    "/me/{application_id}/withdraw",
    response_model=ApplicationRead,
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_WITHDRAW_SELF))],
)
async def withdraw_my_application(
    application_id: UUID,
    request: Request,
    background: BackgroundTasks,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicationsService = Depends(_service),
) -> ApplicationRead:
    applicants = ApplicantRepository(svc.session)
    me = await applicants.get_by_user_id(UUID(current.user_id))
    if not me:
        raise ForbiddenError("No applicant profile")

    await svc.get_or_403_for_applicant(application_id, applicant_id=me.id)
    obj = await svc.withdraw(application_id, actor_id=UUID(current.user_id))
    await AuditService(svc.session).log(
        "application.withdraw",
        user_id=UUID(current.user_id),
        entity_type="applications",
        entity_id=obj.id,
        request=request,
    )
    await svc.session.commit()

    enqueue_application_status_event(
        background,
        external_id=str(me.id),
        status=obj.status.value,
        note="withdrawn by applicant",
    )
    return ApplicationRead.model_validate(obj)


# ---------- Staff ----------
@router.get(
    "/stats",
    response_model=dict[str, int],
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_LIST))],
)
async def application_stats(svc: ApplicationsService = Depends(_service)) -> dict[str, int]:
    return await svc.status_counts()


@router.get(
    "/trend",
    response_model=list[dict],
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_LIST))],
)
async def application_trend(
    months: int = Query(default=12, ge=1, le=24),
    svc: ApplicationsService = Depends(_service),
) -> list[dict]:
    """Monthly application counts (per-status), 12 buckets by default. For dashboard chart."""
    return await svc.monthly_trend(months)


@router.get(
    "",
    response_model=PageResponse[ApplicationDetailed],
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_LIST))],
)
async def list_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    admission_type: AdmissionType | None = Query(default=None),
    program_id: UUID | None = Query(default=None),
    branch_id: UUID | None = Query(default=None),
    education_level_id: UUID | None = Query(default=None),
    education_form_id: UUID | None = Query(default=None),
    consulting_agency_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    svc: ApplicationsService = Depends(_service),
) -> PageResponse[ApplicationDetailed]:
    items, total = await svc.list_detailed(
        status=status_filter,
        admission_type=admission_type,
        program_id=program_id,
        branch_id=branch_id,
        education_level_id=education_level_id,
        education_form_id=education_form_id,
        consulting_agency_id=consulting_agency_id,
        limit=size,
        offset=(page - 1) * size,
    )
    return PageResponse[ApplicationDetailed].build(
        items=[ApplicationDetailed.model_validate(a) for a in items],
        total=total, page=page, size=size,
    )


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_REVIEW))],
)
async def staff_create_application(
    payload: ApplicationCreateForApplicant,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicationsService = Depends(_service),
) -> ApplicationRead:
    obj = await svc.create_for_applicant(payload, actor_id=UUID(current.user_id))

    # If this application is the conversion of a Lead, mark it as won + link back.
    if payload.lead_id:
        from app.modules.leads.service import LeadService
        from app.modules.leads.repository import LeadSourceRepository
        # Stamp source code on the application for analytics (denormalised cache).
        lead_svc = LeadService(svc.session)
        lead = await lead_svc.leads.get(payload.lead_id)
        if lead:
            obj.lead_id = lead.id
            if lead.source_id:
                src = await LeadSourceRepository(svc.session).get(lead.source_id)
                obj.lead_source_code = src.code if src else None
            await lead_svc.mark_converted(
                lead.id,
                applicant_id=payload.applicant_id,
                application_id=obj.id,
                actor_id=UUID(current.user_id),
            )

    await AuditService(svc.session).log(
        "application.create_by_staff",
        user_id=UUID(current.user_id),
        entity_type="applications",
        entity_id=obj.id,
        changes={
            "applicant_id": str(payload.applicant_id),
            "program_id": str(payload.program_id),
            "admission_type": payload.admission_type.value,
            "lead_id": str(payload.lead_id) if payload.lead_id else None,
        },
        request=request,
    )
    await svc.session.commit()
    return ApplicationRead.model_validate(obj)


@router.get(
    "/{application_id}",
    response_model=ApplicationRead,
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_READ))],
)
async def get_application(
    application_id: UUID,
    svc: ApplicationsService = Depends(_service),
) -> ApplicationRead:
    obj = await svc.get(application_id)
    return ApplicationRead.model_validate(obj)


@router.patch(
    "/{application_id}",
    response_model=ApplicationRead,
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_REVIEW))],
)
async def staff_update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    svc: ApplicationsService = Depends(_service),
) -> ApplicationRead:
    obj = await svc.update(application_id, payload)
    await svc.session.commit()
    return ApplicationRead.model_validate(obj)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_REVIEW))],
)
async def staff_delete_application(
    application_id: UUID,
    svc: ApplicationsService = Depends(_service),
):
    await svc.delete(application_id)
    await svc.session.commit()


@router.post(
    "/{application_id}/review",
    response_model=ApplicationRead,
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_REVIEW))],
)
async def review_application(
    application_id: UUID,
    payload: ApplicationReview,
    request: Request,
    background: BackgroundTasks,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicationsService = Depends(_service),
) -> ApplicationRead:
    obj = await svc.review(application_id, payload, reviewer_id=UUID(current.user_id))
    await AuditService(svc.session).log(
        "application.review",
        user_id=UUID(current.user_id),
        entity_type="applications",
        entity_id=obj.id,
        changes={
            "approved": payload.approved,
            "rejection_reason": payload.rejection_reason,
        },
        request=request,
    )
    await svc.session.commit()

    enqueue_application_status_event(
        background,
        external_id=str(obj.applicant_id),
        status=obj.status.value,
        note=payload.rejection_reason if not payload.approved else "approved",
    )
    return ApplicationRead.model_validate(obj)


@router.post(
    "/{application_id}/start-review",
    response_model=ApplicationRead,
    dependencies=[Depends(require_permission(Permission.APPLICATIONS_REVIEW))],
)
async def start_review(
    application_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    svc: ApplicationsService = Depends(_service),
) -> ApplicationRead:
    obj = await svc.mark_review(application_id, reviewer_id=UUID(current.user_id))
    await svc.session.commit()
    return ApplicationRead.model_validate(obj)
