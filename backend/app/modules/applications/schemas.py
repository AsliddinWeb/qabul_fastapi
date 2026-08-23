from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema
from app.db.enums import AdmissionType, ApplicationStatus


class ApplicationCreateSelf(AppSchema):
    """Applicant submits an application to a specific program."""

    admission_type: AdmissionType = AdmissionType.REGULAR
    branch_id: UUID
    education_level_id: UUID
    education_form_id: UUID
    program_id: UUID

    diplom_id: UUID | None = None
    transfer_diplom_id: UUID | None = None
    course_id: UUID | None = None
    consulting_agency_id: UUID | None = None

    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check_admission_consistency(self) -> "ApplicationCreateSelf":
        if self.admission_type == AdmissionType.TRANSFER:
            if self.transfer_diplom_id is None:
                raise ValueError("O'qishni ko'chirish uchun transfer_diplom_id majburiy")
            if self.course_id is None:
                raise ValueError("O'qishni ko'chirish uchun course_id majburiy")
        elif self.admission_type == AdmissionType.SECOND_SPEC:
            # 2-mutaxassislik flow: Bachelor's diploma is the new requirement
            # (carrying is_for_second_specialization=True), and the course is
            # always 2 — backend resolves it from the courses catalogue at
            # service time, so the field is left optional on the API surface
            # and operators don't see "course_id majburiy" errors.
            if self.diplom_id is None:
                raise ValueError("2-mutaxassislik uchun diplom_id majburiy")
        elif self.admission_type == AdmissionType.MAGISTRATURA:
            # Magistratura uses the same Bachelor's diplom row (purpose=true)
            # as SECOND_SPEC. No special course_id — entrants always
            # start at kurs 1.
            if self.diplom_id is None:
                raise ValueError("Magistratura uchun Bakalavr diplomi majburiy")
        else:  # REGULAR
            if self.diplom_id is None:
                raise ValueError("Yangi qabul uchun diplom_id majburiy")
        return self


class ApplicationCreateForApplicant(ApplicationCreateSelf):
    """Operator/admin creates an application on behalf of a known applicant."""

    applicant_id: UUID
    # If this application is being created from a Lead (CRM convert flow),
    # the lead is automatically marked as won and linked back.
    lead_id: UUID | None = None


class ApplicationReview(AppSchema):
    """Approve or reject — used by staff."""

    approved: bool
    rejection_reason: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class ApplicationUpdate(AppSchema):
    admission_type: AdmissionType | None = None
    branch_id: UUID | None = None
    education_level_id: UUID | None = None
    education_form_id: UUID | None = None
    program_id: UUID | None = None
    diplom_id: UUID | None = None
    transfer_diplom_id: UUID | None = None
    course_id: UUID | None = None
    contract_file_id: UUID | None = None
    consulting_agency_id: UUID | None = None
    notes: str | None = None


class ApplicationRead(IdSchema, TimestampedSchema):
    application_number: str
    applicant_id: UUID
    admission_type: AdmissionType
    branch_id: UUID
    education_level_id: UUID
    education_form_id: UUID
    program_id: UUID
    diplom_id: UUID | None = None
    transfer_diplom_id: UUID | None = None
    course_id: UUID | None = None
    contract_file_id: UUID | None = None
    status: ApplicationStatus
    submitted_at: datetime | None = None
    reviewed_by_id: UUID | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    notes: str | None = None
    lead_id: UUID | None = None
    lead_source_code: str | None = None
    consulting_agency_id: UUID | None = None
    hemis_status: str = "qoshilmadi"
    hemis_marked_by: str | None = None
    hemis_marked_at: datetime | None = None
    hemis_comment: str | None = None


class HemisDecision(AppSchema):
    """Bot-set HEMIS enrolment decision (from the group's ✅/❌ buttons)."""

    status: str = Field(pattern="^(qoshildi|qoshilmadi)$")
    marked_by: str | None = Field(default=None, max_length=150)
    comment: str | None = Field(default=None, max_length=2000)


class ReassignOperator(AppSchema):
    """Root-superadmin reassigns the operator who registered the applicant."""

    operator_id: UUID


class ApplicationDetailed(ApplicationRead):
    """Application with denormalized program/branch info — used in lists/detail."""

    program_name: str | None = None
    program_code: str | None = None
    branch_name: str | None = None
    education_level_name: str | None = None
    education_form_name: str | None = None
    applicant_full_name: str | None = None
    consulting_agency_name: str | None = None
    # Operator who originally registered the applicant — handy on the
    # admin list to see who's bringing in students. Joined from
    # applicants.registered_by_id → users.
    applicant_registered_by_id: UUID | None = None
    applicant_registered_by_name: str | None = None
