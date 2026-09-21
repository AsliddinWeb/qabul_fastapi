"""Import confirmed payments from an accountant Excel (e.g. Yangilar.xlsx).

Each row is one student with their identity (F.I.O / Passport / PINFL) and one
or more (To'lov summasi, To'lov sanasi) = (amount, date) pairs. For each pair
we find the student's active contract (by PINFL, then passport) and record a
CONFIRMED payment — attributed to an accountant — then refresh the contract's
paid_amount cache.

IDEMPOTENT: a payment is skipped if the same contract already has a confirmed
payment with the same amount AND the same date. So re-uploading a newer Excel
only adds what's missing; it never double-counts.

Usage (inside the backend container):

    # 1) Dry-run — show what WOULD be inserted, change nothing:
    docker compose cp Yangilar.xlsx backend:/tmp/Yangilar.xlsx
    docker compose exec -T -w /app backend python -m scripts.import_payments \
        --file /tmp/Yangilar.xlsx --dry-run

    # 2) Real run:
    docker compose exec -T -w /app backend python -m scripts.import_payments \
        --file /tmp/Yangilar.xlsx

    # 3) Afterwards DELETE the personal-data file from the container + host:
    docker compose exec -T backend rm -f /tmp/Yangilar.xlsx
    rm -f Yangilar.xlsx

Flags:
    --file PATH        Required. Path to the .xlsx inside the container.
    --dry-run          List actions, write nothing, exit 0.
    --sheet NAME       Worksheet name (default: first sheet).
    --method-code CODE Payment-method dictionary code (default: auto-pick a
                       bank/transfer method, else the first available).
    --actor-id UUID    registered_by user (default: first accountant, else a
                       superadmin).
    --limit N          Stop after N inserted payments (for a careful first pass).

Safety: per-payment commit; a failure on one row doesn't roll back the rest.
"""

from __future__ import annotations

import argparse
import asyncio
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import text

import app.db.models_registry  # noqa: F401  (register all model tables)
from app.db.enums import UserRole
from app.db.session import async_session_factory
from app.modules.payments.schemas import PaymentConfirm, PaymentCreate
from app.modules.payments.service import PaymentsService


# ----------------------------- parsing helpers -----------------------------
def _norm(s: str) -> str:
    """Header key: lowercase, drop apostrophe variants and extra spaces."""
    s = (s or "").strip().lower()
    s = s.replace("’", "").replace("'", "").replace("`", "").replace("ʻ", "")
    return re.sub(r"\s+", " ", s)


def parse_amount(v) -> Decimal | None:
    if v is None or v == "":
        return None
    digits = re.sub(r"\D", "", str(v))  # so'm sums are whole numbers
    if not digits:
        return None
    try:
        d = Decimal(digits)
        return d if d > 0 else None
    except InvalidOperation:
        return None


_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y",
                 "%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y")


