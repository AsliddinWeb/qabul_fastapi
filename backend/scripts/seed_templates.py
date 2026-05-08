"""Seed default contract templates (idempotent).

Creates one 2-party and one 3-party template (Uzbek, version 1, active).
Re-running the script does NOT duplicate — existing rows are skipped.

Run inside container: make seed-templates
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.enums import ContractType, Language
from app.db.session import async_session_factory

# Import all models so SQLAlchemy can resolve cross-table FKs
# (ContractTemplate → dictionary_items.education_level_id, etc.)
import app.db.models_registry  # noqa: F401

from app.modules.contracts.models import ContractTemplate

logger = get_logger("seed.templates")

_TWO_PARTY_HTML = """\
<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><title>Shartnoma {{ contract.number }}</title>
<style>
 body { font-family: sans-serif; padding: 40px; color: #111; line-height: 1.5; }
 h1 { text-align: center; font-size: 18pt; }
 .meta { display:flex; justify-content: space-between; margin: 20px 0; font-size: 11pt; }
 .parties { margin-top: 24px; }
 .party { padding: 12px 0; border-top: 1px solid #ddd; }
 .signatures { margin-top: 50px; display:flex; justify-content: space-between; }
 .sig-block { width: 45%; }
 table { width:100%; border-collapse: collapse; margin: 16px 0; }
 td, th { padding: 6px 8px; border: 1px solid #ddd; font-size: 11pt; text-align: left; }
</style></head><body>
<h1>IKKI TOMONLAMA TA'LIM SHARTNOMASI № {{ contract.number }}</h1>
<div class="meta">
  <div>{{ university.legal_address }}</div>
  <div>{{ contract.today }}</div>
</div>

<p>{{ university.name }} (keyingi o'rinlarda — Universitet) nomidan ish ko'ruvchi
{{ university.director_title }} {{ university.director_name }} bilan
abituriyent <strong>{{ applicant.full_name }}</strong>
(keyingi o'rinlarda — Talaba) ushbu shartnomani tuzdilar.</p>

<h3>1. Shartnoma predmeti</h3>
<p>Universitet Talabaga "{{ program.name_uz }}" yo'nalishi bo'yicha {{ program.duration_years }} yillik
ta'lim xizmatini ko'rsatadi.</p>

<h3>2. Shartnoma summasi</h3>
<table>
  <tr><th>Yo'nalish kodi</th><td>{{ program.code }}</td></tr>
  <tr><th>O'quv yili</th><td>{{ period.name }}</td></tr>
  <tr><th>Yillik to'lov</th><td>{{ offering.tuition_fee }} {{ contract.currency }}</td></tr>
  <tr><th>Jami summa</th><td><strong>{{ contract.total_amount }} {{ contract.currency }}</strong></td></tr>
</table>

<h3>3. Tomonlar rekvizitlari</h3>
<div class="parties">
  {% for p in parties %}
  <div class="party">
    <strong>{{ p.role|upper }}:</strong> {{ p.full_name }}
    {% if p.pinfl %}<br>JSHSHIR: {{ p.pinfl }}{% endif %}
    {% if p.passport_series and p.passport_number %}<br>Pasport: {{ p.passport_series }} {{ p.passport_number }}{% endif %}
    {% if p.address %}<br>Manzil: {{ p.address }}{% endif %}
    {% if p.phone %}<br>Tel: {{ p.phone }}{% endif %}
  </div>
  {% endfor %}
</div>

<div class="signatures">
  <div class="sig-block">
    <div>Universitet nomidan</div>
    <div>{{ university.director_title }}</div>
    <div>____________________ {{ university.director_name }}</div>
  </div>
  <div class="sig-block">
    <div>Talaba</div>
    <div>____________________ {{ applicant.full_name }}</div>
  </div>
</div>
</body></html>
"""

_THREE_PARTY_HTML = """\
<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><title>Shartnoma {{ contract.number }}</title>
<style>
 body { font-family: sans-serif; padding: 40px; color: #111; line-height: 1.5; }
 h1 { text-align: center; font-size: 18pt; }
 .meta { display:flex; justify-content: space-between; margin: 20px 0; font-size: 11pt; }
 .party { padding: 12px 0; border-top: 1px solid #ddd; }
 .signatures { margin-top: 50px; display:flex; justify-content: space-between; gap: 12px; }
 .sig-block { width: 32%; font-size: 11pt; }
 table { width:100%; border-collapse: collapse; margin: 16px 0; }
 td, th { padding: 6px 8px; border: 1px solid #ddd; font-size: 11pt; text-align: left; }
</style></head><body>
<h1>UCH TOMONLAMA TA'LIM SHARTNOMASI № {{ contract.number }}</h1>
<div class="meta">
  <div>{{ university.legal_address }}</div>
  <div>{{ contract.today }}</div>
</div>

<p>{{ university.name }} (Universitet),
abituriyent <strong>{{ applicant.full_name }}</strong> (Talaba) va uchinchi tomon
{% for p in parties if p.role == 'sponsor' or p.role == 'parent' %}<strong>{{ p.full_name }}</strong>{% endfor %}
ushbu shartnomani tuzdilar.</p>

<h3>1. Shartnoma predmeti</h3>
<p>Universitet "{{ program.name_uz }}" yo'nalishi bo'yicha {{ program.duration_years }} yillik
ta'lim xizmatini ko'rsatadi. To'lov uchinchi tomon tomonidan amalga oshiriladi.</p>

<h3>2. Shartnoma summasi</h3>
<table>
  <tr><th>Yo'nalish</th><td>{{ program.code }} — {{ program.name_uz }}</td></tr>
  <tr><th>O'quv yili</th><td>{{ period.name }}</td></tr>
  <tr><th>Yillik to'lov</th><td>{{ offering.tuition_fee }} {{ contract.currency }}</td></tr>
  <tr><th>Jami summa</th><td><strong>{{ contract.total_amount }} {{ contract.currency }}</strong></td></tr>
</table>

<h3>3. Tomonlar</h3>
{% for p in parties %}
<div class="party">
  <strong>{{ p.role|upper }}:</strong> {{ p.full_name }}
  {% if p.relationship %}<em>({{ p.relationship }})</em>{% endif %}
  {% if p.pinfl %}<br>JSHSHIR: {{ p.pinfl }}{% endif %}
  {% if p.passport_series and p.passport_number %}<br>Pasport: {{ p.passport_series }} {{ p.passport_number }}{% endif %}
  {% if p.address %}<br>Manzil: {{ p.address }}{% endif %}
  {% if p.phone %}<br>Tel: {{ p.phone }}{% endif %}
</div>
{% endfor %}

<div class="signatures">
  <div class="sig-block">
    <strong>Universitet</strong><br>{{ university.director_title }}<br>
    ____________ {{ university.director_name }}
  </div>
  <div class="sig-block">
    <strong>Talaba</strong><br>
    ____________ {{ applicant.full_name }}
  </div>
  <div class="sig-block">
    <strong>Uchinchi tomon</strong><br>
    {% for p in parties if p.role == 'sponsor' or p.role == 'parent' %}
    ____________ {{ p.full_name }}
    {% endfor %}
  </div>
</div>
</body></html>
"""


_DEFINITIONS = [
    {
        "name": "Standart 2-tomonlama (UZ)",
        "type": ContractType.TWO_PARTY,
        "language": Language.UZ,
        "body_html": _TWO_PARTY_HTML,
    },
    {
        "name": "Standart 3-tomonlama (UZ)",
        "type": ContractType.THREE_PARTY,
        "language": Language.UZ,
        "body_html": _THREE_PARTY_HTML,
    },
]


async def main() -> None:
    configure_logging(debug=False)
    async with async_session_factory() as session:
        async with session.begin():
            for spec in _DEFINITIONS:
                existing = (
                    await session.execute(
                        select(ContractTemplate).where(ContractTemplate.name == spec["name"])
                    )
                ).scalar_one_or_none()
                if existing:
                    logger.info("seed.template.exists", name=spec["name"])
                    continue
                session.add(
                    ContractTemplate(
                        name=spec["name"],
                        type=spec["type"],
                        language=spec["language"],
                        body_html=spec["body_html"],
                        version=1,
                        is_active=True,
                    )
                )
                logger.info("seed.template.created", name=spec["name"])


if __name__ == "__main__":
    asyncio.run(main())
