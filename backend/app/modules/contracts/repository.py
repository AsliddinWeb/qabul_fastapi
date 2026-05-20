from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from app.core.repository import BaseRepository
from app.db.enums import ContractStatus, ContractType
from app.modules.contracts.models import Contract, ContractParty, ContractSettings, ContractTemplate


class ContractTemplateRepository(BaseRepository[ContractTemplate]):
    model = ContractTemplate

    async def list_active(self) -> list[ContractTemplate]:
        stmt = (
            select(ContractTemplate)
            .where(ContractTemplate.is_active.is_(True))
            .order_by(ContractTemplate.name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active(self) -> ContractTemplate | None:
        stmt = (
            select(ContractTemplate)
            .where(ContractTemplate.is_active.is_(True))
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()


class ContractSettingsRepository(BaseRepository[ContractSettings]):
    model = ContractSettings

    async def get_singleton(self) -> ContractSettings | None:
        stmt = select(ContractSettings).limit(1)
        return (await self.session.scalars(stmt)).first()


class ContractRepository(BaseRepository[Contract]):
    model = Contract

    async def get_by_application(self, application_id: UUID) -> Contract | None:
        return await self.get_by(application_id=application_id)

    async def get_active_by_application(self, application_id: UUID) -> Contract | None:
        from sqlalchemy import select
        stmt = (
            select(Contract)
            .where(
                Contract.application_id == application_id,
                Contract.status != ContractStatus.CANCELLED,
            )
            .order_by(Contract.created_at.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_number(self, contract_number: str) -> Contract | None:
        return await self.get_by(contract_number=contract_number)

    async def list_filtered(
        self,
        *,
        status: ContractStatus | None = None,
        type: ContractType | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Contract], int]:
        stmt = select(Contract)
        count_stmt = select(func.count(Contract.id))
        if status is not None:
            stmt = stmt.where(Contract.status == status)
            count_stmt = count_stmt.where(Contract.status == status)
        if type is not None:
            stmt = stmt.where(Contract.type == type)
            count_stmt = count_stmt.where(Contract.type == type)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(Contract.contract_number.ilike(like))
            count_stmt = count_stmt.where(Contract.contract_number.ilike(like))
        stmt = stmt.order_by(Contract.created_at.desc()).limit(limit).offset(offset)
        rows = list((await self.session.scalars(stmt)).all())
        total = await self.session.scalar(count_stmt) or 0
        return rows, total

    async def list_detailed(
        self,
        *,
        status: ContractStatus | None = None,
        type: ContractType | None = None,
        payment_status: str | None = None,  # "paid" | "partial" | "unpaid"
        branch_id: UUID | None = None,
        created_by_id: UUID | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Contracts joined with applicant + branch for the accountant list.

        Returns dicts (not ORM models) including:
          - all Contract fields
          - applicant_full_name, branch_name, program_name
          - balance (computed)
        """
        # Imports here to avoid pulling other modules at import time.
        from app.modules.applicants.models import Applicant
        from app.modules.applications.models import Application
        from app.modules.programs.models import Branch, Program

        balance_expr = (Contract.total_amount - Contract.paid_amount).label("balance")
        stmt = (
            select(
                Contract,
                Applicant.last_name,
                Applicant.first_name,
                Applicant.other_name,
                Branch.name.label("branch_name"),
                Program.name.label("program_name"),
                balance_expr,
            )
            .join(Application, Application.id == Contract.application_id)
            .join(Applicant, Applicant.id == Application.applicant_id)
            .join(Branch, Branch.id == Application.branch_id)
            .join(Program, Program.id == Application.program_id)
        )
        count_stmt = (
            select(func.count(Contract.id))
            .select_from(Contract)
            .join(Application, Application.id == Contract.application_id)
            .join(Applicant, Applicant.id == Application.applicant_id)
            .join(Branch, Branch.id == Application.branch_id)
        )

        clauses = []
        if status is not None:
            clauses.append(Contract.status == status)
        if type is not None:
            clauses.append(Contract.type == type)
        if branch_id is not None:
            clauses.append(Application.branch_id == branch_id)
        if created_by_id is not None:
            clauses.append(Contract.created_by_id == created_by_id)
        if payment_status == "paid":
            clauses.append(Contract.paid_amount >= Contract.total_amount)
        elif payment_status == "partial":
            clauses.append(Contract.paid_amount > 0)
            clauses.append(Contract.paid_amount < Contract.total_amount)
        elif payment_status == "unpaid":
            clauses.append(Contract.paid_amount == 0)
        if search:
            like = f"%{search}%"
            clauses.append(or_(
                Contract.contract_number.ilike(like),
                Applicant.last_name.ilike(like),
                Applicant.first_name.ilike(like),
                Applicant.other_name.ilike(like),
            ))

        for c in clauses:
            stmt = stmt.where(c)
            count_stmt = count_stmt.where(c)

        stmt = stmt.order_by(Contract.created_at.desc()).limit(limit).offset(offset)
        rows = (await self.session.execute(stmt)).all()

        items: list[dict] = []
        for c, last, first, other, branch_name, program_name, balance in rows:
            d = {
                "id": c.id,
                "contract_number": c.contract_number,
                "application_id": c.application_id,
                "template_id": c.template_id,
                "type": c.type,
                "total_amount": c.total_amount,
                "paid_amount": c.paid_amount,
                "currency": c.currency,
                "status": c.status,
                "signed_at": c.signed_at,
                "pdf_file_id": c.pdf_file_id,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "applicant_full_name": " ".join(filter(None, [last, first, other])).strip() or None,
                "branch_name": branch_name,
                "program_name": program_name,
                "balance": balance,
            }
            items.append(d)

        total = await self.session.scalar(count_stmt) or 0
        return items, total


class ContractPartyRepository(BaseRepository[ContractParty]):
    model = ContractParty

    async def list_for_contract(self, contract_id: UUID) -> list[ContractParty]:
        stmt = (
            select(ContractParty)
            .where(ContractParty.contract_id == contract_id)
            .order_by(ContractParty.party_role)
        )
        return list((await self.session.scalars(stmt)).all())