def parse_date(v) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    s = str(v).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _digits(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


# ----------------------------- header mapping ------------------------------
def map_columns(header: list) -> dict:
    """Return {pinfl, passport, fio: idx} and pairs=[(amount_idx, date_idx), ...]."""
    cols = {"pinfl": None, "passport": None, "fio": None}
    amount_idxs, date_idxs = [], []
    for i, h in enumerate(header):
        k = _norm(str(h) if h is not None else "")
        if "pinfl" in k or "jshshir" in k or "pnfl" in k:
            cols["pinfl"] = i
        elif "passport" in k or "pasport" in k:
            cols["passport"] = i
        elif cols["fio"] is None and (k in ("f.i.o", "fio", "fish") or "f.i.o" in k or "familiya" in k):
            cols["fio"] = i
        elif k == "tolov summasi":
            amount_idxs.append(i)
        elif k == "tolov sanasi":
            date_idxs.append(i)
    pairs = list(zip(amount_idxs, date_idxs))
    return {"cols": cols, "pairs": pairs}


# ----------------------------- lookups -------------------------------------
async def resolve_actor(session, explicit: UUID | None) -> UUID | None:
    if explicit:
        return explicit
    for role in (UserRole.ACCOUNTANT, UserRole.SUPERADMIN):
        uid = await session.scalar(
            text("SELECT id FROM users WHERE role = :r AND is_active = true "
                 "ORDER BY created_at LIMIT 1"),
            {"r": role.value},
        )
        if uid:
            return uid
    return None


async def resolve_method(session, code: str | None) -> UUID | None:
    q = (
        "SELECT di.id, di.code FROM dictionary_items di "
        "JOIN dictionary_types dt ON dt.id = di.type_id "
        "WHERE dt.code = 'payment_methods'"
    )
    rows = (await session.execute(text(q))).all()
    if not rows:
        return None
    by_code = {(r.code or "").lower(): r.id for r in rows}
    if code:
        return by_code.get(code.lower())
    for pref in ("bank", "transfer", "pul_kochirish", "o_tkazma", "otkazma", "naqd", "cash"):
        if pref in by_code:
            return by_code[pref]
    return rows[0].id


async def find_contract(session, *, pinfl: str, passport: str):
    """Active (non-cancelled) contract for the applicant, preferring signed."""
    q = text(
        "SELECT c.id, c.status::text AS status, c.total_amount, c.paid_amount, "
        "       ap.last_name, ap.first_name "
        "FROM contracts c "
        "JOIN applications a ON a.id = c.application_id "
        "JOIN applicants ap ON ap.id = a.applicant_id "
        "WHERE c.status <> 'cancelled' AND ("
        "   (:pinfl <> '' AND ap.pinfl = :pinfl) OR "
        "   (:passport <> '' AND regexp_replace(upper(ap.passport_series),'[^A-Z0-9]','','g') = :passport) "
        ") "
        "ORDER BY (c.status = 'signed') DESC, c.created_at DESC LIMIT 1"
    )
    return (await session.execute(q, {"pinfl": pinfl, "passport": passport})).first()


async def payment_exists(session, contract_id, amount: Decimal, dt: datetime) -> bool:
    q = text(
        "SELECT 1 FROM payments WHERE contract_id = :cid AND status = 'confirmed' "
        "AND amount = :amt AND paid_at::date = :d LIMIT 1"
    )
    return (await session.execute(
        q, {"cid": contract_id, "amt": amount, "d": dt.date()}
    )).first() is not None


# ----------------------------- main ----------------------------------------
async def import_one(*, contract_id: UUID, amount: Decimal, dt: datetime,
                     method_id: UUID, actor_id: UUID | None) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            svc = PaymentsService(session)
            p = await svc.create(
                PaymentCreate(
                    contract_id=contract_id,
                    amount=amount,
                    payment_method_id=method_id,
                    notes="Excel import (buxgalteriya)",
                ),
                registered_by_id=actor_id,
            )
            await svc.confirm(p.id, PaymentConfirm(paid_at=dt))


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--file", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--method-code", default=None)
    ap.add_argument("--actor-id", type=UUID, default=None)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    import openpyxl
    wb = openpyxl.load_workbook(args.file, read_only=True, data_only=True)
    ws = wb[args.sheet] if args.sheet else wb.worksheets[0]

    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    m = map_columns(list(header))
    cols, pairs = m["cols"], m["pairs"]
    if cols["pinfl"] is None and cols["passport"] is None:
        raise SystemExit("PINFL/Passport ustuni topilmadi — sarlavhalarni tekshiring.")
    if not pairs:
        raise SystemExit("(To'lov summasi, To'lov sanasi) ustunlari topilmadi.")

    async with async_session_factory() as s:
        actor_id = await resolve_actor(s, args.actor_id)
        method_id = await resolve_method(s, args.method_code)
    if method_id is None:
        raise SystemExit("To'lov usuli (payment_methods) topilmadi — dictionaryni tekshiring.")

    print(f"Fayl:        {args.file}")
    print(f"Dry-run:     {args.dry_run}")
    print(f"Actor:       {actor_id}")
    print(f"Method:      {method_id}")
    print(f"To'lov juftliklari (ustunlar): {pairs}")
    print("=" * 66)

    stat = {"rows": 0, "no_contract": 0, "pairs_seen": 0,
            "inserted": 0, "already": 0, "bad": 0, "errors": 0}
    inserted = 0

    async with async_session_factory() as look:
        for r in rows:
            if r is None or all(c is None or c == "" for c in r):
                continue
            stat["rows"] += 1
            pinfl = _digits(r[cols["pinfl"]]) if cols["pinfl"] is not None else ""
            passport = re.sub(r"[^A-Z0-9]", "", str(r[cols["passport"]] or "").upper()) if cols["passport"] is not None else ""
            fio = str(r[cols["fio"]] or "") if cols["fio"] is not None else ""

            ct = await find_contract(look, pinfl=pinfl, passport=passport)
            if not ct:
                stat["no_contract"] += 1
                print(f"  [SHARTNOMA YO'Q] {fio[:32]:32} pinfl={pinfl} pass={passport}")
                continue

            for a_idx, d_idx in pairs:
                amount = parse_amount(r[a_idx]) if a_idx < len(r) else None
                dt = parse_date(r[d_idx]) if d_idx < len(r) else None
                if amount is None or dt is None:
                    if (r[a_idx] if a_idx < len(r) else None) or (r[d_idx] if d_idx < len(r) else None):
                        stat["bad"] += 1
                    continue
                stat["pairs_seen"] += 1

                if await payment_exists(look, ct.id, amount, dt):
                    stat["already"] += 1
                    continue

                if args.dry_run:
                    stat["inserted"] += 1
                    print(f"  [+] {fio[:28]:28} {amount:>12,.0f}  {dt.date()}  (contract {ct.status})")
                else:
                    try:
                        await import_one(contract_id=ct.id, amount=amount, dt=dt,
                                         method_id=method_id, actor_id=actor_id)
                        stat["inserted"] += 1
                        print(f"  ✓ {fio[:28]:28} {amount:>12,.0f}  {dt.date()}")
                    except Exception as exc:  # noqa: BLE001
                        stat["errors"] += 1
                        print(f"  ✗ {fio[:28]:28} {amount:>12,.0f}  {dt.date()} -> {exc}")

                inserted += 1
                if args.limit and inserted >= args.limit:
                    print(f"\n--- --limit {args.limit} ga yetdi, to'xtatildi. ---")
                    _summary(stat, args.dry_run)
                    return

    _summary(stat, args.dry_run)


def _summary(stat: dict, dry: bool) -> None:
    print("=" * 66)
    verb = "kiritiladi" if dry else "kiritildi"
    print(f"Qatorlar:            {stat['rows']}")
    print(f"Shartnoma topilmadi: {stat['no_contract']}")
    print(f"To'lov juftliklari:  {stat['pairs_seen']}")
    print(f"Yangi to'lov ({verb}): {stat['inserted']}")
    print(f"Allaqachon bor (skip): {stat['already']}")
    print(f"Buzuq summa/sana:    {stat['bad']}")
    print(f"Xatolar:             {stat['errors']}")


if __name__ == "__main__":
    asyncio.run(main())
