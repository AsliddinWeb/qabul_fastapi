"""Message text + keyboards for the group notifications."""

from __future__ import annotations

from datetime import datetime
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

ADMISSION_TYPE = {
    "yangi_qabul": "1-kurs (Yangi qabul)",
    "perevod": "O'qishni ko'chirish",
    "ikkinchi_mutaxassislik": "2-mutaxassislik",
    "magistratura": "Magistratura",
}


def _e(v) -> str:
    return escape(str(v)) if v not in (None, "") else "—"


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y")
    except ValueError:
        return iso


def application_message(p: dict) -> str:
    """Build the HTML message for a newly-created application."""
    program_line = _e(p.get("program_name"))
    extra = " · ".join(x for x in [p.get("level_name"), p.get("form_name")] if x)
    if extra:
        program_line += f" <i>({escape(extra)})</i>"

    phones = [x for x in [p.get("phone"), p.get("additional_phone")] if x]
    phones_line = ", ".join(escape(x) for x in phones) or "—"

    lines = [
        "🆕 <b>Yangi ariza</b> — <code>{}</code>".format(_e(p.get("application_number"))),
        "",
        "👤 <b>{}</b>".format(_e(p.get("applicant_full_name"))),
        "🎫 Passport: <code>{}</code>".format(_e(p.get("passport_series"))),
        "🔢 PINFL: <code>{}</code>".format(_e(p.get("pinfl"))),
        "📅 Tug'ilgan: {}".format(_fmt_date(p.get("birth_date"))),
        "",
        "🎓 Yo'nalish: {}".format(program_line),
        "🏢 Filial: {}".format(_e(p.get("branch_name"))),
        "📚 Turi: {}".format(escape(ADMISSION_TYPE.get(p.get("admission_type") or "", p.get("admission_type") or "—"))),
        "",
        "📞 Telefon: {}".format(phones_line),
    ]
    if p.get("operator_name"):
        lines.append("👨‍💼 Operator: {}".format(_e(p.get("operator_name"))))
    return "\n".join(lines)


def decision_keyboard(application_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ HEMISga qo'shildi", callback_data=f"h:a:{application_id}"),
        InlineKeyboardButton("❌ Qo'shilmadi", callback_data=f"h:n:{application_id}"),
    ]])


def confirm_keyboard(action: str, application_id: str) -> InlineKeyboardMarkup:
    label = "qo'shildi" if action == "a" else "qo'shilmadi"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"Ha, {label}", callback_data=f"hc:{action}:{application_id}"),
        InlineKeyboardButton("Bekor", callback_data=f"hx:{application_id}"),
    ]])
