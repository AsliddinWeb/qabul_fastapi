"""International applications — repository.

Thin layer over the model. Filtering is light because the staff list
page is a 6-column Kanban — group-by-stage happens in the route.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from app.core.repository import BaseRepository
from app.modules.international_admissions.models import InternationalApplication


class InternationalApplicationRepository(BaseRepository[InternationalApplication]):
    model = InternationalApplication

    async def get_by_ref(self, ref_number: str) -> InternationalApplication | None:
        return await self.get_by(ref_number=ref_number)

    async def list_filtered(
        self,
        *,
        stage: int | None = None,
        country: str | None = None,
        rejected: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[InternationalApplication], int]:
        stmt = select(InternationalApplication)
        count_stmt = select(func.count(InternationalApplication.id))

        if stage is not None:
            stmt = stmt.where(InternationalApplication.stage == stage)
            count_stmt = count_stmt.where(InternationalApplication.stage == stage)
        if country is not None:
            stmt = stmt.where(InternationalApplication.country == country)
            count_stmt = count_stmt.where(InternationalApplication.country == country)
        if rejected is not None:
            stmt = stmt.where(InternationalApplication.rejected.is_(rejected))
            count_stmt = count_stmt.where(InternationalApplication.rejected.is_(rejected))
        if search:
            like = f"%{search.strip()}%"
            cond = or_(
                InternationalApplication.full_name.ilike(like),
                InternationalApplication.country.ilike(like),
                InternationalApplication.passport_number.ilike(like),
                InternationalApplication.email.ilike(like),
                InternationalApplication.phone.ilike(like),
                InternationalApplication.ref_number.ilike(like),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = (
            stmt.order_by(InternationalApplication.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.scalars(stmt)).all())
        total = await self.session.scalar(count_stmt) or 0
        return rows, total

    async def stage_counts(self) -> dict[str, int]:
        """One count per stage (0..5) + total. Drives the dashboard
        KPI cards above the Kanban board."""
        stmt = (
            select(InternationalApplication.stage, func.count(InternationalApplication.id))
            .where(InternationalApplication.rejected.is_(False))
            .group_by(InternationalApplication.stage)
        )
        rows = (await self.session.execute(stmt)).all()
        out = {f"stage_{i}": 0 for i in range(6)}
        out["total"] = 0
        for stage, count in rows:
            out[f"stage_{stage}"] = count
            out["total"] += count
        # Rejected pile separately so staff can spot fraud waves.
        rejected_n = await self.session.scalar(
            select(func.count(InternationalApplication.id))
            .where(InternationalApplication.rejected.is_(True))
        ) or 0
        out["rejected"] = rejected_n
        return out

    async def has_recent_duplicate(
        self,
        *,
        passport_number: str,
        full_name: str | None = None,
        within_hours: int = 24,
    ) -> bool:
        """Anti-spam: same passport submitted in the last `within_hours`.

        Catches the dumb "resubmit same data" attack pattern. Genuine
        re-applications happen weeks later (an applicant fixes their
        document) so a 24h window is wide enough without blocking
        legitimate retries.
        """
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)
        cond = [
            InternationalApplication.passport_number == passport_number,
            InternationalApplication.created_at >= cutoff,
        ]
        if full_name:
            cond.append(InternationalApplication.full_name.ilike(full_name))
        n = await self.session.scalar(
            select(func.count(InternationalApplication.id)).where(*cond)
        ) or 0
        return n > 0

    async def next_ref_number(self) -> str:
        """Generate the next "XIU-INT-YYYY-NNN" reference number.

        Counts ALL rows ever submitted (including rejected) so duplicate
        refs are impossible even after a flood of spam was wiped.
        Year-scoped so the suffix resets each January.
        """
        from datetime import datetime, timezone
        year = datetime.now(timezone.utc).year
        n = await self.session.scalar(
            select(func.count(InternationalApplication.id)).where(
                func.extract("year", InternationalApplication.created_at) == year,
            )
        ) or 0
        return f"XIU-INT-{year}-{(n + 1):03d}"
