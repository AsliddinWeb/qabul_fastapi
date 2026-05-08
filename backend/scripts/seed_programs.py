"""One-shot seed: branch (Qarshi) + 24 study programs (48 program rows
covering both Kunduzgi/Sirtqi forms) + supporting Education Levels and
Education Forms if missing.

Run on the server once after the bootstrap migrations:
    docker compose exec backend python -m scripts.seed_programs

The script is idempotent: re-running leaves existing branch / levels /
forms / programs untouched (programs are matched by
(branch, level, form, name)).

All data is embedded in this file — no CSV needed at runtime.
"""

from __future__ import annotations

import asyncio
import re
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory

# Register all models
import app.db.models_registry  # noqa: F401

from app.modules.programs.models import (
    Branch,
    EducationForm,
    EducationLevel,
    Program,
)

logger = get_logger("seed_programs")


# ============================================================================
# 1. BRANCH — single-branch setup for now
# ============================================================================

BRANCH_NAME = "Xalqaro Innovatsion Universiteti Qarshi filiali"


# ============================================================================
# 2. EDUCATION LEVELS — match what's used in PROGRAMS_DATA below
# ============================================================================

EDUCATION_LEVELS = ["Bakalavr", "Magistr"]


# ============================================================================
# 3. EDUCATION FORMS — every program has both a Kunduzgi and a Sirtqi price
#    in the source data, so we create one Program row per form.
# ============================================================================

EDUCATION_FORMS = ["Kunduzgi", "Sirtqi"]


# ============================================================================
# 4. PROGRAMS — extracted from leadd/yonalishlar.csv (24 programs).
# ============================================================================

