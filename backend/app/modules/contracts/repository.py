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


class ContractPartyRepository(BaseRepository[ContractParty]):
    model = ContractParty

    async def list_for_contract(self, contract_id: UUID) -> list[ContractParty]:
        stmt = (
            select(ContractParty)
            .where(ContractParty.contract_id == contract_id)
            .order_by(ContractParty.party_role)
        )
        return list((await self.session.scalars(stmt)).all())
