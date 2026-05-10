from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.enums import (
    AdmissionType,
    ApplicationStatus,
    ContractStatus,
    ContractType,
    PartyRole,
)
from app.integrations.pdf.generator import render_html, render_pdf
from app.modules.applicants.repository import ApplicantRepository
from app.modules.applications.repository import ApplicationRepository
from app.modules.contracts.models import Contract, ContractParty, ContractSettings, ContractTemplate
from app.modules.contracts.repository import (
    ContractPartyRepository,
    ContractRepository,
    ContractSettingsRepository,
    ContractTemplateRepository,
)
from app.modules.contracts.schemas import (
    ContractCreate,
    ContractSettingsUpdate,
    ContractTemplateCreate,
    ContractTemplateUpdate,
)
from app.modules.files.service import FilesService
from app.modules.programs.repository import BranchRepository, EducationFormRepository, EducationLevelRepository, ProgramRepository

logger = get_logger("contracts")


def _generate_contract_number() -> str:
    year = datetime.now(timezone.utc).year
    return f"C-{year}-{uuid4().hex[:8].upper()}"


class ContractsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.templates = ContractTemplateRepository(session)
        self.contracts = ContractRepository(session)
        self.parties = ContractPartyRepository(session)
        self.settings_repo = ContractSettingsRepository(session)
        self.applications = ApplicationRepository(session)
        self.applicants = ApplicantRepository(session)
        self.programs = ProgramRepository(session)
        self.branches = BranchRepository(session)
        self.education_levels = EducationLevelRepository(session)
        self.education_forms = EducationFormRepository(session)
        self.files = FilesService(session)

    # ---------- Templates ----------
    async def list_templates(self, *, active_only: bool = False) -> list[ContractTemplate]:
        if active_only:
            return await self.templates.list_active()
        return await self.templates.list(limit=200, order_by=ContractTemplate.name)

    async def get_template(self, template_id: UUID) -> ContractTemplate:
        obj = await self.templates.get(template_id)
        if not obj:
            raise NotFoundError("Contract template not found")
        return obj

    async def get_active_template(self) -> ContractTemplate:
        obj = await self.templates.get_active()
        if not obj:
            raise NotFoundError("No active contract template")
        return obj

    async def create_template(self, payload: ContractTemplateCreate) -> ContractTemplate:
        # Single-active rule: if creating an active one, deactivate others.
        if payload.is_active:
            for t in await self.templates.list_active():
                await self.templates.update(t, is_active=False)
        return await self.templates.create(version=1, **payload.model_dump())

    async def update_template(
        self, template_id: UUID, payload: ContractTemplateUpdate
    ) -> ContractTemplate:
        obj = await self.get_template(template_id)
        data = payload.model_dump(exclude_unset=True)
        if data.get("is_active") is True:
            for t in await self.templates.list_active():
                if t.id != obj.id:
                    await self.templates.update(t, is_active=False)
        return await self.templates.update(obj, **data)

    async def activate_template(self, template_id: UUID) -> ContractTemplate:
        obj = await self.get_template(template_id)
        for t in await self.templates.list_active():
            if t.id != obj.id:
                await self.templates.update(t, is_active=False)
        return await self.templates.update(obj, is_active=True)

    async def delete_template(self, template_id: UUID) -> None:
        obj = await self.get_template(template_id)
        await self.templates.delete(obj)

    # ---------- Settings (singleton) ----------
    async def get_settings(self) -> ContractSettings:
        obj = await self.settings_repo.get_singleton()
        if not obj:
            obj = await self.settings_repo.create()
        return obj

    async def update_settings(self, payload: ContractSettingsUpdate) -> ContractSettings:
        obj = await self.get_settings()
        return await self.settings_repo.update(obj, **payload.model_dump(exclude_unset=True))

    # ---------- Contracts (read) ----------
    async def list(self, **filters) -> tuple[list[Contract], int]:
        return await self.contracts.list_filtered(**filters)

    async def list_detailed(self, **filters) -> tuple[list[dict], int]:
        return await self.contracts.list_detailed(**filters)

    async def get(self, contract_id: UUID) -> Contract:
        obj = await self.contracts.get(contract_id)
        if not obj:
            raise NotFoundError("Contract not found")
        return obj

    async def get_parties(self, contract_id: UUID) -> list[ContractParty]:
        await self.get(contract_id)
        return await self.parties.list_for_contract(contract_id)

    async def get_by_application(self, application_id: UUID) -> Contract | None:
        return await self.contracts.get_by_application(application_id)

    # ---------- Create ----------
    async def create_contract(
        self,
        payload: ContractCreate,
        *,
        actor_id: UUID,
        base_url: str | None = None,
    ) -> Contract:
        application = await self.applications.get(payload.application_id)
        if not application:
            raise NotFoundError("Application not found")
        if application.status != ApplicationStatus.ACCEPTED:
            raise ValidationError(
                f"Application must be accepted (current: {application.status.value})"
            )
        existing = await self.contracts.get_active_by_application(application.id)
        if existing:
            raise ConflictError("Contract already exists for this application")

        template = await self.get_template(payload.template_id)
        if not template.is_active:
            raise ValidationError("Template is inactive")

        program = await self.programs.get(application.program_id)
        if not program:
            raise NotFoundError("Program not found")

        applicant = await self.applicants.get(application.applicant_id)
        if not applicant:
            raise NotFoundError("Applicant not found")

        # 3-party contracts require additional party data
        if payload.type == ContractType.THREE_PARTY and payload.additional_party is None:
            raise ValidationError("3-party contract requires additional party data")

        # Tuition fee is stored on Program as String — try to parse for total_amount.
        total_amount = payload.total_amount if payload.total_amount is not None else program.tuition_fee

        contract = await self.contracts.create(
            contract_number=_generate_contract_number(),
            application_id=application.id,
            template_id=template.id,
            type=payload.type,
            total_amount=total_amount,
            currency=payload.currency,
            status=ContractStatus.DRAFT,
            created_by_id=actor_id,
        )

        cfg = await self.get_settings()

        await self.parties.create(
            contract_id=contract.id,
            party_role=PartyRole.UNIVERSITY,
            full_name=cfg.company_name,
            address=cfg.company_address,
        )

        passport_series = applicant.passport_series or ""
        ps = passport_series[:2] if len(passport_series) >= 2 else None
        pn = passport_series[2:] if len(passport_series) > 2 else None

        full_name = " ".join(
            filter(
                None,
                [applicant.last_name, applicant.first_name, applicant.other_name],
            )
        ).strip()

        await self.parties.create(
            contract_id=contract.id,
            party_role=PartyRole.STUDENT,
            full_name=full_name,
            pinfl=applicant.pinfl,
            passport_series=ps,
            passport_number=pn,
            address=applicant.address,
        )

        if payload.additional_party:
            await self.parties.create(
                contract_id=contract.id,
                **payload.additional_party.model_dump(),
            )

        # Render PDF (best-effort)
        if cfg.auto_generate_pdf:
            await self._render_and_attach_pdf(
                contract=contract,
                template=template,
                applicant=applicant,
                application=application,
                program=program,
                actor_id=actor_id,
                base_url=base_url,
            )
        return contract

    async def _render_and_attach_pdf(
        self,
        *,
        contract: Contract,
        template: ContractTemplate,
        applicant,
        application,
        program,
        actor_id: UUID,
        base_url: str | None = None,
    ) -> None:
        body = template.body_three_party if contract.type == ContractType.THREE_PARTY else template.body_two_party
        if not body:
            return

        branch = await self.branches.get(application.branch_id)
        edu_level = await self.education_levels.get(application.education_level_id)
        edu_form = await self.education_forms.get(application.education_form_id)
        parties = await self.parties.list_for_contract(contract.id)
        cfg = await self.get_settings()

        # Look up course (for perevod) and user (for phone)
        from app.modules.applicants.repository import CourseRepository
        from app.modules.users.repository import UserRepository
        course = None
        if application.course_id:
            course = await CourseRepository(self.session).get(application.course_id)
        user = await UserRepository(self.session).get(applicant.user_id)

        # Resolve region/district names so the contract PDF shows
        # "Toshkent viloyati, Yunusobod tumani, ..." instead of just the raw
        # street address. Falls back gracefully if either link is missing.
        from app.modules.regions.models import District, Region
        region_name = None
        district_name = None
        if applicant.region_id:
            region_name = await self.session.scalar(
                select(Region.name).where(Region.id == applicant.region_id)
            )
        if applicant.district_id:
            district_name = await self.session.scalar(
                select(District.name).where(District.id == applicant.district_id)
            )

        try:
            html = render_html(
                body,
                _build_context(
                    contract=contract,
                    applicant=applicant,
                    application=application,
                    program=program,
                    branch=branch,
                    edu_level=edu_level,
                    edu_form=edu_form,
                    course=course,
                    user=user,
                    parties=parties,
                    cfg=cfg,
                    region_name=region_name,
                    district_name=district_name,
                    base_url=base_url,
                ),
            )
            pdf_bytes = render_pdf(html)
            file = await self.files.store_bytes(
                pdf_bytes,
                original_name=f"{contract.contract_number}.pdf",
                mime_type="application/pdf",
                subdir="contracts",
                uploaded_by_id=actor_id,
            )
            contract.pdf_file_id = file.id
            await self.session.flush()
        except Exception as exc:
            logger.error(
                "contract.pdf_failed", contract_id=str(contract.id), error=str(exc)
            )

    # ---------- Sign ----------
    async def sign(self, contract_id: UUID) -> Contract:
        obj = await self.get(contract_id)
        if obj.status != ContractStatus.DRAFT:
            raise ValidationError(
                f"Only draft contracts can be signed (current: {obj.status.value})"
            )
        obj.status = ContractStatus.SIGNED
        obj.signed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return obj

    async def cancel(self, contract_id: UUID) -> Contract:
        obj = await self.get(contract_id)
        if obj.status == ContractStatus.COMPLETED:
            raise ValidationError("Completed contracts cannot be cancelled")
        obj.status = ContractStatus.CANCELLED
        await self.session.flush()
        return obj

    # ---------- File access ----------
    async def get_pdf_bytes(self, contract_id: UUID) -> tuple[bytes, str]:
        obj = await self.get(contract_id)
        # PDF is only meaningful once both parties have signed. Before that,
        # the document is a draft preview — no point downloading it.
        if not obj.signed_at:
            raise NotFoundError("Shartnoma hali imzolanmagan")
        if not obj.pdf_file_id:
            raise NotFoundError("PDF not yet generated")
        from app.modules.files.service import FileRepository

        file = await FileRepository(self.session).get(obj.pdf_file_id)
        if not file:
            raise NotFoundError("PDF file record missing")
        path = await self.files.absolute_path(file)
        if not path.exists():
            raise NotFoundError("PDF file is missing on disk")

        # Filename: applicant's last + first (UPPER) when available so the
        # downloaded file is human-readable. Falls back to the contract
        # number if for any reason the applicant chain isn't loadable.
        download_name = await self._build_pdf_filename(obj) or file.original_name
        return path.read_bytes(), download_name

    async def _build_pdf_filename(self, contract) -> str | None:
        from sqlalchemy import select as _select
        from app.modules.applicants.models import Applicant
        from app.modules.applications.models import Application

        applicant_id = await self.session.scalar(
            _select(Application.applicant_id).where(Application.id == contract.application_id)
        )
        if not applicant_id:
            return None
        ap = await self.session.scalar(
            _select(Applicant).where(Applicant.id == applicant_id)
        )
        if not ap:
            return None
        parts = [
            (ap.last_name or "").strip().upper(),
            (ap.first_name or "").strip().upper(),
        ]
        joined = "-".join(p for p in parts if p)
        if not joined:
            return None
        # Strip filesystem-unfriendly chars but keep Latin/Cyrillic letters,
        # digits, dashes. Apostrophes become nothing (O' -> O), spaces -> -.
        import re
        joined = joined.replace("'", "").replace("`", "")
        joined = re.sub(r"\s+", "-", joined)
        joined = re.sub(r"[^\w\-]", "", joined, flags=re.UNICODE)
        return f"{joined}.pdf" if joined else None


