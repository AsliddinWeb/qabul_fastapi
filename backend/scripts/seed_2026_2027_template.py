"""One-shot seed: install the "2026-2027 yangi shartnoma" template.

Run on the server:
    docker compose exec backend python -m scripts.seed_2026_2027_template

What it does (idempotent — safe to re-run):

  - Finds the existing canonical "Standart shartnoma shabloni" row.
  - Creates (or refreshes) a SECOND row named "2026-2027 yangi shartnoma":
      * body_three_party copied verbatim from the standart template.
      * body_two_party  also copied so the new row is fully usable.
      * is_active = False — existing standart stays the default; an admin
        can switch the active template from /admin/contract-templates.

Does NOT touch the existing "Standart shartnoma shabloni" row.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory

# Register all models for SQLAlchemy.
import app.db.models_registry  # noqa: F401

from app.modules.contracts.models import ContractTemplate

logger = get_logger("seed_2026_2027_template")

STANDART_NAME = "Standart shartnoma shabloni"
NEW_NAME = "2026-2027 yangi shartnoma"


async def main() -> None:
    configure_logging(debug=False)
    async with async_session_factory() as session:
        async with session.begin():
            standart = (
                await session.execute(
                    select(ContractTemplate).where(ContractTemplate.name == STANDART_NAME)
                )
            ).scalar_one_or_none()
            if standart is None:
                raise SystemExit(
                    f"'{STANDART_NAME}' template not found. Run "
                    "`python -m scripts.seed_catalogs_and_template` first."
                )

            existing = (
                await session.execute(
                    select(ContractTemplate).where(ContractTemplate.name == NEW_NAME)
                )
            ).scalar_one_or_none()

            if existing is not None:
                existing.body_two_party = standart.body_two_party
                existing.body_three_party = standart.body_three_party
                existing.version = (existing.version or 0) + 1
                # Don't flip is_active — leave whatever the admin has set.
                action = "refreshed"
            else:
                session.add(ContractTemplate(
                    name=NEW_NAME,
                    body_two_party=standart.body_two_party,
                    body_three_party=standart.body_three_party,
                    version=1,
                    is_active=False,
                ))
                action = "inserted"

            await session.flush()

    print(f"=== 2026-2027 template: {action} ===")
    print(f"  source:           {STANDART_NAME}")
    print(f"  two_party_chars:  {len(standart.body_two_party or '')}")
    print(f"  three_party_chars:{len(standart.body_three_party or '')}")
    print(f"  is_active:        False (admin can activate from /admin/contract-templates)")


if __name__ == "__main__":
    asyncio.run(main())
