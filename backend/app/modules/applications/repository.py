from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.core.repository import BaseRepository
from app.db.enums import AdmissionType, ApplicationStatus
from app.modules.applicants.models import Applicant
from app.modules.applications.models import Application, ApplicationStatusHistory
from app.modules.programs.models import Branch, EducationForm, EducationLevel, Program


class ApplicationRepository(BaseRepository[Application]):
    model = Application

    async def get_by_number(self, number: str) -> Application | None:
        return await self.get_by(application_number=number)

    async def status_counts(self) -> dict[str, int]:
        """Return count of applications per status for the dashboard stats bar."""
        stmt = select(Application.status, func.count(Application.id)).group_by(Application.status)
        rows = (await self.session.execute(stmt)).all()
        out = {s.value: 0 for s in ApplicationStatus}
        out["total"] = 0
        for status, count in rows:
            key = status.value if hasattr(status, "value") else str(status)
            out[key] = count
            out["total"] += count
        return out

    async def monthly_trend(self, months: int = 12) -> list[dict]:
        """Return application counts grouped by (year, month) for the last `months` months,
        broken down by status. Used by the dashboard trend chart."""
        stmt = (
            select(
                func.date_trunc("month", Application.created_at).label("bucket"),
                Application.status,
                func.count(Application.id).label("cnt"),
            )
            .group_by("bucket", Application.status)
            .order_by("bucket")
        )
        rows = (await self.session.execute(stmt)).all()

        # Build a dict bucket_iso -> counts
        per_bucket: dict[str, dict[str, int]] = {}
        for bucket, status, cnt in rows:
            if not bucket:
                continue
            key = bucket.strftime("%Y-%m-01")
            d = per_bucket.setdefault(key, {"topshirildi": 0, "korib_chiqilmoqda": 0, "qabul_qilindi": 0, "rad_etildi": 0, "total": 0})
            sk = status.value if hasattr(status, "value") else str(status)
            d[sk] = d.get(sk, 0) + cnt
            d["total"] += cnt

        # Pad with empty buckets so the frontend always receives `months` rows
        from datetime import date, timedelta
        today = date.today().replace(day=1)
        result: list[dict] = []
        for i in range(months - 1, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            bk = date(year, month, 1).strftime("%Y-%m-01")
            data = per_bucket.get(bk) or {"topshirildi": 0, "korib_chiqilmoqda": 0, "qabul_qilindi": 0, "rad_etildi": 0, "total": 0}
            result.append({"month": bk, **data})
        return result

    async def list_for_applicant(self, applicant_id: UUID) -> list[Application]:
        stmt = (
            select(Application)
            .where(Application.applicant_id == applicant_id)
            .order_by(Application.created_at.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def list_filtered(
        self,
        *,
        status: ApplicationStatus | None = None,
        admission_type: AdmissionType | None = None,
        applicant_id: UUID | None = None,
        program_id: UUID | None = None,
        branch_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        stmt = select(Application)
        count_stmt = select(func.count(Application.id))

        for col, val in (
            (Application.status, status),
            (Application.admission_type, admission_type),
            (Application.applicant_id, applicant_id),
            (Application.program_id, program_id),
            (Application.branch_id, branch_id),
        ):
            if val is not None:
                stmt = stmt.where(col == val)
                count_stmt = count_stmt.where(col == val)

        stmt = stmt.order_by(Application.created_at.desc()).limit(limit).offset(offset)

        rows = list((await self.session.scalars(stmt)).all())
        total = await self.session.scalar(count_stmt) or 0
        return rows, total

    async def detailed_for_applicant(self, applicant_id: UUID) -> list[dict]:
        return await self._detailed_query(Application.applicant_id == applicant_id)

    async def list_detailed(
        self,
        *,
        status: ApplicationStatus | None = None,
        admission_type: AdmissionType | None = None,
        program_id: UUID | None = None,
        branch_id: UUID | None = None,
        education_level_id: UUID | None = None,
        education_form_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        clauses = []
        if status is not None:
            clauses.append(Application.status == status)
        if admission_type is not None:
            clauses.append(Application.admission_type == admission_type)
        if program_id is not None:
            clauses.append(Application.program_id == program_id)
        if branch_id is not None:
            clauses.append(Application.branch_id == branch_id)
        if education_level_id is not None:
            clauses.append(Application.education_level_id == education_level_id)
        if education_form_id is not None:
            clauses.append(Application.education_form_id == education_form_id)

        rows = await self._detailed_query(*clauses, limit=limit, offset=offset)

        count_stmt = select(func.count(Application.id))
        for c in clauses:
            count_stmt = count_stmt.where(c)
        total = await self.session.scalar(count_stmt) or 0
        return rows, total

    async def _detailed_query(self, *where_clauses, limit: int | None = None, offset: int = 0) -> list[dict]:
        stmt = (
            select(
                Application,
                Program.name.label("program_name"),
                Program.code.label("program_code"),
                Branch.name.label("branch_name"),
                EducationLevel.name.label("education_level_name"),
                EducationForm.name.label("education_form_name"),
                Applicant.first_name.label("a_first_name"),
                Applicant.last_name.label("a_last_name"),
                Applicant.other_name.label("a_other_name"),
            )
            .join(Program, Application.program_id == Program.id)
            .join(Branch, Application.branch_id == Branch.id)
            .join(EducationLevel, Application.education_level_id == EducationLevel.id)
            .join(EducationForm, Application.education_form_id == EducationForm.id)
            .join(Applicant, Application.applicant_id == Applicant.id)
        )
        for c in where_clauses:
            stmt = stmt.where(c)
        stmt = stmt.order_by(Application.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).all()
        result = []
        for app, p_name, p_code, b_name, lvl_name, form_name, a_first, a_last, a_other in rows:
            data = {**app.__dict__}
            data.pop("_sa_instance_state", None)
            full_name = " ".join(filter(None, [a_last, a_first, a_other])).strip() or None
            data.update({
                "program_name": p_name,
                "program_code": p_code,
                "branch_name": b_name,
                "education_level_name": lvl_name,
                "education_form_name": form_name,
                "applicant_full_name": full_name,
            })
            result.append(data)
        return result


class ApplicationStatusHistoryRepository(BaseRepository[ApplicationStatusHistory]):
    model = ApplicationStatusHistory

    async def list_for_application(self, application_id: UUID) -> list[ApplicationStatusHistory]:
        stmt = (
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == application_id)
            .order_by(ApplicationStatusHistory.created_at.asc())
        )
        return list((await self.session.scalars(stmt)).all())
