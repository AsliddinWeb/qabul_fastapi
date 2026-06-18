from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema
from app.db.enums import Gender


def _empty_to_none(v: Any) -> Any:
    """Coerce empty/whitespace-only strings to None.

    Frontend forms commonly send '' for cleared fields, but typed fields
    like EmailStr / pattern-validated strings reject ''. Treating it as
    None makes the API forgiving without losing real validation.
    """
    if isinstance(v, str) and not v.strip():
        return None
    return v


# ---------- Applicant ----------
class ApplicantBase(AppSchema):
    last_name: str = Field(min_length=1, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    other_name: str | None = Field(default=None, max_length=100)
    birth_date: date
    gender: Gender

    passport_series: str | None = Field(default=None, pattern=r"^[A-Z]{2}\d{7}$")
    pinfl: str | None = Field(default=None, pattern=r"^\d{14}$")

    region_id: UUID | None = None
    district_id: UUID | None = None
    address: str | None = None

    nationality: str = Field(default="O'zbek", max_length=50)
    additional_phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    telegram_username: str | None = Field(default=None, max_length=64)

    image_id: UUID | None = None
    passport_file_id: UUID | None = None

    @field_validator(
        "other_name", "passport_series", "pinfl", "address",
        "additional_phone", "email", "telegram_username",
        mode="before",
    )
    @classmethod
    def _strip_empty(cls, v: Any) -> Any:
        return _empty_to_none(v)

    @field_validator("region_id", "district_id", "image_id", "passport_file_id", mode="before")
    @classmethod
    def _empty_uuid(cls, v: Any) -> Any:
        return _empty_to_none(v)


class ApplicantCreate(ApplicantBase):
    """Self-registration: user_id is taken from the authenticated user."""

    # Optional invite code (the public referral_code of another user). When
    # set, the applicants service registers a `pending` referral row.
    referrer_code: str | None = Field(default=None, max_length=8)


class ApplicantCreateForOperator(ApplicantBase):
    """Operator manually creates an applicant — no auth flow on applicant side."""

    phone: str = Field(min_length=4, max_length=20)
    referrer_code: str | None = Field(default=None, max_length=8)


class ApplicantUpdate(AppSchema):
    last_name: str | None = Field(default=None, max_length=100)
    first_name: str | None = Field(default=None, max_length=100)
    other_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    gender: Gender | None = None
    passport_series: str | None = Field(default=None, pattern=r"^[A-Z]{2}\d{7}$")
    pinfl: str | None = Field(default=None, pattern=r"^\d{14}$")
    region_id: UUID | None = None
    district_id: UUID | None = None
    address: str | None = None
    nationality: str | None = Field(default=None, max_length=50)
    additional_phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    telegram_username: str | None = Field(default=None, max_length=64)
    image_id: UUID | None = None
    passport_file_id: UUID | None = None

    @field_validator(
        "last_name", "first_name", "other_name", "passport_series", "pinfl",
        "address", "nationality", "additional_phone", "email", "telegram_username",
        mode="before",
    )
    @classmethod
    def _strip_empty(cls, v: Any) -> Any:
        return _empty_to_none(v)

    @field_validator("region_id", "district_id", "image_id", "passport_file_id", mode="before")
    @classmethod
    def _empty_uuid(cls, v: Any) -> Any:
        return _empty_to_none(v)


class ApplicantRead(IdSchema, TimestampedSchema, ApplicantBase):
    user_id: UUID
    registered_by_id: UUID | None = None


# ---------- Diplom catalog ----------
class _NameOnlyBase(AppSchema):
    name: str = Field(min_length=1, max_length=255)


class _NameOnlyUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class EducationTypeRead(IdSchema, TimestampedSchema, _NameOnlyBase):
    pass


class EducationTypeCreate(_NameOnlyBase):
    pass


class EducationTypeUpdate(_NameOnlyUpdate):
    pass


class InstitutionTypeRead(IdSchema, TimestampedSchema, _NameOnlyBase):
    pass


class InstitutionTypeCreate(_NameOnlyBase):
    pass


class InstitutionTypeUpdate(_NameOnlyUpdate):
    pass


class CourseRead(IdSchema, TimestampedSchema, _NameOnlyBase):
    pass


class CourseCreate(_NameOnlyBase):
    pass


class CourseUpdate(_NameOnlyUpdate):
    pass


# ---------- Diplom ----------
class DiplomBase(AppSchema):
    user_id: UUID
    serial_number: str = Field(min_length=1, max_length=100)
    education_type_id: UUID
    institution_type_id: UUID
    university_name: str = Field(min_length=1)
    graduation_year: str = Field(pattern=r"^\d{4}$")
    region_id: UUID
    district_id: UUID
    diploma_file_id: UUID | None = None
    # TRUE = Bachelor's diploma used for the 2-mutaxassislik flow.
    # Defaults to FALSE so existing callers (1-kurs flow) keep working.
    is_for_second_specialization: bool = False


class DiplomCreate(DiplomBase):
    pass


class DiplomUpdate(AppSchema):
    serial_number: str | None = Field(default=None, max_length=100)
    education_type_id: UUID | None = None
    institution_type_id: UUID | None = None
    university_name: str | None = None
    graduation_year: str | None = Field(default=None, pattern=r"^\d{4}$")
    region_id: UUID | None = None
    district_id: UUID | None = None
    diploma_file_id: UUID | None = None
    is_for_second_specialization: bool | None = None


class DiplomRead(IdSchema, TimestampedSchema, DiplomBase):
    pass


class DiplomWithApplicant(DiplomRead):
    """Diplom + applicant denormalized info — for list endpoint."""

    applicant_last_name: str | None = None
    applicant_first_name: str | None = None
    applicant_other_name: str | None = None
    applicant_pinfl: str | None = None
    applicant_passport_series: str | None = None


# ---------- TransferDiplom ----------
class TransferDiplomBase(AppSchema):
    user_id: UUID
    country_id: UUID
    university_name: str = Field(min_length=1)
    target_course_id: UUID
    transcript_file_id: UUID | None = None


class TransferDiplomCreate(TransferDiplomBase):
    pass


class TransferDiplomUpdate(AppSchema):
    country_id: UUID | None = None
    university_name: str | None = None
    target_course_id: UUID | None = None
    transcript_file_id: UUID | None = None


class TransferDiplomRead(IdSchema, TimestampedSchema, TransferDiplomBase):
    pass


class TransferDiplomWithApplicant(TransferDiplomRead):
    applicant_last_name: str | None = None
    applicant_first_name: str | None = None
    applicant_other_name: str | None = None
    applicant_pinfl: str | None = None
    applicant_passport_series: str | None = None


class ApplicantDetailed(ApplicantRead):
    """Applicant with nested diplom + transfer diplom (if any)."""

    diplom: DiplomRead | None = None
    transfer_diplom: TransferDiplomRead | None = None
