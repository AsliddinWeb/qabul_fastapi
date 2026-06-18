from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from app.core.repository import BaseRepository
from app.modules.applicants.models import (
    Applicant,
    Course,
    Diplom,
    EducationType,
    InstitutionType,
    TransferDiplom,
)
from app.modules.users.models import User


class ApplicantRepository(BaseRepository[Applicant]):
    model = Applicant

    async def get_by_user_id(self, user_id: UUID) -> Applicant | None:
        return await self.get_by(user_id=user_id)

    async def get_by_pinfl(self, pinfl: str) -> Applicant | None:
        return await self.get_by(pinfl=pinfl)

    async def list_filtered(
        self,
        *,
        region_id: UUID | None = None,
        registered_by_id: UUID | None = None,
        contact_status=None,
        has_contract: bool | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List applicants enriched with login phone + contract status.

        Returns dicts (not raw Applicant ORM rows) carrying every
        Applicant column PLUS:
          - user_phone   — the User.phone the applicant logs in with
          - contract_status — 'signed' | 'draft' | None
              The applicant's "highest-priority" non-cancelled contract
              status; lets the table show a green / amber / empty chip
              without an N+1 fetch.

        SIGNED > DRAFT > none. CANCELLED is ignored.
        """
        # Local imports to keep this repo importable without pulling
        # half the domain at module-import time.
        from app.modules.applications.models import Application
        from app.modules.contracts.models import Contract
        from app.db.enums import ContractStatus
        from sqlalchemy import exists as _exists

        signed_exists = _exists(
            select(Contract.id)
            .join(Application, Application.id == Contract.application_id)
            .where(
                Application.applicant_id == Applicant.id,
                Contract.status == ContractStatus.SIGNED,
            )
        ).label("has_signed")
        draft_exists = _exists(
            select(Contract.id)
            .join(Application, Application.id == Contract.application_id)
            .where(
                Application.applicant_id == Applicant.id,
                Contract.status == ContractStatus.DRAFT,
            )
        ).label("has_draft")

        # Always outer-join User — we need User.phone in every row to
        # show "asosiy raqam" in the table. 1:1 relation so the join
        # doesn't change row counts.
        stmt = (
            select(Applicant, User.phone.label("user_phone"), signed_exists, draft_exists)
            .outerjoin(User, Applicant.user_id == User.id)
        )
        count_stmt = (
            select(func.count(Applicant.id))
            .select_from(Applicant)
            .outerjoin(User, Applicant.user_id == User.id)
        )

        if region_id is not None:
            stmt = stmt.where(Applicant.region_id == region_id)
            count_stmt = count_stmt.where(Applicant.region_id == region_id)
        if registered_by_id is not None:
            stmt = stmt.where(Applicant.registered_by_id == registered_by_id)
            count_stmt = count_stmt.where(Applicant.registered_by_id == registered_by_id)
        if contact_status is not None:
            stmt = stmt.where(Applicant.contact_status == contact_status)
            count_stmt = count_stmt.where(Applicant.contact_status == contact_status)
        if has_contract is not None:
            # EXISTS subquery — applicant has a non-cancelled contract through
            # any of their applications. Index on contracts.application_id +
            # applications.applicant_id makes this O(log n) per row.
            contract_exists = _exists(
                select(Contract.id)
                .join(Application, Application.id == Contract.application_id)
                .where(
                    Application.applicant_id == Applicant.id,
                    Contract.status != ContractStatus.CANCELLED,
                )
            )
            cond = contract_exists if has_contract else ~contract_exists
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        if search:
            like = f"%{search}%"
            # If the search looks phone-like, also build a digits-only
            # pattern so "94 202 55 11" matches "+998942025511" stored
            # on User.phone — operators routinely paste formatted phones.
            digits = "".join(c for c in search if c.isdigit())
            phone_like = f"%{digits}%" if digits else None

            or_terms = [
                Applicant.first_name.ilike(like),
                Applicant.last_name.ilike(like),
                Applicant.other_name.ilike(like),
                Applicant.passport_series.ilike(like),
                Applicant.pinfl.ilike(like),
                Applicant.additional_phone.ilike(like),
            ]
            if phone_like:
                or_terms.extend([
                    User.phone.ilike(phone_like),
                    Applicant.additional_phone.ilike(phone_like),
                ])
            cond = or_(*or_terms)
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(Applicant.created_at.desc()).limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).all()
        result: list[dict] = []
        for app, phone, has_signed, has_draft in rows:
            data = {**app.__dict__}
            data.pop("_sa_instance_state", None)
            data["user_phone"] = phone
            data["contract_status"] = (
                "signed" if has_signed
                else "draft" if has_draft
                else None
            )
            result.append(data)
        total = await self.session.scalar(count_stmt) or 0
        return result, total


class EducationTypeRepository(BaseRepository[EducationType]):
    model = EducationType


class InstitutionTypeRepository(BaseRepository[InstitutionType]):
    model = InstitutionType


class CourseRepository(BaseRepository[Course]):
    model = Course


class DiplomRepository(BaseRepository[Diplom]):
    model = Diplom

    async def get_by_user_id(
        self,
        user_id: UUID,
        *,
        is_for_second_specialization: bool = False,
    ) -> Diplom | None:
        """Return the diplom for this user's flow.

        The Diplom row is now unique on (user_id, is_for_second_specialization),
        so callers MUST disambiguate. Defaulting to False keeps the legacy
        1-kurs callers behaviour-compatible.
        """
        return await self.get_by(
            user_id=user_id,
            is_for_second_specialization=is_for_second_specialization,
        )

    async def list_filtered(
        self,
        *,
        user_id: UUID | None = None,
        search: str | None = None,
        is_for_second_specialization: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Returns diploms joined with applicant info (last/first/other name, pinfl, passport)."""
        stmt = (
            select(
                Diplom,
                Applicant.last_name.label("a_last_name"),
                Applicant.first_name.label("a_first_name"),
                Applicant.other_name.label("a_other_name"),
                Applicant.pinfl.label("a_pinfl"),
                Applicant.passport_series.label("a_passport_series"),
            )
            .outerjoin(Applicant, Applicant.user_id == Diplom.user_id)
        )
        count_stmt = select(func.count(Diplom.id)).select_from(Diplom).outerjoin(Applicant, Applicant.user_id == Diplom.user_id)
        if user_id is not None:
            stmt = stmt.where(Diplom.user_id == user_id)
            count_stmt = count_stmt.where(Diplom.user_id == user_id)
        if is_for_second_specialization is not None:
            stmt = stmt.where(Diplom.is_for_second_specialization == is_for_second_specialization)
            count_stmt = count_stmt.where(Diplom.is_for_second_specialization == is_for_second_specialization)
        if search:
            like = f"%{search}%"
            cond = or_(
                Diplom.serial_number.ilike(like),
                Diplom.university_name.ilike(like),
                Applicant.last_name.ilike(like),
                Applicant.first_name.ilike(like),
                Applicant.pinfl.ilike(like),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        stmt = stmt.order_by(Diplom.created_at.desc()).limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).all()
        result: list[dict] = []
        for d, a_last, a_first, a_other, a_pinfl, a_passport in rows:
            data = {**d.__dict__}
            data.pop("_sa_instance_state", None)
            data["applicant_last_name"] = a_last
            data["applicant_first_name"] = a_first
            data["applicant_other_name"] = a_other
            data["applicant_pinfl"] = a_pinfl
            data["applicant_passport_series"] = a_passport
            result.append(data)
        total = await self.session.scalar(count_stmt) or 0
        return result, total


class TransferDiplomRepository(BaseRepository[TransferDiplom]):
    model = TransferDiplom

    async def get_by_user_id(self, user_id: UUID) -> TransferDiplom | None:
        return await self.get_by(user_id=user_id)

    async def list_filtered(
        self,
        *,
        user_id: UUID | None = None,
        country_id: UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Returns transfer diploms joined with applicant info."""
        stmt = (
            select(
                TransferDiplom,
                Applicant.last_name.label("a_last_name"),
                Applicant.first_name.label("a_first_name"),
                Applicant.other_name.label("a_other_name"),
                Applicant.pinfl.label("a_pinfl"),
                Applicant.passport_series.label("a_passport_series"),
            )
            .outerjoin(Applicant, Applicant.user_id == TransferDiplom.user_id)
        )
        count_stmt = select(func.count(TransferDiplom.id)).select_from(TransferDiplom).outerjoin(Applicant, Applicant.user_id == TransferDiplom.user_id)
        if user_id is not None:
            stmt = stmt.where(TransferDiplom.user_id == user_id)
            count_stmt = count_stmt.where(TransferDiplom.user_id == user_id)
        if country_id is not None:
            stmt = stmt.where(TransferDiplom.country_id == country_id)
            count_stmt = count_stmt.where(TransferDiplom.country_id == country_id)
        if search:
            like = f"%{search}%"
            cond = or_(
                TransferDiplom.university_name.ilike(like),
                Applicant.last_name.ilike(like),
                Applicant.first_name.ilike(like),
                Applicant.pinfl.ilike(like),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        stmt = stmt.order_by(TransferDiplom.created_at.desc()).limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).all()
        result: list[dict] = []
        for d, a_last, a_first, a_other, a_pinfl, a_passport in rows:
            data = {**d.__dict__}
            data.pop("_sa_instance_state", None)
            data["applicant_last_name"] = a_last
            data["applicant_first_name"] = a_first
            data["applicant_other_name"] = a_other
            data["applicant_pinfl"] = a_pinfl
            data["applicant_passport_series"] = a_passport
            result.append(data)
        total = await self.session.scalar(count_stmt) or 0
        return result, total
