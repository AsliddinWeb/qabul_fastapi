from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.core.schemas import AppSchema, IdSchema, TimestampedSchema


# ---------- Branch ----------
class BranchBase(AppSchema):
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class BranchRead(IdSchema, TimestampedSchema, BranchBase):
    pass


# ---------- EducationLevel ----------
class EducationLevelBase(AppSchema):
    name: str = Field(min_length=1, max_length=100)


class EducationLevelCreate(EducationLevelBase):
    pass


class EducationLevelUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class EducationLevelRead(IdSchema, TimestampedSchema, EducationLevelBase):
    pass


# ---------- EducationForm ----------
class EducationFormBase(AppSchema):
    name: str = Field(min_length=1, max_length=100)


class EducationFormCreate(EducationFormBase):
    pass


class EducationFormUpdate(AppSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class EducationFormRead(IdSchema, TimestampedSchema, EducationFormBase):
    pass


# ---------- Program ----------
class ProgramBase(AppSchema):
    branch_id: UUID
    education_level_id: UUID
    education_form_id: UUID
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=100)
    image_id: UUID | None = None
    tuition_fee: Decimal = Field(gt=0, description="Yillik to'lov, so'm")
    study_duration_years: int = Field(ge=1, le=8)
    contract_series: str = Field(min_length=1, max_length=100)
    is_active: bool = True


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(AppSchema):
    branch_id: UUID | None = None
    education_level_id: UUID | None = None
    education_form_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    image_id: UUID | None = None
    tuition_fee: Decimal | None = Field(default=None, gt=0)
    study_duration_years: int | None = Field(default=None, ge=1, le=8)
    contract_series: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class ProgramRead(IdSchema, TimestampedSchema, ProgramBase):
    pass


class ProgramExpanded(ProgramRead):
    """Program with denormalized branch/level/form names — for landing/applicant UI."""

    branch_name: str
    education_level_name: str
    education_form_name: str
