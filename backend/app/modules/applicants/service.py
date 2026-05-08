from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.db.enums import UserRole
from app.modules.applicants.models import (
    Applicant,
    Course,
    Diplom,
    EducationType,
    InstitutionType,
    TransferDiplom,
)
from app.modules.applicants.repository import (
    ApplicantRepository,
    CourseRepository,
    DiplomRepository,
    EducationTypeRepository,
    InstitutionTypeRepository,
    TransferDiplomRepository,
)
from app.modules.applicants.schemas import (
    ApplicantCreate,
    ApplicantCreateForOperator,
    ApplicantUpdate,
    CourseCreate,
    CourseUpdate,
    DiplomCreate,
    DiplomUpdate,
    EducationTypeCreate,
    EducationTypeUpdate,
    InstitutionTypeCreate,
    InstitutionTypeUpdate,
    TransferDiplomCreate,
    TransferDiplomUpdate,
)
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.utils.phone import normalize_phone


def _normalize_applicant(data: dict) -> dict:
    """Match old Django AbituriyentProfile.save(): UPPER + strip names + passport."""
    for key in ("last_name", "first_name", "other_name"):
        v = data.get(key)
        if isinstance(v, str):
            data[key] = v.upper().strip()
    if isinstance(data.get("passport_series"), str):
        data["passport_series"] = data["passport_series"].upper().strip()
    if isinstance(data.get("pinfl"), str):
        data["pinfl"] = data["pinfl"].strip()
    if isinstance(data.get("address"), str):
        data["address"] = data["address"].strip()
    return data


class ApplicantsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.applicants = ApplicantRepository(session)
        self.education_types = EducationTypeRepository(session)
        self.institution_types = InstitutionTypeRepository(session)
        self.courses = CourseRepository(session)
        self.diploms = DiplomRepository(session)
        self.transfer_diploms = TransferDiplomRepository(session)
        self.users = UserRepository(session)

    # ---------- Applicant ----------
    async def list(self, **filters) -> tuple[list[Applicant], int]:
        return await self.applicants.list_filtered(**filters)

    async def get(self, applicant_id: UUID) -> Applicant:
        obj = await self.applicants.get(applicant_id)
        if not obj:
            raise NotFoundError("Applicant not found")
        return obj

    async def get_for_user(self, user_id: UUID) -> Applicant:
        obj = await self.applicants.get_by_user_id(user_id)
        if not obj:
            raise NotFoundError("Applicant profile not found")
        return obj

    async def get_or_403(
        self,
        applicant_id: UUID,
        *,
        current_user_id: UUID,
        current_role: UserRole,
    ) -> Applicant:
        obj = await self.get(applicant_id)
        if current_role == UserRole.APPLICANT and obj.user_id != current_user_id:
            raise ForbiddenError("Cannot access another applicant's profile")
        return obj

    async def create_for_user(
        self,
        user_id: UUID,
        payload: ApplicantCreate,
        *,
        registered_by_id: UUID | None = None,
    ) -> Applicant:
        if await self.applicants.get_by_user_id(user_id):
            raise ConflictError("Applicant profile already exists for this user")
        data = _normalize_applicant(payload.model_dump())
        if data.get("pinfl") and await self.applicants.get_by_pinfl(data["pinfl"]):
            raise ConflictError("Applicant with this PINFL already exists")
        return await self.applicants.create(
            user_id=user_id,
            registered_by_id=registered_by_id,
            **data,
        )

    async def create_by_operator(
        self,
        payload: ApplicantCreateForOperator,
        *,
        operator_id: UUID,
    ) -> tuple[Applicant, User]:
        phone = normalize_phone(payload.phone)
        data = _normalize_applicant(payload.model_dump(exclude={"phone"}))

        user = await self.users.get_by_phone(phone)
        if user is None:
            user = await self.users.create(
                phone=phone,
                role=UserRole.APPLICANT,
                is_active=True,
                is_phone_verified=True,
                created_by_id=operator_id,
            )
        else:
            if user.role != UserRole.APPLICANT:
                raise ConflictError(
                    "Phone is already used by a staff account; cannot register applicant"
                )
            if await self.applicants.get_by_user_id(user.id):
                raise ConflictError("Applicant with this phone already exists")

        if data.get("pinfl") and await self.applicants.get_by_pinfl(data["pinfl"]):
            raise ConflictError("Applicant with this PINFL already exists")

        applicant = await self.applicants.create(
            user_id=user.id,
            registered_by_id=operator_id,
            **data,
        )
        return applicant, user

    async def update(self, applicant_id: UUID, payload: ApplicantUpdate) -> Applicant:
        obj = await self.get(applicant_id)
        data = _normalize_applicant(payload.model_dump(exclude_unset=True))
        return await self.applicants.update(obj, **data)

    async def delete(self, applicant_id: UUID) -> None:
        obj = await self.get(applicant_id)
        await self.applicants.delete(obj)

    # ---------- Diplom catalog ----------
    async def list_education_types(self) -> list[EducationType]:
        return await self.education_types.list(limit=100, order_by=EducationType.name)

    async def create_education_type(self, payload: EducationTypeCreate) -> EducationType:
        if await self.education_types.exists(name=payload.name):
            raise ConflictError(f"Education type '{payload.name}' already exists")
        return await self.education_types.create(**payload.model_dump())

    async def update_education_type(self, item_id: UUID, payload: EducationTypeUpdate) -> EducationType:
        obj = await self.education_types.get(item_id)
        if not obj:
            raise NotFoundError("Education type not found")
        return await self.education_types.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_education_type(self, item_id: UUID) -> None:
        obj = await self.education_types.get(item_id)
        if not obj:
            raise NotFoundError("Education type not found")
        await self.education_types.delete(obj)

    async def list_institution_types(self) -> list[InstitutionType]:
        return await self.institution_types.list(limit=100, order_by=InstitutionType.name)

    async def create_institution_type(self, payload: InstitutionTypeCreate) -> InstitutionType:
        if await self.institution_types.exists(name=payload.name):
            raise ConflictError(f"Institution type '{payload.name}' already exists")
        return await self.institution_types.create(**payload.model_dump())

    async def update_institution_type(self, item_id: UUID, payload: InstitutionTypeUpdate) -> InstitutionType:
        obj = await self.institution_types.get(item_id)
        if not obj:
            raise NotFoundError("Institution type not found")
        return await self.institution_types.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_institution_type(self, item_id: UUID) -> None:
        obj = await self.institution_types.get(item_id)
        if not obj:
            raise NotFoundError("Institution type not found")
        await self.institution_types.delete(obj)

    async def list_courses(self) -> list[Course]:
        return await self.courses.list(limit=100, order_by=Course.name)

    async def create_course(self, payload: CourseCreate) -> Course:
        if await self.courses.exists(name=payload.name):
            raise ConflictError(f"Course '{payload.name}' already exists")
        return await self.courses.create(**payload.model_dump())

    async def update_course(self, item_id: UUID, payload: CourseUpdate) -> Course:
        obj = await self.courses.get(item_id)
        if not obj:
            raise NotFoundError("Course not found")
        return await self.courses.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_course(self, item_id: UUID) -> None:
        obj = await self.courses.get(item_id)
        if not obj:
            raise NotFoundError("Course not found")
        await self.courses.delete(obj)

    # ---------- Diplom (1-kurs) ----------
    async def list_diploms(self, **filters) -> tuple[list[Diplom], int]:
        return await self.diploms.list_filtered(**filters)

    async def get_diplom(self, diplom_id: UUID) -> Diplom:
        obj = await self.diploms.get(diplom_id)
        if not obj:
            raise NotFoundError("Diplom not found")
        return obj

    async def get_diplom_for_user(self, user_id: UUID) -> Diplom:
        obj = await self.diploms.get_by_user_id(user_id)
        if not obj:
            raise NotFoundError("Diplom not found")
        return obj

    async def upsert_diplom(self, payload: DiplomCreate) -> Diplom:
        existing = await self.diploms.get_by_user_id(payload.user_id)
        if existing:
            data = payload.model_dump(exclude={"user_id"})
            return await self.diploms.update(existing, **data)
        return await self.diploms.create(**payload.model_dump())

    async def update_diplom(self, diplom_id: UUID, payload: DiplomUpdate) -> Diplom:
        obj = await self.diploms.get(diplom_id)
        if not obj:
            raise NotFoundError("Diplom not found")
        return await self.diploms.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_diplom(self, diplom_id: UUID) -> None:
        obj = await self.diploms.get(diplom_id)
        if not obj:
            raise NotFoundError("Diplom not found")
        await self.diploms.delete(obj)

    # ---------- TransferDiplom (perevod) ----------
    async def list_transfer_diploms(self, **filters) -> tuple[list[TransferDiplom], int]:
        return await self.transfer_diploms.list_filtered(**filters)

    async def get_transfer_diplom(self, item_id: UUID) -> TransferDiplom:
        obj = await self.transfer_diploms.get(item_id)
        if not obj:
            raise NotFoundError("Transfer diplom not found")
        return obj

    async def get_transfer_diplom_for_user(self, user_id: UUID) -> TransferDiplom:
        obj = await self.transfer_diploms.get_by_user_id(user_id)
        if not obj:
            raise NotFoundError("Transfer diplom not found")
        return obj

    async def upsert_transfer_diplom(self, payload: TransferDiplomCreate) -> TransferDiplom:
        existing = await self.transfer_diploms.get_by_user_id(payload.user_id)
        if existing:
            data = payload.model_dump(exclude={"user_id"})
            return await self.transfer_diploms.update(existing, **data)
        return await self.transfer_diploms.create(**payload.model_dump())

    async def update_transfer_diplom(self, item_id: UUID, payload: TransferDiplomUpdate) -> TransferDiplom:
        obj = await self.transfer_diploms.get(item_id)
        if not obj:
            raise NotFoundError("Transfer diplom not found")
        return await self.transfer_diploms.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_transfer_diplom(self, item_id: UUID) -> None:
        obj = await self.transfer_diploms.get(item_id)
        if not obj:
            raise NotFoundError("Transfer diplom not found")
        await self.transfer_diploms.delete(obj)
