from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.programs.models import Branch, EducationForm, EducationLevel, Program
from app.modules.programs.repository import (
    BranchRepository,
    EducationFormRepository,
    EducationLevelRepository,
    ProgramRepository,
)
from app.modules.programs.schemas import (
    BranchCreate,
    BranchUpdate,
    EducationFormCreate,
    EducationFormUpdate,
    EducationLevelCreate,
    EducationLevelUpdate,
    ProgramCreate,
    ProgramUpdate,
)


class ProgramsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.branches = BranchRepository(session)
        self.education_levels = EducationLevelRepository(session)
        self.education_forms = EducationFormRepository(session)
        self.programs = ProgramRepository(session)

    # ---------- Branches ----------
    async def list_branches(self, *, active_only: bool = True) -> list[Branch]:
        where = Branch.is_active.is_(True) if active_only else None
        return await self.branches.list(limit=200, order_by=Branch.name, where=where)

    async def create_branch(self, payload: BranchCreate) -> Branch:
        if await self.branches.exists(name=payload.name):
            raise ConflictError(f"Branch '{payload.name}' already exists")
        return await self.branches.create(**payload.model_dump())

    async def update_branch(self, branch_id: UUID, payload: BranchUpdate) -> Branch:
        obj = await self.branches.get(branch_id)
        if not obj:
            raise NotFoundError("Branch not found")
        return await self.branches.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_branch(self, branch_id: UUID) -> None:
        obj = await self.branches.get(branch_id)
        if not obj:
            raise NotFoundError("Branch not found")
        await self.branches.delete(obj)

    # ---------- Education Levels ----------
    async def list_education_levels(self) -> list[EducationLevel]:
        return await self.education_levels.list(limit=50, order_by=EducationLevel.name)

    async def create_education_level(self, payload: EducationLevelCreate) -> EducationLevel:
        if await self.education_levels.exists(name=payload.name):
            raise ConflictError(f"Education level '{payload.name}' already exists")
        return await self.education_levels.create(**payload.model_dump())

    async def update_education_level(self, level_id: UUID, payload: EducationLevelUpdate) -> EducationLevel:
        obj = await self.education_levels.get(level_id)
        if not obj:
            raise NotFoundError("Education level not found")
        return await self.education_levels.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_education_level(self, level_id: UUID) -> None:
        obj = await self.education_levels.get(level_id)
        if not obj:
            raise NotFoundError("Education level not found")
        await self.education_levels.delete(obj)

    # ---------- Education Forms ----------
    async def list_education_forms(self) -> list[EducationForm]:
        return await self.education_forms.list(limit=50, order_by=EducationForm.name)

    async def create_education_form(self, payload: EducationFormCreate) -> EducationForm:
        if await self.education_forms.exists(name=payload.name):
            raise ConflictError(f"Education form '{payload.name}' already exists")
        return await self.education_forms.create(**payload.model_dump())

    async def update_education_form(self, form_id: UUID, payload: EducationFormUpdate) -> EducationForm:
        obj = await self.education_forms.get(form_id)
        if not obj:
            raise NotFoundError("Education form not found")
        return await self.education_forms.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_education_form(self, form_id: UUID) -> None:
        obj = await self.education_forms.get(form_id)
        if not obj:
            raise NotFoundError("Education form not found")
        await self.education_forms.delete(obj)

    # ---------- Programs ----------
    async def list_programs(
        self,
        *,
        active_only: bool = True,
        branch_id: UUID | None = None,
        education_level_id: UUID | None = None,
        education_form_id: UUID | None = None,
    ) -> list[Program]:
        return await self.programs.list_filtered(
            active_only=active_only,
            branch_id=branch_id,
            education_level_id=education_level_id,
            education_form_id=education_form_id,
        )

    async def list_programs_expanded(
        self,
        *,
        active_only: bool = True,
        branch_id: UUID | None = None,
    ) -> list[dict]:
        return await self.programs.list_expanded(active_only=active_only, branch_id=branch_id)

    async def get_program(self, program_id: UUID) -> Program:
        obj = await self.programs.get(program_id)
        if not obj:
            raise NotFoundError("Program not found")
        return obj

    async def create_program(self, payload: ProgramCreate) -> Program:
        if not await self.branches.exists(id=payload.branch_id):
            raise NotFoundError("Branch not found")
        if not await self.education_levels.exists(id=payload.education_level_id):
            raise NotFoundError("Education level not found")
        if not await self.education_forms.exists(id=payload.education_form_id):
            raise NotFoundError("Education form not found")
        return await self.programs.create(**payload.model_dump())

    async def update_program(self, program_id: UUID, payload: ProgramUpdate) -> Program:
        obj = await self.get_program(program_id)
        return await self.programs.update(obj, **payload.model_dump(exclude_unset=True))

    async def delete_program(self, program_id: UUID) -> None:
        obj = await self.get_program(program_id)
        await self.programs.delete(obj)
