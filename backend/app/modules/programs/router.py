from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_permission
from app.core.permissions import Permission
from app.modules.programs.schemas import (
    BranchCreate,
    BranchRead,
    BranchUpdate,
    EducationFormCreate,
    EducationFormRead,
    EducationFormUpdate,
    EducationLevelCreate,
    EducationLevelRead,
    EducationLevelUpdate,
    ProgramCreate,
    ProgramExpanded,
    ProgramRead,
    ProgramUpdate,
)
from app.modules.programs.service import ProgramsService

router = APIRouter()
require_write = require_permission(Permission.PROGRAMS_WRITE)


def _service(session: AsyncSession = Depends(get_db)) -> ProgramsService:
    return ProgramsService(session)


# ---------- Branches ----------
@router.get("/branches", response_model=list[BranchRead])
async def list_branches(
    active_only: bool = True,
    svc: ProgramsService = Depends(_service),
) -> list[BranchRead]:
    rows = await svc.list_branches(active_only=active_only)
    return [BranchRead.model_validate(r) for r in rows]


@router.post(
    "/branches",
    response_model=BranchRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
async def create_branch(payload: BranchCreate, svc: ProgramsService = Depends(_service)) -> BranchRead:
    obj = await svc.create_branch(payload)
    await svc.session.commit()
    return BranchRead.model_validate(obj)


@router.patch(
    "/branches/{branch_id}",
    response_model=BranchRead,
    dependencies=[Depends(require_write)],
)
async def update_branch(
    branch_id: UUID,
    payload: BranchUpdate,
    svc: ProgramsService = Depends(_service),
) -> BranchRead:
    obj = await svc.update_branch(branch_id, payload)
    await svc.session.commit()
    return BranchRead.model_validate(obj)


@router.delete(
    "/branches/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write)],
)
async def delete_branch(branch_id: UUID, svc: ProgramsService = Depends(_service)) -> None:
    await svc.delete_branch(branch_id)
    await svc.session.commit()


# ---------- Education Levels ----------
@router.get("/education-levels", response_model=list[EducationLevelRead])
async def list_education_levels(svc: ProgramsService = Depends(_service)) -> list[EducationLevelRead]:
    rows = await svc.list_education_levels()
    return [EducationLevelRead.model_validate(r) for r in rows]


@router.post(
    "/education-levels",
    response_model=EducationLevelRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
async def create_education_level(
    payload: EducationLevelCreate,
    svc: ProgramsService = Depends(_service),
) -> EducationLevelRead:
    obj = await svc.create_education_level(payload)
    await svc.session.commit()
    return EducationLevelRead.model_validate(obj)


@router.patch(
    "/education-levels/{level_id}",
    response_model=EducationLevelRead,
    dependencies=[Depends(require_write)],
)
async def update_education_level(
    level_id: UUID,
    payload: EducationLevelUpdate,
    svc: ProgramsService = Depends(_service),
) -> EducationLevelRead:
    obj = await svc.update_education_level(level_id, payload)
    await svc.session.commit()
    return EducationLevelRead.model_validate(obj)


@router.delete(
    "/education-levels/{level_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write)],
)
async def delete_education_level(level_id: UUID, svc: ProgramsService = Depends(_service)) -> None:
    await svc.delete_education_level(level_id)
    await svc.session.commit()


# ---------- Education Forms ----------
@router.get("/education-forms", response_model=list[EducationFormRead])
async def list_education_forms(svc: ProgramsService = Depends(_service)) -> list[EducationFormRead]:
    rows = await svc.list_education_forms()
    return [EducationFormRead.model_validate(r) for r in rows]


@router.post(
    "/education-forms",
    response_model=EducationFormRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
async def create_education_form(
    payload: EducationFormCreate,
    svc: ProgramsService = Depends(_service),
) -> EducationFormRead:
    obj = await svc.create_education_form(payload)
    await svc.session.commit()
    return EducationFormRead.model_validate(obj)


@router.patch(
    "/education-forms/{form_id}",
    response_model=EducationFormRead,
    dependencies=[Depends(require_write)],
)
async def update_education_form(
    form_id: UUID,
    payload: EducationFormUpdate,
    svc: ProgramsService = Depends(_service),
) -> EducationFormRead:
    obj = await svc.update_education_form(form_id, payload)
    await svc.session.commit()
    return EducationFormRead.model_validate(obj)


@router.delete(
    "/education-forms/{form_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write)],
)
async def delete_education_form(form_id: UUID, svc: ProgramsService = Depends(_service)) -> None:
    await svc.delete_education_form(form_id)
    await svc.session.commit()


# ---------- Programs ----------
@router.get("/programs", response_model=list[ProgramExpanded])
async def list_programs(
    active_only: bool = True,
    branch_id: UUID | None = Query(default=None),
    svc: ProgramsService = Depends(_service),
) -> list[ProgramExpanded]:
    rows = await svc.list_programs_expanded(active_only=active_only, branch_id=branch_id)
    return [ProgramExpanded.model_validate(r) for r in rows]


@router.get("/programs/{program_id}", response_model=ProgramRead)
async def get_program(program_id: UUID, svc: ProgramsService = Depends(_service)) -> ProgramRead:
    obj = await svc.get_program(program_id)
    return ProgramRead.model_validate(obj)


@router.post(
    "/programs",
    response_model=ProgramRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
async def create_program(payload: ProgramCreate, svc: ProgramsService = Depends(_service)) -> ProgramRead:
    obj = await svc.create_program(payload)
    await svc.session.commit()
    return ProgramRead.model_validate(obj)


@router.patch(
    "/programs/{program_id}",
    response_model=ProgramRead,
    dependencies=[Depends(require_write)],
)
async def update_program(
    program_id: UUID,
    payload: ProgramUpdate,
    svc: ProgramsService = Depends(_service),
) -> ProgramRead:
    obj = await svc.update_program(program_id, payload)
    await svc.session.commit()
    return ProgramRead.model_validate(obj)


@router.delete(
    "/programs/{program_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write)],
)
async def delete_program(program_id: UUID, svc: ProgramsService = Depends(_service)) -> None:
    await svc.delete_program(program_id)
    await svc.session.commit()
