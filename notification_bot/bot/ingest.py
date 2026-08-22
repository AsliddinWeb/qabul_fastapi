"""HTTP ingest server — receives the backend PUSH for new applications and
posts them to the operators' group with the ✅/❌ HEMIS buttons.

Runs inside the PTB event loop (started from main.post_init) so it can use
the same `application.bot` to send messages.
"""

from __future__ import annotations

import logging

from aiohttp import web
from telegram.constants import ParseMode

from bot.formatting import application_message, decision_keyboard

log = logging.getLogger("bot.ingest")


def build_ingest_app(application, cfg) -> web.Application:
    async def handle(request: web.Request) -> web.Response:
        if request.headers.get("X-Ingest-Secret") != cfg.ingest_secret:
            return web.json_response({"error": "forbidden"}, status=403)
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return web.json_response({"error": "invalid json"}, status=400)

        app_id = payload.get("application_id")
        if not app_id:
            return web.json_response({"error": "application_id required"}, status=400)

        try:
            await application.bot.send_message(
                chat_id=cfg.group_chat_id,
                text=application_message(payload),
                parse_mode=ParseMode.HTML,
                reply_markup=decision_keyboard(str(app_id)),
                disable_web_page_preview=True,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("send_message failed for %s: %s", app_id, exc)
            return web.json_response({"error": "send failed"}, status=502)

        log.info("posted application %s to group", app_id)
        return web.json_response({"ok": True})

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    web_app = web.Application()
    web_app.router.add_post("/ingest", handle)
    web_app.router.add_get("/health", health)
    return web_app
