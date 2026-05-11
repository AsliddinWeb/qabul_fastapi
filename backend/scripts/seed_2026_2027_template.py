"""One-shot seed: install the "2026-2027 yangi shartnoma" template.

Run on the server:
    docker compose exec backend python -m scripts.seed_2026_2027_template

What it does (idempotent — safe to re-run):

  - Finds the existing canonical "Standart shartnoma shabloni".
  - Clones its body_two_party + body_three_party into a SECOND row named
    "2026-2027 yangi shartnoma".
  - Replaces the single-QR `<div class="qr-section">` block in both
    bodies with a DUAL-QR block: the existing contract-PDF QR side by
    side with the Xazna treasury-app payment QR. The xazna QR data is
    injected at render time via the XAZNA_QR_CODE_DATA context var
    populated in contracts/service.py.
  - Leaves is_active=False so the existing standart stays the default;
    an admin can switch from /admin/contract-templates.

Does NOT touch the existing "Standart shartnoma shabloni" row.
"""

from __future__ import annotations

import asyncio
import re

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.session import async_session_factory

# Register all models for SQLAlchemy.
import app.db.models_registry  # noqa: F401

from app.modules.contracts.models import ContractTemplate

logger = get_logger("seed_2026_2027_template")

STANDART_NAME = "Standart shartnoma shabloni"
NEW_NAME = "2026-2027 yangi shartnoma"

# Drop-in replacement for the single-QR block from the standart templates.
# Renders two QR codes (contract PDF + Xazna treasury) with captions, so the
# applicant can scan either one from the printed contract.
DUAL_QR_BLOCK = """
    <div class="qr-section" style="display: flex; gap: 32px; justify-content: center; align-items: flex-start; flex-wrap: wrap; margin-top: 24px;">
        {% if QR_CODE_DATA %}
        <div style="text-align: center;">
            <img src="{{ QR_CODE_DATA }}" alt="Shartnoma QR" class="qr-code" style="width: 110px; height: 110px;">
            <div style="font-size: 10px; margin-top: 6px; max-width: 130px; line-height: 1.3;">Shartnomani onlayn ko'rish</div>
        </div>
        {% endif %}
        {% if XAZNA_QR_CODE_DATA %}
        <div style="text-align: center;">
            <img src="{{ XAZNA_QR_CODE_DATA }}" alt="Xazna ilovasi QR" class="qr-code" style="width: 110px; height: 110px;">
            <div style="font-size: 10px; margin-top: 6px; max-width: 130px; line-height: 1.3; font-weight: bold;">Kontrakt to'lovini xazna ilovasi orqali to'lang</div>
        </div>
        {% endif %}
    </div>
""".strip()


# Pattern matches the original "<div class=\"qr-section\">...</div>" block in
# both two_party.html and three_party.html. Non-greedy + DOTALL so it stops at
# the first closing </div> belonging to qr-section.
_QR_SECTION_RE = re.compile(
    r'<div class="qr-section">.*?</div>',
    flags=re.DOTALL,
)


def _inject_dual_qr(body: str) -> str:
    """Replace the existing single-QR section with the dual-QR layout.

    If the marker is missing (template author edited it away), append the
    dual-QR block before </body> so we still emit both QRs in the rendered PDF.
    """
    if not body:
        return body
    replaced, n = _QR_SECTION_RE.subn(DUAL_QR_BLOCK, body, count=1)
    if n > 0:
        return replaced
    # Fallback: insert before </body>.
    if "</body>" in body:
        return body.replace("</body>", f"{DUAL_QR_BLOCK}\n</body>", 1)
    return body + "\n" + DUAL_QR_BLOCK


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

            two_body = _inject_dual_qr(standart.body_two_party or "")
            three_body = _inject_dual_qr(standart.body_three_party or "")

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
    print(f"  source:           {STANDART_NAME}")
    print(f"  two_party_chars:  {len(two_body)}")
    print(f"  three_party_chars:{len(three_body)}")
    print(f"  qr layout:        contract PDF QR + Xazna treasury QR")
    print(f"  is_active:        False (admin activates from /admin/contract-templates)")


if __name__ == "__main__":
    asyncio.run(main())
