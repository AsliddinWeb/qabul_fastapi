"""One-shot script: shorten existing program codes to a compact
"{LEVEL}-{NAME}-{FORM}" format.

Strategy:
  • Level prefix: first letter only ("B" for Bakalavr, "M" for Magistr).
  • Name slug: first 2 letters of the FIRST word
    (e.g. "Iqtisodiyot" -> "IQ", "Pedagogika" -> "PE").
    On collision, fall back to 3 letters, then 4. If still colliding,
    append "-2", "-3", ... to disambiguate.
  • Form suffix: "K" (kunduzgi) / "S" (sirtqi). Preserved from the old
    code if present, otherwise inferred from the program's education_form.

Examples:
  Iqtisodiyot — Bakalavr — Kunduzgi  ->  B-IQ-K
  Iqtisodiyot — Bakalavr — Sirtqi    ->  B-IQ-S
  Iqtisodiyot — Magistr — Kunduzgi   ->  M-IQ-K
  Pedagogika  — Bakalavr — Kunduzgi  ->  B-PE-K

contract_series mirrors code.

Run on the server once after migrations:
    docker compose exec backend python -m scripts.shorten_program_codes
"""

from __future__ import annotations

import asyncio
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory

import app.db.models_registry  # noqa: F401

from app.modules.programs.models import EducationForm, EducationLevel, Program

logger = get_logger("shorten_codes")


def _level_prefix(name: str) -> str:
    """Single letter: B / M / O / etc."""
    letters = re.sub(r"[^A-Za-z]", "", (name or "").upper())
    return letters[:1] or "X"


def _first_word_slug(name: str, n_chars: int) -> str:
    """First N letters of the first word. Apostrophe-stripped (o' -> o, g' -> g)."""
    s = (name or "").replace("'", "").replace("`", "")
    s = s.replace("o'", "o").replace("g'", "g").replace("O'", "O").replace("G'", "G")
    words = re.findall(r"[A-Za-zА-Яа-я]+", s)
    if not words:
        return "X"
    return words[0][:n_chars].upper()


def _form_suffix(form_name: str | None, prev_code: str) -> str:
    """Detect K/S suffix from the existing code first (preserves user changes),
    fall back to the form name."""
    m = re.search(r"-([KS])$", prev_code or "")
    if m:
        return m.group(1)
    n = (form_name or "").lower()
    if "kunduz" in n:
        return "K"
    if "sirt" in n:
        return "S"
    return ""


async def main() -> None:
    configure_logging(debug=False)

    async with async_session_factory() as session:
        # Load levels + forms once for label lookup.
        levels = {l.id: l.name for l in (await session.scalars(select(EducationLevel))).all()}
        forms = {f.id: f.name for f in (await session.scalars(select(EducationForm))).all()}

        programs = list((await session.scalars(select(Program))).all())

        def build(p: Program, n_chars: int) -> str:
            level_pref = _level_prefix(levels.get(p.education_level_id, ""))
            slug = _first_word_slug(p.name, n_chars)
            suffix = _form_suffix(forms.get(p.education_form_id), p.code)
            base = f"{level_pref}-{slug}"
            if suffix:
                base = f"{base}-{suffix}"
            return base

        # Try widths 2 -> 3 -> 4 letters. After each pass, ANY program whose
        # code clashes with another program's code is recomputed at the next
        # width. This way "Iqtisodiyot" gets B-IQ-K, but two programs both
        # starting with "Ma..." escalate to 3 letters (MAK / MAT) before
        # falling back to numeric disambiguation.
        chosen: dict[str, str] = {}  # program_id -> code
        candidates: dict[str, list[Program]] = {}

        for width in (2, 3, 4):
            # Re-evaluate any unresolved program at this width.
            unresolved = [p for p in programs if str(p.id) not in chosen]
            if not unresolved:
                break

            # Bucket by code at this width
            buckets: dict[str, list[Program]] = {}
            for p in unresolved:
                buckets.setdefault(build(p, width), []).append(p)

            for code, group in buckets.items():
                if len(group) == 1:
                    # Also make sure this code isn't already locked-in for someone else
                    if code not in chosen.values():
                        chosen[str(group[0].id)] = code
                # else: leave for next-wider pass

        # Anything still unresolved gets numeric disambiguation at width=4.
        leftovers = [p for p in programs if str(p.id) not in chosen]
        for p in leftovers:
            base = build(p, 4)
            n = 2
            code = base
            while code in chosen.values():
                code = f"{base}-{n}"
                n += 1
            chosen[str(p.id)] = code

        proposed: list[tuple[Program, str]] = [(p, chosen[str(p.id)]) for p in programs]

        # Apply
        renamed = 0
        for p, new_code in proposed:
            if p.code == new_code and p.contract_series == new_code:
                continue
            old = p.code
            p.code = new_code
            p.contract_series = new_code
            renamed += 1
            logger.info("program.code.shortened", from_code=old, to_code=new_code, name=p.name)

        await session.commit()

    print(f"\n=== Done ===")
    print(f"  total programs:  {len(programs)}")
    print(f"  codes updated:   {renamed}")
    print(f"  codes unchanged: {len(programs) - renamed}")


if __name__ == "__main__":
    asyncio.run(main())
