"""One-shot script: shorten existing program codes from
"BAK-AXBOROT-TIZIMLARI-VA-TEXNOLOGIYALARI-018-S" to "BAK-ATT-S".

Strategy:
  • Level prefix: first 3 letters of education level ("BAK", "MAG").
  • Name acronym: initials of the first 3-4 words; if the name is a
    single word, use its first 3 letters. Strips non-alphabetic chars.
  • Form suffix: "K" (kunduzgi) / "S" (sirtqi). Preserved from the old
    code if present, otherwise inferred from the program's education_form.
  • Disambiguator: NO sequence number by default. If two programs would
    end up with the same code (acronym collision), append "-2", "-3", ...

contract_series mirrors code (same value).

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
    return re.sub(r"[^A-Za-z]", "", (name or "").upper())[:3] or "PRG"


def _name_acronym(name: str) -> str:
    """Initials of the first 3 words; fall back to first 3 letters if 1 word."""
    s = (name or "").replace("'", "").replace("`", "")
    s = s.replace("o'", "o").replace("g'", "g").replace("O'", "O").replace("G'", "G")
    words = re.findall(r"[A-Za-zА-Яа-я]+", s)
    if not words:
        return "X"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:4]).upper()


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

        # First pass: compute the *natural* short code for each program.
        natural: list[tuple[Program, str]] = []
        for p in programs:
            level_pref = _level_prefix(levels.get(p.education_level_id, ""))
            acro = _name_acronym(p.name)
            suffix = _form_suffix(forms.get(p.education_form_id), p.code)
            base = f"{level_pref}-{acro}"
            if suffix:
                base = f"{base}-{suffix}"
            natural.append((p, base))

        # Second pass: only programs that collide get a numeric tail.
        from collections import Counter
        cnt = Counter(code for _, code in natural)
        used: dict[str, int] = {}
        proposed: list[tuple[Program, str]] = []
        for p, base in natural:
            if cnt[base] == 1:
                proposed.append((p, base))
                continue
            used[base] = used.get(base, 0) + 1
            n = used[base]
            disambiguated = base if n == 1 else f"{base}-{n}"
            proposed.append((p, disambiguated))

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
