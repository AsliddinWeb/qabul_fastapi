from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.programs.models import Branch, EducationForm, EducationLevel, Program


class BranchRepository(BaseRepository[Branch]):
    model = Branch


class EducationLevelRepository(BaseRepository[EducationLevel]):
    model = EducationLevel


class EducationFormRepository(BaseRepository[EducationForm]):
    model = EducationForm


class ProgramRepository(BaseRepository[Program]):
    model = Program

    async def list_filtered(
        self,
        *,
        active_only: bool = True,
        branch_id: UUID | None = None,
        education_level_id: UUID | None = None,
        education_form_id: UUID | None = None,
    ) -> list[Program]:
        stmt = select(Program)
        if active_only:
            stmt = stmt.where(Program.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(Program.branch_id == branch_id)
        if education_level_id:
            stmt = stmt.where(Program.education_level_id == education_level_id)
        if education_form_id:
            stmt = stmt.where(Program.education_form_id == education_form_id)
        stmt = stmt.order_by(Program.name)
        return list((await self.session.scalars(stmt)).all())

    async def list_expanded(
        self,
        *,
        active_only: bool = True,
        branch_id: UUID | None = None,
    ) -> list[dict]:
        stmt = (
            select(
                Program,
                Branch.name.label("branch_name"),
                EducationLevel.name.label("education_level_name"),
                EducationForm.name.label("education_form_name"),
            )
            .join(Branch, Program.branch_id == Branch.id)
            .join(EducationLevel, Program.education_level_id == EducationLevel.id)
            .join(EducationForm, Program.education_form_id == EducationForm.id)
        )
        if active_only:
            stmt = stmt.where(Program.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(Program.branch_id == branch_id)
        stmt = stmt.order_by(Branch.name, Program.name)

        rows = (await self.session.execute(stmt)).all()
        result: list[dict] = []
        for prog, b_name, lvl_name, form_name in rows:
            data = {
                **prog.__dict__,
                "branch_name": b_name,
                "education_level_name": lvl_name,
                "education_form_name": form_name,
            }
            data.pop("_sa_instance_state", None)
            result.append(data)
        return result
