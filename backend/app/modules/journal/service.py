"""Tizim daftari — every applicant's path through the admission funnel.

Events are DERIVED from the domain tables' own timestamps (not from
audit_logs), so the journal is complete for historical data too:

    registered / registered_by_staff   applicants.created_at (+ registered_by_id)
    application_submitted              applications.submitted_at / created_at
    status_changed                     application_status_history (from_status set)
    contract_created / _renewed        contracts.created_at (renewed = the
                                       application already had an earlier contract)
    contract_signed                    contracts.signed_at
    contract_cancelled                 contracts.cancelled_at

O'qishni ko'chirish (admission_type = 'perevod') is excluded entirely:
perevod applications and their contracts never appear, and applicants
whose ONLY applications are perevod are dropped (registration included).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TZ = "Asia/Tashkent"

EVENT_LABELS: dict[str, str] = {
    "registered": "Ro'yxatdan o'tdi",
    "registered_by_staff": "Ro'yxatdan o'tkazildi",
    "application_submitted": "Ariza topshirildi",
    "status_changed": "Ariza holati o'zgardi",
    "contract_created": "Shartnoma olindi",
    "contract_renewed": "Shartnoma yangilandi",
    "contract_signed": "Shartnoma imzolandi",
    "contract_cancelled": "Shartnoma bekor qilindi",
}
EVENT_CODES = tuple(EVENT_LABELS)

STATUS_LABELS = {
    "topshirildi": "Topshirildi",
    "korib_chiqilmoqda": "Ko'rib chiqilmoqda",
    "qabul_qilindi": "Qabul qilindi",
    "rad_etildi": "Rad etildi",
}

ROLE_LABELS = {
    "superadmin": "Superadmin",
    "admin": "Admin",
    "operator": "Operator",
    "director": "Direktor",
    "accountant": "Buxgalter",
    "applicant": "Abituriyent",
}

# One row per event. NULLs are typed explicitly so the UNION lines up.
_EVENTS_CTE = f"""
WITH excl AS (
    SELECT ap.id FROM applicants ap
    WHERE EXISTS (SELECT 1 FROM applications x
                  WHERE x.applicant_id = ap.id AND x.admission_type = 'perevod')
      AND NOT EXISTS (SELECT 1 FROM applications x
                      WHERE x.applicant_id = ap.id AND x.admission_type <> 'perevod')
),
apps AS (
    SELECT a.id, a.applicant_id, a.created_at, a.submitted_at
    FROM applications a
    WHERE a.admission_type <> 'perevod'
),
ev AS (
    SELECT ap.created_at AS event_at, ap.id AS applicant_id, NULL::uuid AS application_id,
           CASE WHEN ap.registered_by_id IS NULL THEN 'registered'
                ELSE 'registered_by_staff' END AS code,
           NULL::text AS from_status, NULL::text AS to_status, NULL::text AS note,
           NULL::uuid AS contract_id, ap.registered_by_id AS actor_id
    FROM applicants ap
    WHERE ap.id NOT IN (SELECT id FROM excl)

    UNION ALL
    SELECT COALESCE(a.submitted_at, a.created_at), a.applicant_id, a.id,
           'application_submitted', NULL, NULL, NULL, NULL::uuid,
           (SELECT h.changed_by_id FROM application_status_history h
             WHERE h.application_id = a.id AND h.from_status IS NULL
             ORDER BY h.created_at LIMIT 1)
    FROM apps a

    UNION ALL
    SELECT h.created_at, a.applicant_id, a.id, 'status_changed',
           h.from_status::text, h.to_status::text, h.comment, NULL::uuid, h.changed_by_id
    FROM application_status_history h
    JOIN apps a ON a.id = h.application_id
    WHERE h.from_status IS NOT NULL

    UNION ALL
    SELECT c.created_at, a.applicant_id, a.id,
           CASE WHEN EXISTS (SELECT 1 FROM contracts c2
                             WHERE c2.application_id = c.application_id
                               AND c2.created_at < c.created_at)
                THEN 'contract_renewed' ELSE 'contract_created' END,
           NULL, NULL, NULL, c.id, c.created_by_id
    FROM contracts c JOIN apps a ON a.id = c.application_id

    UNION ALL
    SELECT c.signed_at, a.applicant_id, a.id, 'contract_signed',
           NULL, NULL, NULL, c.id, c.signed_by_id
    FROM contracts c JOIN apps a ON a.id = c.application_id
    WHERE c.signed_at IS NOT NULL

    UNION ALL
    SELECT c.cancelled_at, a.applicant_id, a.id, 'contract_cancelled',
           NULL, NULL, c.cancelled_reason, c.id, c.cancelled_by_id
    FROM contracts c JOIN apps a ON a.id = c.application_id
    WHERE c.cancelled_at IS NOT NULL
),
full_ev AS (
    SELECT ev.*,
           (ev.event_at AT TIME ZONE '{TZ}') AS local_at,
           ap.last_name, ap.first_name, ap.other_name, ap.pinfl, ap.passport_series,
           u.phone,
           app.application_number,
           p.name AS program_name, ef.name AS form_name,
           c.contract_number, c.total_amount, c.source AS contract_source,
           act.full_name AS actor_name, act.role::text AS actor_role
    FROM ev
    JOIN applicants ap ON ap.id = ev.applicant_id
    JOIN users u ON u.id = ap.user_id
    LEFT JOIN applications app ON app.id = ev.application_id
    LEFT JOIN programs p ON p.id = app.program_id
    LEFT JOIN education_forms ef ON ef.id = app.education_form_id
    LEFT JOIN contracts c ON c.id = ev.contract_id
    LEFT JOIN users act ON act.id = ev.actor_id
    WHERE ev.event_at IS NOT NULL
)
"""

_SEARCH_SQL = """
    AND (:q = '' OR
         lower(concat_ws(' ', last_name, first_name, other_name)) LIKE :q_like OR
         pinfl LIKE :q_like OR
         phone LIKE :q_like OR
         upper(coalesce(passport_series, '')) LIKE upper(:q_like) OR
         coalesce(application_number, '') LIKE :q_like OR
         coalesce(contract_number, '') ILIKE :q_like)
