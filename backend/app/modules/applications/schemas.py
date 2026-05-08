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

    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check_admission_consistency(self) -> "ApplicationCreateSelf":
        if self.admission_type == AdmissionType.TRANSFER:
            if self.transfer_diplom_id is None:
                raise ValueError("Perevod uchun transfer_diplom_id majburiy")
            if self.course_id is None:
                raise ValueError("Perevod uchun course_id majburiy")
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
    branch_id: UUID | None = None
    education_level_id: UUID | None = None
    education_form_id: UUID | None = None
    program_id: UUID | None = None
    diplom_id: UUID | None = None
    transfer_diplom_id: UUID | None = None
    course_id: UUID | None = None
    contract_file_id: UUID | None = None
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


class ApplicationDetailed(ApplicationRead):
    """Application with denormalized program/branch info — used in lists/detail."""

    program_name: str | None = None
    program_code: str | None = None
    branch_name: str | None = None
    education_level_name: str | None = None
    education_form_name: str | None = None
    applicant_full_name: str | None = None
