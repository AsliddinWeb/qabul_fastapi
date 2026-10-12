"""Excel builders for the Tizim daftari export.

Two variants (chosen from the dropdown on the page):

  dates       — "Sanalar kesimida": events grouped under a per-day header
                row, plus a "Kunlik xulosa" sheet (day × event-type counts).
  applicants  — "Abituriyentlar kesimida": a "Yo'l xulosasi" sheet with one
                row per applicant and the milestone dates, plus "Batafsil
                yo'l" with each applicant's full path under a header row.

Uses openpyxl's write-only (streaming) mode: tens of thousands of rows
build in seconds instead of minutes. Trade-off: no merged cells — group
header rows are tinted across the full width instead.
"""

from __future__ import annotations

import io
from collections import OrderedDict
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.modules.journal.service import EVENT_CODES, EVENT_LABELS, STATUS_LABELS

_WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

_HEAD_FILL = PatternFill("solid", fgColor="4F46E5")
_HEAD_FONT = Font(bold=True, color="FFFFFF", size=11)
_HEAD_ALIGN = Alignment(horizontal="left", vertical="center", wrap_text=True)
_GROUP_FILL = PatternFill("solid", fgColor="E0E7FF")
_GROUP_FONT = Font(bold=True, color="1E1B4B", size=11)
_TITLE_FONT = Font(bold=True, size=14)
_BOLD = Font(bold=True)
_TOP_WRAP = Alignment(vertical="top", wrap_text=True)

# Light tint per event type so the eye can scan a long sheet.
_EVENT_FILL = {
    code: PatternFill("solid", fgColor=color)
    for code, color in {
        "registered": "F1F5F9",
        "registered_by_staff": "F1F5F9",
        "application_submitted": "FEF3C7",
        "status_changed": "E0F2FE",
        "contract_created": "DCFCE7",
        "contract_renewed": "D1FAE5",
        "contract_signed": "BBF7D0",
        "contract_cancelled": "FFE4E6",
    }.items()
}


def _fmt_dt(d: datetime) -> str:
    return d.strftime("%d.%m.%Y %H:%M")


def _fmt_d(d: datetime | date | None) -> str:
    return d.strftime("%d.%m.%Y") if d else ""


def _c(ws, value, *, font=None, fill=None, align=None) -> WriteOnlyCell:
    cell = WriteOnlyCell(ws, value=value)
    if font is not None:
        cell.font = font
    if fill is not None:
        cell.fill = fill
    if align is not None:
        cell.alignment = align
    return cell


def _new_sheet(wb: Workbook, name: str, widths: list[int], freeze: str = "A3"):
    ws = wb.create_sheet(name)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = freeze  # rows 1-2 = title, header
    return ws


def _title_rows(ws, title: str, headers: list[str]) -> None:
    ws.append([_c(ws, title, font=_TITLE_FONT)])
    ws.append([_c(ws, h, font=_HEAD_FONT, fill=_HEAD_FILL, align=_HEAD_ALIGN) for h in headers])


def _group_row(ws, text: str, ncols: int) -> None:
    ws.append([_c(ws, text, font=_GROUP_FONT, fill=_GROUP_FILL)]
              + [_c(ws, None, fill=_GROUP_FILL) for _ in range(ncols - 1)])


def _event_row(ws, values: list, code: str, event_col: int) -> None:
    fill = _EVENT_FILL.get(code)
    ws.append([
        _c(ws, v, align=_TOP_WRAP, fill=fill if i == event_col else None)
        for i, v in enumerate(values, start=1)
    ])


def _save(wb: Workbook) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- by dates
def build_by_dates(events: list[dict]) -> bytes:
    wb = Workbook(write_only=True)

    by_day: OrderedDict[date, list[dict]] = OrderedDict()
    for e in events:
        by_day.setdefault(e["at"].date(), []).append(e)

    headers = ["№", "Vaqt", "F.I.O", "JSHSHIR", "Telefon", "Hodisa", "Tafsilot",
               "Yo'nalish", "Kim tomonidan"]
    ws = _new_sheet(wb, "Sanalar kesimida", [6, 8, 34, 17, 15, 24, 48, 36, 28])
    _title_rows(ws, "Tizim daftari — sanalar kesimida", headers)
    n = 0
    for day, items in by_day.items():
        _group_row(ws, f"{day.strftime('%d.%m.%Y')} · {_WEEKDAYS[day.weekday()]} — {len(items)} ta hodisa",
                   len(headers))
        for e in items:
            n += 1
            _event_row(ws, [n, e["at"].strftime("%H:%M"), e["full_name"], e["pinfl"], e["phone"],
                            e["event"], e["detail"], e["program"], e["actor"]],
                       e["code"], event_col=6)

    # ---- daily summary
    sum_headers = ["Sana", "Hafta kuni"] + [EVENT_LABELS[c] for c in EVENT_CODES] + ["Jami"]
    ss = _new_sheet(wb, "Kunlik xulosa", [12, 12] + [16] * len(EVENT_CODES) + [10])
    _title_rows(ss, "Kunlik xulosa", sum_headers)
    totals = {c: 0 for c in EVENT_CODES}
    for day, items in by_day.items():
        counts = {c: 0 for c in EVENT_CODES}
        for e in items:
            counts[e["code"]] = counts.get(e["code"], 0) + 1
        for c in EVENT_CODES:
            totals[c] += counts[c]
        ss.append([day.strftime("%d.%m.%Y"), _WEEKDAYS[day.weekday()]]
                  + [counts[c] or "" for c in EVENT_CODES] + [len(items)])
    ss.append([_c(ss, v, font=_BOLD, fill=_GROUP_FILL)
               for v in ["JAMI", ""] + [totals[c] for c in EVENT_CODES] + [sum(totals.values())]])
    return _save(wb)


