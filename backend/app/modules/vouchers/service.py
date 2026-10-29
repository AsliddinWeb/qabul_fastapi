"""Vaucher — kontrakt to'loviga chegirma huquqi (faqat o'qishni ko'chirish).

Issued either together with a re-created contract (ContractCreate.with_voucher)
or standalone from the application page. The PDF is rendered on demand from
the snapshot columns, with a QR code pointing at the public PDF URL — scanning
a cancelled voucher shows it stamped "BEKOR QILINGAN".
"""

from __future__ import annotations

import base64
import re
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.enums import AdmissionType, ContractStatus
from app.modules.vouchers.models import VOUCHER_ACTIVE, VOUCHER_CANCELLED, Voucher

logger = get_logger("vouchers")

_HERE = Path(__file__).parent
DEFAULT_PERCENT = 50


def default_valid_until(today: date | None = None) -> date:
    """End of the current academic year (30 June)."""
    today = today or date.today()
    return date(today.year + 1 if today.month >= 7 else today.year, 6, 30)


def format_number(n: int) -> str:
    return f"{n:04d}"


@lru_cache(maxsize=1)
def _template() -> str:
    return (_HERE / "template.html").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _logo_src() -> str:
    data = (_HERE / "assets" / "logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def public_pdf_url(voucher_id: UUID, base_url: str | None) -> str:
    base = (base_url or settings.public_base_url or "").rstrip("/")
    path = f"/api/v1/vouchers/public/{voucher_id}/pdf"
    return f"{base}{path}" if base else path


def render_voucher_pdf(v: Voucher, *, base_url: str | None) -> bytes:
    """CPU-bound (WeasyPrint) — call via run_in_threadpool from async code."""
    from app.integrations.pdf.generator import render_html, render_pdf
    from app.modules.contracts.service import _make_qr_data_uri

    html = render_html(_template(), {
        "number": format_number(v.voucher_number),
        "percent": v.discount_percent,
        "full_name": v.student_full_name,
        "program": v.program_name,
        "valid_until": v.valid_until.strftime("%d.%m.%Y"),
        "logo_src": _logo_src(),
        "qr_src": _make_qr_data_uri(public_pdf_url(v.id, base_url)),
        "cancelled": v.status == VOUCHER_CANCELLED,
        "fonts": (_HERE / "assets" / "fonts").as_uri(),
    })
    return render_pdf(html)


def pdf_filename(v: Voucher) -> str:
    name = v.student_full_name.replace("'", "").replace("`", "").upper()
    parts = name.split()[:2]
    slug = re.sub(r"[^\w\-]", "", "-".join(parts), flags=re.UNICODE)
    return f"VAUCHER-{format_number(v.voucher_number)}" + (f"-{slug}" if slug else "") + ".pdf"


class VoucherService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, voucher_id: UUID) -> Voucher:
        v = await self.session.get(Voucher, voucher_id)
        if not v:
            raise NotFoundError("Vaucher topilmadi")
        return v

    async def list_for_application(self, application_id: UUID) -> list[Voucher]:
        rows = await self.session.scalars(
            select(Voucher)
            .where(Voucher.application_id == application_id)
            .order_by(Voucher.created_at.desc())
        )
        return list(rows)

    async def issue(
        self,
        application_id: UUID,
        *,
        contract_id: UUID | None,
        valid_until: date | None,
        actor_id: UUID | None,
        replace_active: bool = False,
    ) -> Voucher:
        from app.modules.applicants.models import Applicant
        from app.modules.applications.models import Application
        from app.modules.programs.models import Program

        app = await self.session.get(Application, application_id)
        if not app:
            raise NotFoundError("Ariza topilmadi")
        if app.admission_type != AdmissionType.TRANSFER:
            raise ValidationError("Vaucher faqat o'qishni ko'chirish arizalariga beriladi")

        active = await self.session.scalar(
            select(Voucher).where(
                Voucher.application_id == application_id, Voucher.status == VOUCHER_ACTIVE,
            )
        )
        if active:
            if not replace_active:
                raise ConflictError("Bu arizada faol vaucher allaqachon bor")
            self._mark_cancelled(active, actor_id, "Yangi shartnoma bilan qayta berildi")
            await self.session.flush()

        applicant = await self.session.get(Applicant, app.applicant_id)
        program = await self.session.get(Program, app.program_id)
        full_name = " ".join(
            x for x in (applicant.last_name, applicant.first_name, applicant.other_name) if x
        ).strip() if applicant else ""

        number = await self.session.scalar(text("SELECT nextval('voucher_number_seq')"))
        v = Voucher(
            voucher_number=int(number),
            application_id=application_id,
            contract_id=contract_id,
            discount_percent=DEFAULT_PERCENT,
            student_full_name=full_name or "—",
            program_name=(program.name if program else "") or "—",
            valid_until=valid_until or default_valid_until(),
            status=VOUCHER_ACTIVE,
            created_by_id=actor_id,
        )
        self.session.add(v)
        await self.session.flush()
        return v

    async def issue_standalone(
        self, application_id: UUID, *, valid_until: date | None, actor_id: UUID | None,
    ) -> Voucher:
        """From the application page: attach to the current active contract."""
        from app.modules.contracts.models import Contract

        contract_id = await self.session.scalar(
            select(Contract.id).where(
                Contract.application_id == application_id,
                Contract.status != ContractStatus.CANCELLED,
            )
        )
        if not contract_id:
            raise ValidationError("Vaucher berish uchun arizada faol shartnoma bo'lishi kerak")
        return await self.issue(
            application_id, contract_id=contract_id, valid_until=valid_until, actor_id=actor_id,
        )

    @staticmethod
    def _mark_cancelled(v: Voucher, actor_id: UUID | None, reason: str | None) -> None:
        v.status = VOUCHER_CANCELLED
        v.cancelled_at = datetime.now(timezone.utc)
        v.cancelled_by_id = actor_id
        if reason:
            v.cancelled_reason = reason[:1000]

    async def cancel(self, voucher_id: UUID, *, actor_id: UUID | None, reason: str | None) -> Voucher:
        v = await self.get(voucher_id)
        if v.status == VOUCHER_CANCELLED:
            raise ValidationError("Vaucher allaqachon bekor qilingan")
        self._mark_cancelled(v, actor_id, reason)
        await self.session.flush()
        return v

    async def cancel_for_contract(self, contract_id: UUID, *, actor_id: UUID | None, reason: str) -> int:
        rows = list(await self.session.scalars(
            select(Voucher).where(Voucher.contract_id == contract_id, Voucher.status == VOUCHER_ACTIVE)
        ))
        for v in rows:
            self._mark_cancelled(v, actor_id, reason)
        if rows:
            await self.session.flush()
        return len(rows)
