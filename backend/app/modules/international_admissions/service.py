"""International applications — service layer.

Holds the stage transitions and the public-form submission glue.
The router handles HTTP-shaped validation (rate limit, honeypot,
file fields); this layer assumes inputs are clean.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.international_admissions.models import InternationalApplication
from app.modules.international_admissions.repository import (
    InternationalApplicationRepository,
)


MAX_STAGE = 5


class InternationalAdmissionsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = InternationalApplicationRepository(session)

    # ---- Public submission ----
    async def submit(
        self,
        *,
        full_name: str,
        country: str,
        passport_number: str,
        birth_date,
        phone: str,
        email: str,
        program: str,
        faculty_code: str,
        faculty_text: str,
        language: str | None,
        passport_file_id: UUID | None,
        diploma_file_id: UUID | None,
        photo_file_id: UUID | None,
        submitter_ip: str | None,
        submitter_user_agent: str | None,
    ) -> InternationalApplication:
        # Duplicate guard — same passport submitting twice within 24h
        # is almost always either a misclick or a bot. Real applicants
        # who genuinely want to fix something will contact the office.
        if await self.repo.has_recent_duplicate(
            passport_number=passport_number, full_name=full_name,
        ):
            raise ConflictError(
                "Bu pasport raqami bilan oxirgi 24 soat ichida ariza topshirilgan. "
                "Iltimos, qabul bo'limi bilan bog'laning."
            )

        # Normalise phone — strip spaces / dashes / parentheses so the
        # value we store is always a plain string of digits and a
        # leading +.
        phone = "".join(c for c in phone if c.isdigit() or c == "+").strip()

        ref = await self.repo.next_ref_number()
        return await self.repo.create(
            ref_number=ref,
            full_name=full_name.strip(),
            country=country.strip(),
            passport_number=passport_number.strip().upper(),
            birth_date=birth_date,
            phone=phone,
            email=email.strip().lower(),
            program=program.strip(),
            faculty_code=faculty_code.strip(),
            faculty_text=faculty_text.strip(),
            language=language,
            passport_file_id=passport_file_id,
            diploma_file_id=diploma_file_id,
            photo_file_id=photo_file_id,
            stage=0,
            rejected=False,
            submitter_ip=submitter_ip,
            submitter_user_agent=(submitter_user_agent or "")[:500] or None,
        )

    # ---- Staff: list / get / mutate ----
    async def list(self, **filters):
        return await self.repo.list_filtered(**filters)

    async def get(self, app_id: UUID) -> InternationalApplication:
        obj = await self.repo.get(app_id)
        if not obj:
            raise NotFoundError("International application not found")
        return obj

    async def advance_stage(self, app_id: UUID, *, direction: str) -> InternationalApplication:
        obj = await self.get(app_id)
        if obj.rejected:
            raise ValidationError("Rejected applications can't change stage")
        if direction == "next":
            if obj.stage >= MAX_STAGE:
                raise ValidationError(f"Already at max stage ({MAX_STAGE})")
            obj.stage += 1
        elif direction == "back":
            if obj.stage <= 0:
                raise ValidationError("Already at stage 0")
            obj.stage -= 1
        await self.session.flush()
        return obj

    async def reject(self, app_id: UUID, *, reason: str | None) -> InternationalApplication:
        obj = await self.get(app_id)
        obj.rejected = True
        obj.rejection_reason = (reason or "").strip() or None
        await self.session.flush()
        return obj

    async def unreject(self, app_id: UUID) -> InternationalApplication:
        obj = await self.get(app_id)
        obj.rejected = False
        obj.rejection_reason = None
        await self.session.flush()
        return obj

    async def update_notes(self, app_id: UUID, *, notes: str | None) -> InternationalApplication:
        obj = await self.get(app_id)
        obj.notes = (notes or "").strip() or None
        await self.session.flush()
        return obj

    async def delete(self, app_id: UUID) -> None:
        obj = await self.get(app_id)
        await self.session.delete(obj)
        await self.session.flush()

    async def stage_counts(self) -> dict[str, int]:
        return await self.repo.stage_counts()
