"""Inline-button callback handling with a confirm step.

Callback data (compact, ≤64 bytes):
  h:a:<id>   ✅ pressed  → show confirm buttons
  h:n:<id>   ❌ pressed  → show confirm buttons
  hc:a:<id>  confirmed ✅ → call API, finalize message
  hc:n:<id>  confirmed ❌ → call API, finalize message
  hx:<id>    cancel      → restore ✅/❌ buttons
"""

from __future__ import annotations

import logging
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.formatting import confirm_keyboard, decision_keyboard

log = logging.getLogger("bot.handlers")


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/id — reply with the current chat id (handy for GROUP_CHAT_ID setup)."""
    chat = update.effective_chat
    await update.effective_message.reply_text(f"chat_id: {chat.id}\ntype: {chat.type}")


def _presser_name(update: Update) -> str:
    u = update.callback_query.from_user
    name = " ".join(filter(None, [u.first_name, u.last_name])).strip()
    if u.username:
        name = f"{name} (@{u.username})" if name else f"@{u.username}"
    return name or str(u.id)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    parts = (q.data or "").split(":")
    kind = parts[0]

    # ── ✅/❌ pressed → replace with confirm buttons ──
    if kind == "h" and len(parts) == 3:
        action, app_id = parts[1], parts[2]
        await q.answer("Rostdan amalni tasdiqlaysizmi?")
        await q.edit_message_reply_markup(reply_markup=confirm_keyboard(action, app_id))
        return

    # ── Cancel → restore the original ✅/❌ buttons ──
    if kind == "hx" and len(parts) == 2:
        app_id = parts[1]
        await q.answer("Bekor qilindi")
        await q.edit_message_reply_markup(reply_markup=decision_keyboard(app_id))
        return

    # ── Confirmed → write to the system, then finalize the message ──
    if kind == "hc" and len(parts) == 3:
        action, app_id = parts[1], parts[2]
        status = "qoshildi" if action == "a" else "qoshilmadi"
        who = _presser_name(update)
        api = context.application.bot_data["api"]
        try:
            await api.set_hemis_status(app_id, status=status, marked_by=who)
        except Exception as exc:  # noqa: BLE001
            log.error("set_hemis failed for %s: %s", app_id, exc)
            await q.answer("Xatolik — qayta urinib ko'ring", show_alert=True)
            await q.edit_message_reply_markup(reply_markup=decision_keyboard(app_id))
            return

        await q.answer("Saqlandi")
        emoji = "✅" if action == "a" else "❌"
        label = "HEMISga qo'shildi" if action == "a" else "HEMISga qo'shilmadi"
        stamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        original = q.message.text_html or q.message.text or ""
        new_text = f"{original}\n\n{emoji} <b>{label}</b> — {who}, {stamp}"
        await q.edit_message_text(new_text, parse_mode=ParseMode.HTML, reply_markup=None)
        return

    await q.answer()
