"""One-shot seed for production: catalogs + canonical contract template.

Run on the server once after migrations:
    docker compose exec backend python -m scripts.seed_catalogs_and_template

What it does (idempotent — safe to re-run):

  1. Education types (Bakalavr / Magistratura / O'rta-maxsus / ... )
  2. Institution types (Universitet / Akademiya / Institut / Kollej / Litsey / Maktab)
  3. Courses (1-kurs ... 6-kurs)
  4. Contract templates: REPLACE all existing rows with a single active
     template populated from the legacy Django files
     (old/qabul-sayt-main/templates/contracts/{ikki,uch}_tomonlama.html).

The template file paths are resolved relative to /app inside the backend
container, where the repo is mounted via the Dockerfile.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory

# Register all models for SQLAlchemy.
import app.db.models_registry  # noqa: F401

from app.modules.applicants.models import Course, EducationType, InstitutionType
from app.modules.contracts.models import ContractTemplate

logger = get_logger("seed_catalogs")


# ---------------------------------------------------------------------------
# Catalogs
# ---------------------------------------------------------------------------

EDUCATION_TYPES = [
    "Maktab attestati",
    "Akademik litsey diplomi",
    "Kasb-hunar kolleji diplomi",
    "Bakalavr diplomi",
    "Magistr diplomi",
    "O'rta-maxsus ma'lumot diplomi",
]

INSTITUTION_TYPES = [
    "Maktab",
    "Akademik litsey",
    "Kasb-hunar kolleji",
    "Texnikum",
    "Universitet",
    "Institut",
    "Akademiya",
]

COURSES = [
    "1-kurs",
    "2-kurs",
    "3-kurs",
    "4-kurs",
    "5-kurs",
    "6-kurs",
]


# ---------------------------------------------------------------------------
# Contract templates — bundled with the backend image at /app/data/.
# (Original source: old/qabul-sayt-main/templates/contracts/*.html, copied
# into backend/data/contract_templates/ so the files ship in the Docker image.)
# ---------------------------------------------------------------------------

TEMPLATES_DIR = Path("/app/data/contract_templates")


def _read_template(file_name: str) -> str:
    path = TEMPLATES_DIR / file_name
    if not path.exists():
        # Fallback for running outside docker (repo-relative).
        path = Path(__file__).resolve().parent.parent / "data" / "contract_templates" / file_name
    if not path.exists():
        raise FileNotFoundError(
            f"Contract template not found: {file_name}. "
            f"Expected at {TEMPLATES_DIR}/. The backend image must include backend/data/contract_templates/."
        )
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Seeders (idempotent)
# ---------------------------------------------------------------------------

async def _ensure_named_rows(session: AsyncSession, model, names: list[str], label: str) -> int:
    created = 0
    for name in names:
        res = await session.execute(select(model).where(model.name == name))
        if res.scalar_one_or_none() is None:
            session.add(model(name=name))
            await session.flush()
            created += 1
    logger.info(f"seed.{label}.done", created=created, total=len(names))
    return created


async def _replace_contract_template(session: AsyncSession) -> None:
    """Wipe existing templates, install a single active canonical one.

    Safe because contracts already in the DB don't FK to template rows
    (template_id is captured as a snapshot at contract creation time).
    """
    two_party = _read_template("two_party.html")
    three_party = _read_template("three_party.html")

    # Wipe all existing templates — caller asked for "delete current ones,
    # keep one standard". This is a one-shot script so we accept the cost.
    await session.execute(delete(ContractTemplate))

    template = ContractTemplate(
        name="Standart shartnoma shabloni",
        body_two_party=two_party,
        body_three_party=three_party,
        version=1,
        is_active=True,
    )
    session.add(template)
    await session.flush()
    logger.info(
        "seed.contract_template.installed",
        two_party_chars=len(two_party),
        three_party_chars=len(three_party),
    )


async def main() -> None:
    configure_logging(debug=False)
    async with async_session_factory() as session:
        async with session.begin():
            ed_created  = await _ensure_named_rows(session, EducationType,   EDUCATION_TYPES,   "education_types")
            in_created  = await _ensure_named_rows(session, InstitutionType, INSTITUTION_TYPES, "institution_types")
            crs_created = await _ensure_named_rows(session, Course,          COURSES,           "courses")
            await _replace_contract_template(session)

    print("\n=== Seed summary ===")
    print(f"  education types:    +{ed_created}  / total {len(EDUCATION_TYPES)}")
    print(f"  institution types:  +{in_created}  / total {len(INSTITUTION_TYPES)}")
    print(f"  courses:            +{crs_created} / total {len(COURSES)}")
    print(f"  contract template:  replaced (1 active row)")


if __name__ == "__main__":
    asyncio.run(main())
