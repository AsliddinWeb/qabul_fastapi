from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.enums import AdmissionType, ApplicationStatus
from app.modules.applicants.repository import ApplicantRepository, DiplomRepository, TransferDiplomRepository
from app.modules.applications.models import Application
from app.modules.applications.repository import (
    ApplicationRepository,
    ApplicationStatusHistoryRepository,
)
from app.modules.applications.schemas import (
    ApplicationCreateForApplicant,
    ApplicationCreateSelf,
    ApplicationReview,
    ApplicationUpdate,
)
from app.modules.programs.repository import ProgramRepository


def _generate_application_number() -> str:
    year = datetime.now(timezone.utc).year
    return f"XIU-{year}-{uuid4().hex[:8].upper()}"


class ApplicationsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ApplicationRepository(session)
        self.history = ApplicationStatusHistoryRepository(session)
        self.applicants = ApplicantRepository(session)
        self.programs = ProgramRepository(session)
        self.diploms = DiplomRepository(session)
        self.transfer_diploms = TransferDiplomRepository(session)

    # ---------- Read ----------
    async def get(self, application_id: UUID) -> Application:
        obj = await self.repo.get(application_id)
        if not obj:
            raise NotFoundError("Application not found")
        return obj

    async def get_or_403_for_applicant(
        self, application_id: UUID, *, applicant_id: UUID
    ) -> Application:
        obj = await self.get(application_id)
        if obj.applicant_id != applicant_id:
            raise ForbiddenError("Cannot access another applicant's application")
        return obj

    async def list_for_applicant(self, applicant_id: UUID) -> list[Application]:
        return await self.repo.list_for_applicant(applicant_id)

    async def list_detailed_for_applicant(self, applicant_id: UUID) -> list[dict]:
        return await self.repo.detailed_for_applicant(applicant_id)

    async def list(self, **filters) -> tuple[list[Application], int]:
        return await self.repo.list_filtered(**filters)

    async def list_detailed(self, **filters) -> tuple[list[dict], int]:
        return await self.repo.list_detailed(**filters)

    async def status_counts(self) -> dict[str, int]:
        return await self.repo.status_counts()

    async def monthly_trend(self, months: int = 12) -> list[dict]:
        return await self.repo.monthly_trend(months)

    # ---------- Create ----------
    async def create(
        self,
        *,
        applicant_id: UUID,
        payload: ApplicationCreateSelf,
        actor_id: UUID,
    ) -> Application:
        applicant = await self.applicants.get(applicant_id)
        if not applicant:
            raise NotFoundError("Applicant not found")

        program = await self.programs.get(payload.program_id)
        if not program:
            raise NotFoundError("Program not found")
        if not program.is_active:
            raise ValidationError("Program is not active")

        # Sanity-check: branch / level / form on program must match payload.
        if (
            program.branch_id != payload.branch_id
            or program.education_level_id != payload.education_level_id
            or program.education_form_id != payload.education_form_id
        ):
            raise ValidationError(
                "Program's branch / education level / education form mismatch"
            )

        # Diplom / transfer_diplom validation already enforced in schema.
        if payload.admission_type == AdmissionType.REGULAR and payload.diplom_id:
            d = await self.diploms.get(payload.diplom_id)
            if not d or d.user_id != applicant.user_id:
                raise ValidationError("Diplom does not belong to this applicant")
        if payload.admission_type == AdmissionType.TRANSFER and payload.transfer_diplom_id:
            td = await self.transfer_diploms.get(payload.transfer_diplom_id)
            if not td or td.user_id != applicant.user_id:
                raise ValidationError("Transfer diplom does not belong to this applicant")

        # One ACTIVE application per applicant — they pick a single program.
        # Rejected applications don't count (admin can re-apply on someone's
        # behalf after a rejection); pending / under-review / accepted do.
        all_for_applicant = await self.repo.list_for_applicant(applicant_id)
        active = [a for a in all_for_applicant if a.status != ApplicationStatus.REJECTED]
        if active:
            raise ConflictError(
                "Bu abituriyent uchun aktiv ariza allaqachon mavjud. "
                "Yangi ariza topshirish uchun avval mavjudini o'chirib tashlash kerak."
            )

        application = await self.repo.create(
            application_number=_generate_application_number(),
            applicant_id=applicant_id,
            admission_type=payload.admission_type,
            branch_id=payload.branch_id,
            education_level_id=payload.education_level_id,
            education_form_id=payload.education_form_id,
            program_id=payload.program_id,
            diplom_id=payload.diplom_id,
            transfer_diplom_id=payload.transfer_diplom_id,
            course_id=payload.course_id,
            status=ApplicationStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
            notes=payload.notes,
        )

        await self.history.create(
            application_id=application.id,
            from_status=None,
            to_status=ApplicationStatus.PENDING,
            changed_by_id=actor_id,
            comment="created",
        )
        return application

    async def create_for_applicant(
        self, payload: ApplicationCreateForApplicant, *, actor_id: UUID
    ) -> Application:
        return await self.create(
            applicant_id=payload.applicant_id,
            payload=payload,
            actor_id=actor_id,
        )

    # ---------- Update (staff) ----------
    async def update(self, application_id: UUID, payload: ApplicationUpdate) -> Application:
        obj = await self.get(application_id)
        return await self.repo.update(obj, **payload.model_dump(exclude_unset=True))

    # ---------- Delete (staff) ----------
    async def delete(self, application_id: UUID) -> None:
        obj = await self.get(application_id)
        await self.repo.delete(obj)

    # ---------- Review ----------
    async def review(
        self,
        application_id: UUID,
        payload: ApplicationReview,
        *,
        reviewer_id: UUID,
    ) -> Application:
        obj = await self.get(application_id)
        if obj.status not in {ApplicationStatus.PENDING, ApplicationStatus.REVIEW}:
            raise ValidationError(f"Cannot review application in status '{obj.status.value}'")

        new_status = ApplicationStatus.ACCEPTED if payload.approved else ApplicationStatus.REJECTED
        old_status = obj.status

        obj.status = new_status
        obj.reviewed_by_id = reviewer_id
        obj.reviewed_at = datetime.now(timezone.utc)
        if payload.rejection_reason is not None:
            obj.rejection_reason = payload.rejection_reason
        if payload.notes is not None:
            obj.notes = payload.notes
        await self.session.flush()

        await self.history.create(
            application_id=obj.id,
            from_status=old_status,
            to_status=new_status,
            changed_by_id=reviewer_id,
            comment=payload.rejection_reason if not payload.approved else "approved",
        )
        return obj

    async def mark_review(self, application_id: UUID, *, reviewer_id: UUID) -> Application:
        """Move PENDING → REVIEW (operator picked up the file)."""
        obj = await self.get(application_id)
        if obj.status != ApplicationStatus.PENDING:
            raise ValidationError(f"Only PENDING applications can be moved to REVIEW (got '{obj.status.value}')")
        old = obj.status
        obj.status = ApplicationStatus.REVIEW
        obj.reviewed_by_id = reviewer_id
        await self.session.flush()
        await self.history.create(
            application_id=obj.id,
            from_status=old,
            to_status=ApplicationStatus.REVIEW,
            changed_by_id=reviewer_id,
            comment="marked under review",
        )
        return obj

    # ---------- Withdraw (self) ----------
    async def withdraw(self, application_id: UUID, *, actor_id: UUID) -> Application:
        obj = await self.get(application_id)
        if obj.status not in {ApplicationStatus.PENDING, ApplicationStatus.REVIEW}:
            raise ValidationError(
                f"Cannot withdraw application in status '{obj.status.value}'"
            )
        old = obj.status
        obj.status = ApplicationStatus.REJECTED
        await self.session.flush()
        await self.history.create(
            application_id=obj.id,
            from_status=old,
            to_status=ApplicationStatus.REJECTED,
            changed_by_id=actor_id,
            comment="withdrawn by applicant",
        )
        return obj