def _make_qr_data_uri(payload: str) -> str:
    """Generate a base64-encoded PNG data URI for the given payload."""
    import base64
    import io

    import qrcode

    img = qrcode.make(payload, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _build_context(
    *, contract, applicant, application, program, branch, edu_level, edu_form, parties,
    course=None, user=None, cfg=None,
    region_name: str | None = None, district_name: str | None = None,
    base_url: str | None = None,
) -> dict:
    today = date.today()

    admission_type_label = (
        "Perevod" if application.admission_type == AdmissionType.TRANSFER else "1-kurs (yangi qabul)"
    )

    full_name = " ".join(
        filter(
            None, [applicant.last_name, applicant.first_name, applicant.other_name]
        )
    ).strip()

    # Parent / sponsor party (for 3-party templates)
    extra = next(
        (p for p in parties if p.party_role in {PartyRole.PARENT, PartyRole.SPONSOR}),
        None,
    )

    # Course label: "1-kurs" for new admission, course name for transfer
    if application.admission_type == AdmissionType.TRANSFER and course:
        course_label = course.name
    else:
        course_label = "1-kurs"

    # Format tuition fee with thousand separators ("12 000 000")
    yillik_tolov = ""
    if program and program.tuition_fee is not None:
        yillik_tolov = f"{int(program.tuition_fee):,}".replace(",", " ")

    # Phone: use the applicant's primary registration number (users.phone),
    # which is what they signed up with. additional_phone is a backup-only
    # contact and shouldn't be the one stamped on contracts.
    phone = (user.phone if user else "") or applicant.additional_phone or ""

    # Compose the student address: "<viloyat> viloyati, <tuman> tumani, <manzil>"
    # so the contract shows full geographic context, not just a street line.
    # Drops any segment that's missing.
    _addr_parts: list[str] = []
    if region_name:
        _addr_parts.append(f"{region_name} viloyati")
    if district_name:
        _addr_parts.append(f"{district_name} tumani")
    if applicant.address:
        _addr_parts.append(applicant.address.strip())
    composed_address = ", ".join(_addr_parts)

    # === QR code: encode public PDF URL → scannable PNG data URI ===
    # Prefer base_url derived from the request (works in any environment),
    # fall back to settings.public_base_url, then to relative path.
    public_base = (base_url or settings.public_base_url or "").rstrip("/")
    pdf_url = (
        f"{public_base}/api/v1/contracts/public/{contract.id}/pdf"
        if public_base else f"/api/v1/contracts/public/{contract.id}/pdf"
    )
    qr_data_uri = _make_qr_data_uri(pdf_url)

    # Bitiruv yili (graduation year): expected current_year + duration for new admission
    bitiruv_yili = ""
    if program and program.study_duration_years:
        try:
            bitiruv_yili = str(today.year + int(program.study_duration_years))
        except Exception:
            bitiruv_yili = ""

    # Short ID for contract (last 8 of UUID, uppercased)
    short_id = contract.contract_number.split("-")[-1] if contract.contract_number else str(contract.id).split("-")[-1].upper()
    yonalish_seriya = program.contract_series if program else ""

    return {
        # Core (new-style)
        "TALABA_ISMI": full_name,
        "TELEFON": phone,
        "FILIAL": branch.name if branch else "",
        "YONALISH": program.name if program else "",
        "TALIM_DARAJASI": edu_level.name if edu_level else "",
        "TALIM_SHAKLI": edu_form.name if edu_form else "",
        "QABUL_TURI": admission_type_label,
        "SANA": today.strftime("%d.%m.%Y"),
        "OTA_ONA_ISMI": extra.full_name if extra else "",
        "OTA_ONA_TELEFON": (extra.phone or "") if extra else "",
        "KONTRAKT_RAQAMI": contract.contract_number,
        "YILLIK_TOLOV": yillik_tolov,
        "OQISH_MUDDATI": f"{program.study_duration_years} yil" if program else "",
        "OQUV_KURSI": course_label,
        "PASSPORT_SERIYA": applicant.passport_series or "",
        "PINFL": applicant.pinfl or "",
        "YASHASH_MANZILI": composed_address or applicant.address or "",
        "SHARTNOMA_SERIYASI": yonalish_seriya,
        # Old Django-style aliases (kept for 1:1 reuse of legacy templates)
        "ID": short_id,
        "YONALISH_SERIYA": yonalish_seriya,
        "KONTRAKT_SUMMASI": yillik_tolov,
        "TALABA_MANZILI": composed_address or applicant.address or "",
        "TALABA_VILOYATI": region_name or "",
        "TALABA_TUMANI": district_name or "",
        "BITIRUV_YILI": bitiruv_yili,
        # QR code (use either case)
        "QR_CODE": qr_data_uri,
        "QR_CODE_DATA": qr_data_uri,
        "qr_code": qr_data_uri,
        # Structured nested context
        "contract": {
            "number": contract.contract_number,
            "type": contract.type.value if contract.type else "",
            "total_amount": str(contract.total_amount),
            "currency": contract.currency,
            "today": today.strftime("%d.%m.%Y"),
        },
        "applicant": {
            "full_name": full_name,
            "first_name": applicant.first_name,
            "last_name": applicant.last_name,
            "other_name": applicant.other_name or "",
            "birth_date": applicant.birth_date.strftime("%d.%m.%Y") if applicant.birth_date else "",
            "address": applicant.address or "",
            "full_address": composed_address or applicant.address or "",
            "region_name": region_name or "",
            "district_name": district_name or "",
            "passport_series": applicant.passport_series or "",
            "pinfl": applicant.pinfl or "",
        },
        "program": {
            "code": program.code if program else "",
            "name": program.name if program else "",
            "tuition_fee": str(program.tuition_fee) if program else "",
            "study_duration": f"{program.study_duration_years} yil" if program else "",
            "contract_series": program.contract_series if program else "",
        },
        "branch": {"name": branch.name if branch else ""},
        "education_level": {"name": edu_level.name if edu_level else ""},
        "education_form": {"name": edu_form.name if edu_form else ""},
        "admission_type": admission_type_label,
        "parties": [
            {
                "role": p.party_role.value,
                "full_name": p.full_name,
                "pinfl": p.pinfl or "",
                "passport_series": p.passport_series or "",
                "passport_number": p.passport_number or "",
                "phone": p.phone or "",
                "relationship": p.relationship or "",
                "address": p.address or "",
            }
            for p in parties
        ],
        "university": {
            "name": cfg.company_name if cfg else "",
            "legal_address": cfg.company_address if cfg else "",
            "inn": cfg.company_inn if cfg else "",
            "director_name": cfg.director_name if cfg else "",
            "director_title": cfg.director_title if cfg else "",
        },
    }
