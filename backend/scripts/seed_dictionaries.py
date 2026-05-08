"""Seed default dictionaries (idempotent).

Run inside container:  make seed
Run locally:           python -m scripts.seed_dictionaries

Idempotency: lookups by (type.code) and (item.type_id, item.code) — re-running
this script will NOT duplicate rows. Existing rows are left untouched.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory

# Register all models so SQLAlchemy can resolve cross-table FK references
import app.db.models_registry  # noqa: F401

from app.modules.dictionaries.models import DictionaryItem, DictionaryType

logger = get_logger("seed")


# ---------- Data definitions ----------

DICT_TYPES: list[dict[str, Any]] = [
    {"code": "regions",          "name": "Viloyatlar",            "is_hierarchical": True,  "is_system": True},
    {"code": "districts",        "name": "Tumanlar",              "is_hierarchical": True,  "is_system": True},
    {"code": "nationalities",    "name": "Millat",                "is_hierarchical": False, "is_system": True},
    {"code": "citizenships",     "name": "Fuqarolik",             "is_hierarchical": False, "is_system": True},
    {"code": "education_levels", "name": "Ta'lim darajasi",       "is_hierarchical": False, "is_system": True},
    {"code": "education_forms",  "name": "Ta'lim shakli",         "is_hierarchical": False, "is_system": True},
    {"code": "languages",        "name": "Ta'lim tili",           "is_hierarchical": False, "is_system": True},
    {"code": "payment_methods",  "name": "To'lov turi",           "is_hierarchical": False, "is_system": True},
    {"code": "document_types",   "name": "Hujjat turi",           "is_hierarchical": False, "is_system": True},
]


REGIONS: list[dict[str, str]] = [
    {"code": "TSH",  "name_uz": "Toshkent shahri",     "name_ru": "город Ташкент",         "name_en": "Tashkent city"},
    {"code": "TSHR", "name_uz": "Toshkent viloyati",   "name_ru": "Ташкентская область",   "name_en": "Tashkent region"},
    {"code": "AND",  "name_uz": "Andijon viloyati",    "name_ru": "Андижанская область",   "name_en": "Andijan"},
    {"code": "BUX",  "name_uz": "Buxoro viloyati",     "name_ru": "Бухарская область",     "name_en": "Bukhara"},
    {"code": "FAR",  "name_uz": "Farg'ona viloyati",   "name_ru": "Ферганская область",    "name_en": "Fergana"},
    {"code": "JIZ",  "name_uz": "Jizzax viloyati",     "name_ru": "Джизакская область",    "name_en": "Jizzakh"},
    {"code": "XOR",  "name_uz": "Xorazm viloyati",     "name_ru": "Хорезмская область",    "name_en": "Khorezm"},
    {"code": "NAM",  "name_uz": "Namangan viloyati",   "name_ru": "Наманганская область",  "name_en": "Namangan"},
    {"code": "NAV",  "name_uz": "Navoiy viloyati",     "name_ru": "Навоийская область",    "name_en": "Navoi"},
    {"code": "QAS",  "name_uz": "Qashqadaryo viloyati","name_ru": "Кашкадарьинская обл.",  "name_en": "Kashkadarya"},
    {"code": "QQR",  "name_uz": "Qoraqalpog'iston Respublikasi", "name_ru": "Республика Каракалпакстан", "name_en": "Karakalpakstan"},
    {"code": "SAM",  "name_uz": "Samarqand viloyati",  "name_ru": "Самаркандская область", "name_en": "Samarkand"},
    {"code": "SIR",  "name_uz": "Sirdaryo viloyati",   "name_ru": "Сырдарьинская область", "name_en": "Sirdaryo"},
    {"code": "SUR",  "name_uz": "Surxondaryo viloyati","name_ru": "Сурхандарьинская обл.", "name_en": "Surkhandarya"},
]


# Sample districts: Toshkent shahri (12 ta tuman). Boshqa viloyatlar keyinroq qo'shiladi.
DISTRICTS_BY_REGION: dict[str, list[dict[str, str]]] = {
    "TSH": [
        {"code": "TSH-BEK",  "name_uz": "Bektemir tumani"},
        {"code": "TSH-CHL",  "name_uz": "Chilonzor tumani"},
        {"code": "TSH-MIR",  "name_uz": "Mirobod tumani"},
        {"code": "TSH-MZU",  "name_uz": "Mirzo Ulug'bek tumani"},
        {"code": "TSH-OLM",  "name_uz": "Olmazor tumani"},
        {"code": "TSH-SER",  "name_uz": "Sergeli tumani"},
        {"code": "TSH-SHA",  "name_uz": "Shayxontohur tumani"},
        {"code": "TSH-UCH",  "name_uz": "Uchtepa tumani"},
        {"code": "TSH-YAK",  "name_uz": "Yakkasaroy tumani"},
        {"code": "TSH-YAS",  "name_uz": "Yashnobod tumani"},
        {"code": "TSH-YUN",  "name_uz": "Yunusobod tumani"},
        {"code": "TSH-YUK",  "name_uz": "Yangihayot tumani"},
    ],
}


NATIONALITIES = [
    {"code": "uzb",   "name_uz": "O'zbek",   "name_ru": "Узбек",   "name_en": "Uzbek"},
    {"code": "rus",   "name_uz": "Rus",      "name_ru": "Русский", "name_en": "Russian"},
    {"code": "qrq",   "name_uz": "Qoraqalpoq", "name_ru": "Каракалпак", "name_en": "Karakalpak"},
    {"code": "tjk",   "name_uz": "Tojik",    "name_ru": "Таджик",  "name_en": "Tajik"},
    {"code": "kaz",   "name_uz": "Qozoq",    "name_ru": "Казах",   "name_en": "Kazakh"},
    {"code": "kgz",   "name_uz": "Qirg'iz",  "name_ru": "Киргиз",  "name_en": "Kyrgyz"},
    {"code": "tat",   "name_uz": "Tatar",    "name_ru": "Татар",   "name_en": "Tatar"},
    {"code": "kor",   "name_uz": "Koreys",   "name_ru": "Кореец",  "name_en": "Korean"},
    {"code": "ukr",   "name_uz": "Ukrain",   "name_ru": "Украинец","name_en": "Ukrainian"},
    {"code": "tur",   "name_uz": "Turk",     "name_ru": "Турок",   "name_en": "Turkish"},
    {"code": "other", "name_uz": "Boshqa",   "name_ru": "Другой",  "name_en": "Other"},
]


CITIZENSHIPS = [
    {"code": "UZ",    "name_uz": "O'zbekiston", "name_ru": "Узбекистан", "name_en": "Uzbekistan"},
    {"code": "STATELESS", "name_uz": "Fuqaroligi yo'q", "name_ru": "Без гражданства", "name_en": "Stateless"},
    {"code": "OTHER", "name_uz": "Boshqa davlat", "name_ru": "Другое",   "name_en": "Other"},
]


EDUCATION_LEVELS = [
    {"code": "school",       "name_uz": "O'rta maktab",          "name_ru": "Средняя школа",  "name_en": "Secondary school"},
    {"code": "lyceum",       "name_uz": "Akademik litsey",       "name_ru": "Лицей",          "name_en": "Lyceum"},
    {"code": "college",      "name_uz": "Kasb-hunar kolleji",    "name_ru": "Колледж",        "name_en": "College"},
    {"code": "bachelor",     "name_uz": "Bakalavriat",           "name_ru": "Бакалавр",       "name_en": "Bachelor"},
    {"code": "master",       "name_uz": "Magistratura",          "name_ru": "Магистр",        "name_en": "Master"},
    {"code": "phd",          "name_uz": "Doktorantura",          "name_ru": "Докторант",      "name_en": "PhD"},
]


EDUCATION_FORMS = [
    {"code": "full_time",    "name_uz": "Kunduzgi", "name_ru": "Очная",     "name_en": "Full-time"},
    {"code": "evening",      "name_uz": "Kechki",   "name_ru": "Вечерняя",  "name_en": "Evening"},
    {"code": "correspondence","name_uz":"Sirtqi",   "name_ru": "Заочная",   "name_en": "Correspondence"},
    {"code": "distance",     "name_uz": "Masofaviy","name_ru": "Дистанц.",  "name_en": "Distance"},
]


LANGUAGES_DICT = [
    {"code": "uz", "name_uz": "O'zbek tili", "name_ru": "Узбекский", "name_en": "Uzbek"},
    {"code": "ru", "name_uz": "Rus tili",    "name_ru": "Русский",   "name_en": "Russian"},
    {"code": "en", "name_uz": "Ingliz tili", "name_ru": "Английский","name_en": "English"},
]


PAYMENT_METHODS = [
    {"code": "cash",      "name_uz": "Naqd",            "name_ru": "Наличные",    "name_en": "Cash"},
    {"code": "bank",      "name_uz": "Bank o'tkazma",   "name_ru": "Банк. перевод","name_en": "Bank transfer"},
    {"code": "click",     "name_uz": "Click",           "name_ru": "Click",       "name_en": "Click"},
    {"code": "payme",     "name_uz": "Payme",           "name_ru": "Payme",       "name_en": "Payme"},
    {"code": "uzcard",    "name_uz": "Uzcard",          "name_ru": "Uzcard",      "name_en": "Uzcard"},
    {"code": "humo",      "name_uz": "Humo",            "name_ru": "Humo",        "name_en": "Humo"},
]


DOCUMENT_TYPES = [
    {"code": "passport",     "name_uz": "Pasport"},
    {"code": "diploma",      "name_uz": "Diplom"},
    {"code": "school_cert",  "name_uz": "Maktab attestati"},
    {"code": "photo",        "name_uz": "3x4 rasm"},
    {"code": "medical_086",  "name_uz": "086 spravka"},
    {"code": "military",     "name_uz": "Harbiy guvohnoma"},
]


# ---------- Seeder ----------

async def _ensure_type(session: AsyncSession, spec: dict[str, Any]) -> DictionaryType:
    res = await session.execute(select(DictionaryType).where(DictionaryType.code == spec["code"]))
    obj = res.scalar_one_or_none()
    if obj:
        return obj
    obj = DictionaryType(**spec)
    session.add(obj)
    await session.flush()
    logger.info("seed.dictionary_type.created", code=spec["code"])
    return obj


async def _ensure_item(
    session: AsyncSession,
    type_obj: DictionaryType,
    item: dict[str, Any],
    *,
    parent_id=None,
) -> DictionaryItem:
    code = item.get("code")
    if code:
        res = await session.execute(
            select(DictionaryItem).where(
                DictionaryItem.type_id == type_obj.id,
                DictionaryItem.code == code,
            )
        )
        obj = res.scalar_one_or_none()
        if obj:
            return obj

    obj = DictionaryItem(
        type_id=type_obj.id,
        parent_id=parent_id,
        code=code,
        name_uz=item["name_uz"],
        name_ru=item.get("name_ru"),
        name_en=item.get("name_en"),
    )
    session.add(obj)
    await session.flush()
    return obj


async def seed(session: AsyncSession) -> None:
    types: dict[str, DictionaryType] = {}
    for t in DICT_TYPES:
        types[t["code"]] = await _ensure_type(session, t)

    # Flat lists
    flat_map = [
        ("nationalities",    NATIONALITIES),
        ("citizenships",     CITIZENSHIPS),
        ("education_levels", EDUCATION_LEVELS),
        ("education_forms",  EDUCATION_FORMS),
        ("languages",        LANGUAGES_DICT),
        ("payment_methods",  PAYMENT_METHODS),
        ("document_types",   DOCUMENT_TYPES),
    ]
    for type_code, items in flat_map:
        t = types[type_code]
        for it in items:
            await _ensure_item(session, t, it)

    # Regions (flat, but type is hierarchical because districts attach to it via parent_id).
    regions_type = types["regions"]
    region_objs: dict[str, DictionaryItem] = {}
    for r in REGIONS:
        region_objs[r["code"]] = await _ensure_item(session, regions_type, r)

    # Districts (children of regions) — go into the *districts* dictionary type,
    # but parent_id points to dictionary_items row of the region (cross-type tree).
    districts_type = types["districts"]
    for region_code, districts in DISTRICTS_BY_REGION.items():
        parent = region_objs[region_code]
        for d in districts:
            await _ensure_item(session, districts_type, d, parent_id=parent.id)


async def main() -> None:
    configure_logging(debug=False)
    async with async_session_factory() as session:
        async with session.begin():
            await seed(session)
    logger.info("seed.done")


if __name__ == "__main__":
    asyncio.run(main())