"""

_RANGE_SQL = """
    AND (CAST(:d_from AS date) IS NULL OR local_at::date >= CAST(:d_from AS date))
    AND (CAST(:d_to AS date) IS NULL OR local_at::date <= CAST(:d_to AS date))
"""


def _fio(r: Any) -> str:
    return " ".join(x for x in (r["last_name"], r["first_name"], r["other_name"]) if x)


def _money(v: Decimal | None) -> str:
    if v is None:
        return ""
    return f"{int(v):,}".replace(",", " ") + " so'm"


def _detail(r: Any) -> str:
    code = r["code"]
    if code == "registered":
        return "O'zi ro'yxatdan o'tdi"
    if code == "registered_by_staff":
        return f"Xodim: {r['actor_name'] or '—'}"
    if code == "application_submitted":
        parts = [f"Ariza №{r['application_number']}"] if r["application_number"] else []
        if r["program_name"]:
            parts.append(r["program_name"] + (f" ({r['form_name']})" if r["form_name"] else ""))
        return " · ".join(parts)
    if code == "status_changed":
        s = f"{STATUS_LABELS.get(r['from_status'], r['from_status'])} → {STATUS_LABELS.get(r['to_status'], r['to_status'])}"
        return s + (f" · {r['note']}" if r["note"] else "")
    if code in ("contract_created", "contract_renewed", "contract_signed", "contract_cancelled"):
        parts = [f"Shartnoma №{r['contract_number']}"]
        if code in ("contract_created", "contract_renewed"):
            if r["total_amount"] is not None:
                parts.append(_money(r["total_amount"]))
            if r["contract_source"] == "external":
                parts.append("billing (tashqi)")
        if code == "contract_cancelled" and r["note"]:
            parts.append(f"Sabab: {r['note']}")
        return " · ".join(parts)
    return ""


def _actor(r: Any) -> str:
    if r["code"] == "registered":
        return "Abituriyent (o'zi)"
    if not r["actor_name"] and not r["actor_role"]:
        return ""
    role = ROLE_LABELS.get(r["actor_role"] or "", r["actor_role"] or "")
    name = r["actor_name"] or ""
    return f"{name} ({role})" if name and role else (name or role)


def _to_item(r: Any) -> dict:
    local_at: datetime = r["local_at"]
    return {
        "at": local_at,
        "applicant_id": r["applicant_id"],
        "application_id": r["application_id"],
        "full_name": _fio(r),
        "pinfl": r["pinfl"] or "",
        "phone": r["phone"] or "",
        "code": r["code"],
        "event": EVENT_LABELS.get(r["code"], r["code"]),
        "detail": _detail(r),
        "program": (r["program_name"] or "") + (f" ({r['form_name']})" if r["form_name"] else ""),
        "application_number": r["application_number"] or "",
        "contract_number": r["contract_number"] or "",
        "to_status": r["to_status"],
        "actor": _actor(r),
    }


class JournalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _params(*, date_from: date | None, date_to: date | None, search: str | None,
                codes: list[str] | None) -> tuple[dict, str]:
        q = (search or "").strip().lower()
        params: dict[str, Any] = {
            "d_from": date_from, "d_to": date_to,
            "q": q, "q_like": f"%{q}%",
        }
        codes_sql = ""
        valid = [c for c in (codes or []) if c in EVENT_CODES]
        if valid:
            codes_sql = " AND code = ANY(:codes)"
            params["codes"] = valid
        return params, codes_sql

    async def list_page(self, *, date_from: date | None, date_to: date | None,
                        search: str | None, codes: list[str] | None,
                        limit: int, offset: int) -> tuple[list[dict], int]:
        params, codes_sql = self._params(date_from=date_from, date_to=date_to,
                                         search=search, codes=codes)
        where = "WHERE TRUE" + _RANGE_SQL + _SEARCH_SQL + codes_sql
        total = (await self.session.execute(
            text(_EVENTS_CTE + f"SELECT count(*) FROM full_ev {where}"), params
        )).scalar_one()
        rows = (await self.session.execute(
            text(_EVENTS_CTE + f"SELECT * FROM full_ev {where} "
                 "ORDER BY event_at DESC LIMIT :limit OFFSET :offset"),
            {**params, "limit": limit, "offset": offset},
        )).mappings().all()
        return [_to_item(r) for r in rows], int(total)

    async def stats(self, *, date_from: date | None, date_to: date | None,
                    search: str | None) -> dict[str, int]:
        params, _ = self._params(date_from=date_from, date_to=date_to,
                                 search=search, codes=None)
        rows = (await self.session.execute(
            text(_EVENTS_CTE + "SELECT code, count(*) AS n FROM full_ev WHERE TRUE"
                 + _RANGE_SQL + _SEARCH_SQL + " GROUP BY code"),
            params,
        )).all()
        out = {c: 0 for c in EVENT_CODES}
        for code, n in rows:
            out[code] = int(n)
        return out

    async def events_by_date(self, *, date_from: date | None, date_to: date | None,
                             search: str | None, codes: list[str] | None) -> list[dict]:
        params, codes_sql = self._params(date_from=date_from, date_to=date_to,
                                         search=search, codes=codes)
        rows = (await self.session.execute(
            text(_EVENTS_CTE + "SELECT * FROM full_ev WHERE TRUE"
                 + _RANGE_SQL + _SEARCH_SQL + codes_sql + " ORDER BY event_at ASC"),
            params,
        )).mappings().all()
        return [_to_item(r) for r in rows]

    async def events_by_applicant(self, *, date_from: date | None, date_to: date | None,
                                  search: str | None) -> list[dict]:
        """Applicants that had ANY activity in the range — with their FULL
        path (all events, not only the in-range ones), grouped per person."""
        params, _ = self._params(date_from=date_from, date_to=date_to,
                                 search=search, codes=None)
        rows = (await self.session.execute(
            text(_EVENTS_CTE + """
                SELECT * FROM full_ev
                WHERE applicant_id IN (
                    SELECT applicant_id FROM full_ev WHERE TRUE""" + _RANGE_SQL + _SEARCH_SQL + """
                )
                ORDER BY last_name, first_name, applicant_id, event_at ASC
            """),
            params,
        )).mappings().all()
        return [_to_item(r) for r in rows]