PROGRAMS_DATA: list[dict[str, Any]] = [
    {'n': 1,  'fakultet': 'Pedagogika fakulteti',         'name_uz': 'Pedagogika',                          'name_ru': 'Педагогика',                                'name_en': 'Pedagogy',                  'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 2,  'fakultet': 'Pedagogika fakulteti',         'name_uz': "Maktabgacha ta'lim",                  'name_ru': 'Дошкольное образование',                    'name_en': 'Preschool education',       'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 3,  'fakultet': 'Pedagogika fakulteti',         'name_uz': "Boshlang'ich ta'lim",                 'name_ru': 'Начальное образование',                     'name_en': 'Primary education',         'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 4,  'fakultet': 'Pedagogika fakulteti',         'name_uz': 'Maxsus pedagogika (logopediya)',      'name_ru': 'Специальная педагогика (логопедия)',        'name_en': 'Special pedagogy (logopedics)', 'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",             'fee_kunduzgi': 10880000, 'fee_sirtqi': 10000000},
    {'n': 5,  'fakultet': 'Pedagogika fakulteti',         'name_uz': "Musiqa ta'limi",                      'name_ru': 'Музыкальное образование',                   'name_en': 'Music education',           'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 10880000, 'fee_sirtqi': 10000000},
    {'n': 6,  'fakultet': 'Pedagogika fakulteti',         'name_uz': "Psixologiya (faoliyat turlari bo'yicha)", 'name_ru': 'Психология (по направлениям деятельности)', 'name_en': 'Psychology',           'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 7,  'fakultet': 'Pedagogika fakulteti',         'name_uz': 'Jismoniy madaniyat',                  'name_ru': 'Физическая культура',                       'name_en': 'Physical education',        'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 8,  'fakultet': 'Pedagogika fakulteti',         'name_uz': 'Matematika',                          'name_ru': 'Математика',                                'name_en': 'Mathematics',               'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 9,  'fakultet': 'Tarix va filologiya fakulteti', 'name_uz': "Filologiya va tillarni o'qitish: o'zbek tili", 'name_ru': 'Филология и обучение языкам: узбекский', 'name_en': 'Philology: Uzbek', 'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 10000000, 'fee_sirtqi': 9000000},
    {'n': 10, 'fakultet': 'Tarix va filologiya fakulteti', 'name_uz': "Filologiya va tillarni o'qitish: rus tili",    'name_ru': 'Филология и обучение языкам: русский',   'name_en': 'Philology: Russian', 'level': 'Bakalavr', 'years': 4, 'language': 'Rus',                    'fee_kunduzgi': 10000000, 'fee_sirtqi': 9000000},
    {'n': 11, 'fakultet': 'Tarix va filologiya fakulteti', 'name_uz': "Filologiya va tillarni o'qitish: ingliz tili", 'name_ru': 'Филология и обучение языкам: английский','name_en': 'Philology: English', 'level': 'Bakalavr', 'years': 4, 'language': 'Ingliz',                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 12, 'fakultet': 'Tarix va filologiya fakulteti', 'name_uz': 'Tarix',                              'name_ru': 'История',                                   'name_en': 'History',                   'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 13, 'fakultet': 'Tarix va filologiya fakulteti', 'name_uz': 'Jurnalistika',                       'name_ru': 'Журналистика',                              'name_en': 'Journalism',                'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 14, 'fakultet': 'Tarix va filologiya fakulteti', 'name_uz': 'Kutubxona axborot faoliyati',        'name_ru': 'Библиотечно-информационная деятельность',  'name_en': 'Library science',           'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 15, 'fakultet': 'Iqtisodiyot fakulteti',        'name_uz': "Iqtisodiyot (tarmoqlar va sohalar bo'yicha)", 'name_ru': 'Экономика (по отраслям и сферам)',  'name_en': 'Economics',                 'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 16, 'fakultet': 'Iqtisodiyot fakulteti',        'name_uz': 'Moliya va moliyaviy texnologiyalar',  'name_ru': 'Финансы и финансовые технологии',           'name_en': 'Finance and FinTech',       'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 17, 'fakultet': 'Iqtisodiyot fakulteti',        'name_uz': 'Buxgalteriya hisobi va audit',        'name_ru': 'Бухгалтерский учёт и аудит',                'name_en': 'Accounting and audit',      'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 18, 'fakultet': 'Iqtisodiyot fakulteti',        'name_uz': 'Axborot tizimlari va texnologiyalari', 'name_ru': 'Информационные системы и технологии',      'name_en': 'Information systems',       'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 12000000, 'fee_sirtqi': 11000000},
    {'n': 19, 'fakultet': 'Iqtisodiyot fakulteti',        'name_uz': 'Kommunal infra tuzilmalarni tashkil etish va boshqarish', 'name_ru': 'Организация коммунальной инфраструктуры', 'name_en': 'Communal infrastructure management', 'level': 'Bakalavr', 'years': 4, 'language': "O'zbek", 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 20, 'fakultet': 'Iqtisodiyot fakulteti',        'name_uz': 'Yer kadastri va yer tuzish',          'name_ru': 'Земельный кадастр и землеустройство',       'name_en': 'Land cadastre',             'level': 'Bakalavr', 'years': 4, 'language': "O'zbek",                 'fee_kunduzgi': 11000000, 'fee_sirtqi': 10000000},
    {'n': 21, 'fakultet': "Magistratura bo'limi",         'name_uz': 'Iqtisodiyot',                         'name_ru': 'Экономика',                                 'name_en': 'Economics',                 'level': 'Magistr',  'years': 2, 'language': "O'zbek",                 'fee_kunduzgi': 14000000, 'fee_sirtqi': 12000000},
    {'n': 22, 'fakultet': "Magistratura bo'limi",         'name_uz': 'Pedagogika',                          'name_ru': 'Педагогика',                                'name_en': 'Pedagogy',                  'level': 'Magistr',  'years': 2, 'language': "O'zbek",                 'fee_kunduzgi': 14000000, 'fee_sirtqi': 12000000},
    {'n': 23, 'fakultet': "Magistratura bo'limi",         'name_uz': 'Psixologiya',                         'name_ru': 'Психология',                                'name_en': 'Psychology',                'level': 'Magistr',  'years': 2, 'language': "O'zbek",                 'fee_kunduzgi': 14000000, 'fee_sirtqi': 12000000},
    {'n': 24, 'fakultet': "Magistratura bo'limi",         'name_uz': "Lingvistika (rus, o'zbek, ingliz tillari)", 'name_ru': 'Лингвистика (русский, узбекский, английский)', 'name_en': 'Linguistics', 'level': 'Magistr',  'years': 2, 'language': "O'zbek/Rus/Ingliz",      'fee_kunduzgi': 14000000, 'fee_sirtqi': 12000000},
]


# ============================================================================
# Helpers
# ============================================================================

def _slug(name: str) -> str:
    """Build a URL-safe code from a program name (uppercase, alnum + dashes)."""
    s = name.lower()
    # transliterate common Uzbek/Russian to ASCII-ish
    s = s.replace("o'", "o").replace("g'", "g").replace("'", "").replace("`", "")
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s.upper()[:40] or "PROGRAM"


def _make_code(level_name: str, name: str, n: int) -> str:
    return f"{_slug(level_name)[:3]}-{_slug(name)}-{n:03d}"


# ============================================================================
# Seeders (idempotent)
# ============================================================================

async def _ensure_branch(session: AsyncSession) -> Branch:
    res = await session.execute(select(Branch).where(Branch.name == BRANCH_NAME))
    b = res.scalar_one_or_none()
    if b:
        return b
    b = Branch(name=BRANCH_NAME, is_active=True)
    session.add(b)
    await session.flush()
    logger.info("seed.branch.created", name=BRANCH_NAME)
    return b


async def _ensure_level(session: AsyncSession, name: str) -> EducationLevel:
    res = await session.execute(select(EducationLevel).where(EducationLevel.name == name))
    obj = res.scalar_one_or_none()
    if obj:
        return obj
    obj = EducationLevel(name=name)
    session.add(obj)
    await session.flush()
    logger.info("seed.level.created", name=name)
    return obj


async def _ensure_form(session: AsyncSession, name: str) -> EducationForm:
    res = await session.execute(select(EducationForm).where(EducationForm.name == name))
    obj = res.scalar_one_or_none()
    if obj:
        return obj
    obj = EducationForm(name=name)
    session.add(obj)
    await session.flush()
    logger.info("seed.form.created", name=name)
    return obj


async def _ensure_program(
    session: AsyncSession,
    *,
    branch: Branch,
    level: EducationLevel,
    form: EducationForm,
    name: str,
    code: str,
    tuition: int,
    years: int,
) -> tuple[Program, bool]:
    """Returns (program, created)."""
    res = await session.execute(
        select(Program).where(
            Program.branch_id == branch.id,
            Program.education_level_id == level.id,
            Program.education_form_id == form.id,
            Program.name == name,
        )
    )
    prg = res.scalar_one_or_none()
    if prg:
        return prg, False

    prg = Program(
        branch_id=branch.id,
        education_level_id=level.id,
        education_form_id=form.id,
        name=name,
        code=code,
        tuition_fee=Decimal(tuition),
        study_duration_years=years,
        contract_series=code,
        is_active=True,
    )
    session.add(prg)
    await session.flush()
    return prg, True


async def main() -> None:
    configure_logging(debug=False)

    async with async_session_factory() as session:
        async with session.begin():
            branch = await _ensure_branch(session)

            levels: dict[str, EducationLevel] = {}
            for ln in EDUCATION_LEVELS:
                levels[ln] = await _ensure_level(session, ln)

            forms: dict[str, EducationForm] = {}
            for fn in EDUCATION_FORMS:
                forms[fn] = await _ensure_form(session, fn)

            created_count = 0
            existing_count = 0

            for spec in PROGRAMS_DATA:
                level = levels[spec["level"]]
                base_code = _make_code(spec["level"], spec["name_uz"], spec["n"])

                # Kunduzgi
                if spec["fee_kunduzgi"] > 0:
                    _, was_new = await _ensure_program(
                        session,
                        branch=branch, level=level, form=forms["Kunduzgi"],
                        name=spec["name_uz"],
                        code=f"{base_code}-K",
                        tuition=spec["fee_kunduzgi"],
                        years=spec["years"],
                    )
                    if was_new: created_count += 1
                    else: existing_count += 1

                # Sirtqi
                if spec["fee_sirtqi"] > 0:
                    _, was_new = await _ensure_program(
                        session,
                        branch=branch, level=level, form=forms["Sirtqi"],
                        name=spec["name_uz"],
                        code=f"{base_code}-S",
                        tuition=spec["fee_sirtqi"],
                        years=spec["years"],
                    )
                    if was_new: created_count += 1
                    else: existing_count += 1

    print("\n=== Seed summary ===")
    print(f"  branch:                 {BRANCH_NAME}")
    print(f"  education levels:       {len(EDUCATION_LEVELS)}")
    print(f"  education forms:        {len(EDUCATION_FORMS)}")
    print(f"  programs created:       {created_count}")
    print(f"  programs already-exist: {existing_count}")


if __name__ == "__main__":
    asyncio.run(main())
