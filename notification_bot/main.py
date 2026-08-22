"""Entrypoint: runs the Telegram bot (polling) + the HTTP ingest server
together in one asyncio loop.

  • Telegram side  — handles the ✅/❌ button callbacks (with confirm step).
  • Ingest side    — receives the backend PUSH and posts new applications.
"""

from __future__ import annotations

import logging

from aiohttp import web
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot.api_client import ApiClient
from bot.config import load_config
from bot.handlers import cmd_chatid, on_callback
from bot.ingest import build_ingest_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("bot.main")


async def _post_init(application: Application) -> None:
    cfg = application.bot_data["cfg"]
    runner = web.AppRunner(build_ingest_app(application, cfg))
    await runner.setup()
    site = web.TCPSite(runner, cfg.ingest_host, cfg.ingest_port)
    await site.start()
    application.bot_data["ingest_runner"] = runner
    log.info("ingest server listening on %s:%s", cfg.ingest_host, cfg.ingest_port)


async def _post_shutdown(application: Application) -> None:
    runner = application.bot_data.get("ingest_runner")
    if runner is not None:
        await runner.cleanup()
        log.info("ingest server stopped")


def main() -> None:
    cfg = load_config()
    application = (
        Application.builder()
        .token(cfg.bot_token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    application.bot_data["cfg"] = cfg
    application.bot_data["api"] = ApiClient(cfg)

    application.add_handler(CommandHandler("id", cmd_chatid))
    application.add_handler(CallbackQueryHandler(on_callback))

    log.info("bot starting (polling)…")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