# ----------------------------------------------------------- by applicants
def build_by_applicants(events: list[dict]) -> bytes:
    wb = Workbook(write_only=True)

    # Group, preserving the service's (name, applicant, time) ordering.
    people: OrderedDict[str, list[dict]] = OrderedDict()
    for e in events:
        people.setdefault(str(e["applicant_id"]), []).append(e)

    # ---- sheet 1: path summary (one row per applicant)
    headers = ["№", "F.I.O", "JSHSHIR", "Telefon", "Ro'yxatdan o'tgan", "Kim ro'yxatga olgan",
               "Ariza topshirgan", "Yo'nalish", "Ariza holati", "Shartnoma olgan",
               "Shartnoma raqami", "Imzolangan", "Oxirgi yangilanish", "Bekor qilingan",
               "Hodisalar soni"]
    ws = _new_sheet(wb, "Yo'l xulosasi", [6, 34, 17, 15, 14, 26, 14, 36, 18, 14, 18, 14, 16, 14, 10])
    _title_rows(ws, "Tizim daftari — abituriyentlar kesimida (xulosa)", headers)

    for i, items in enumerate(people.values(), start=1):
        first = items[0]
        reg = next((e for e in items if e["code"] in ("registered", "registered_by_staff")), None)
        subm = next((e for e in items if e["code"] == "application_submitted"), None)
        status = None
        for e in items:
            if e["code"] == "application_submitted" and status is None:
                status = "topshirildi"
            if e["code"] == "status_changed" and e["to_status"]:
                status = e["to_status"]
        got = next((e for e in items if e["code"] == "contract_created"), None)
        renewed = [e for e in items if e["code"] == "contract_renewed"]
        signed = [e for e in items if e["code"] == "contract_signed"]
        cancelled = [e for e in items if e["code"] == "contract_cancelled"]
        contract_events = [e for e in items if e["contract_number"]]
        ws.append([_c(ws, v, align=_TOP_WRAP) for v in [
            i, first["full_name"], first["pinfl"], first["phone"],
            _fmt_d(reg["at"]) if reg else "",
            ("O'zi" if reg["code"] == "registered" else reg["actor"]) if reg else "",
            _fmt_d(subm["at"]) if subm else "",
            subm["program"] if subm else "",
            STATUS_LABELS.get(status, status or ""),
            _fmt_d(got["at"]) if got else "",
            contract_events[-1]["contract_number"] if contract_events else "",
            _fmt_d(signed[-1]["at"]) if signed else "",
            _fmt_d(renewed[-1]["at"]) if renewed else "",
            _fmt_d(cancelled[-1]["at"]) if cancelled else "",
            len(items),
        ]])

    # ---- sheet 2: detailed path per applicant
    d_headers = ["№", "Sana va vaqt", "Hodisa", "Tafsilot", "Yo'nalish", "Kim tomonidan"]
    ds = _new_sheet(wb, "Batafsil yo'l", [6, 17, 24, 52, 36, 30])
    _title_rows(ds, "Tizim daftari — abituriyentlar kesimida (batafsil)", d_headers)
    for i, items in enumerate(people.values(), start=1):
        p = items[0]
        _group_row(ds, f"{i}. {p['full_name']} · JSHSHIR {p['pinfl'] or '—'} · "
                       f"{p['phone'] or '—'} — {len(items)} ta hodisa", len(d_headers))
        for j, e in enumerate(items, start=1):
            _event_row(ds, [j, _fmt_dt(e["at"]), e["event"], e["detail"], e["program"], e["actor"]],
                       e["code"], event_col=3)
    return _save(wb)
