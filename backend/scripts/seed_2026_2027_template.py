"""One-shot seed: install the "2026-2027 yangi shartnoma" template.

Run on the server:
    docker compose exec backend python -m scripts.seed_2026_2027_template

What it does (idempotent — safe to re-run):

  - UPSERTs a contract_templates row named "2026-2027 yangi shartnoma"
    populated from the customer-supplied 2026-2027 contract drafts
    bundled with the backend image:
      data/contract_templates/2026_two_party.html
      data/contract_templates/2026_three_party.html
  - Two-party body is a faithful HTML port of the leadd/.docx provided
    by the customer; three-party body extends the same clauses with a
    To'lovchi/Vasiy section in articles 1, 3, 4, and 9 ("9.3. To'lovchi/
    Vasiy" signature block).
  - Both bodies render TWO QR codes at the bottom: the existing
    contract-PDF QR (QR_CODE_DATA) and the new Xazna treasury-app QR
    (XAZNA_QR_CODE_DATA — populated by contracts/service.py at render
    time with the static merchantId URL).
  - is_active=False — existing "Standart shartnoma shabloni" stays the
    default; an admin activates this one from /admin/contract-templates.

Does NOT touch the standart row.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory

# Register all models for SQLAlchemy.
import app.db.models_registry  # noqa: F401

from app.modules.contracts.models import ContractTemplate

logger = get_logger("seed_2026_2027_template")

NEW_NAME = "2026-2027 yangi shartnoma"

TEMPLATES_DIR = Path("/app/data/contract_templates")


def _read_template(file_name: str) -> str:
    path = TEMPLATES_DIR / file_name
    if not path.exists():
        # Fallback for running outside docker (repo-relative).
        path = Path(__file__).resolve().parent.parent / "data" / "contract_templates" / file_name
    if not path.exists():
        raise FileNotFoundError(
            f"Contract template not found: {file_name}. "
            f"Expected at {TEMPLATES_DIR}/."
        )
    return path.read_text(encoding="utf-8")


async def main() -> None:
    configure_logging(debug=False)

    two_body = _read_template("2026_two_party.html")
    three_body = _read_template("2026_three_party.html")

    async with async_session_factory() as session:
        async with session.begin():
            existing = (
                await session.execute(
                    select(ContractTemplate).where(ContractTemplate.name == NEW_NAME)
                )
            ).scalar_one_or_none()

            if existing is not None:
                existing.body_two_party = two_body
                existing.body_three_party = three_body
                existing.version = (existing.version or 0) + 1
                # Don't flip is_active — leave whatever the admin has set.
                action = "refreshed"
            else:
                session.add(ContractTemplate(
                    name=NEW_NAME,
                    body_two_party=two_body,
                    body_three_party=three_body,
                    version=1,
                    is_active=False,
                ))
                action = "inserted"

            await session.flush()

    print(f"=== 2026-2027 template: {action} ===")
    print(f"  two_party_chars:  {len(two_body)}")
    print(f"  three_party_chars:{len(three_body)}")
    print(f"  qr layout:        contract PDF QR + Xazna treasury QR")
    print(f"  is_active:        False (admin activates from /admin/contract-templates)")


if __name__ == "__main__":
    asyncio.run(main())
