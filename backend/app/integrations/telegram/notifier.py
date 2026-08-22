"""Outbound push to the Telegram notification bot.

The bot runs as a host systemd service OUTSIDE docker; when a new application
is created we POST its display payload to the bot's ingest endpoint, which
then posts it to the operators' group with the ✅/❌ HEMIS buttons.

Best-effort: fired as a FastAPI BackgroundTask so it never blocks (or breaks)
the create request. Failures are logged, not raised — the bot reconciles
missed items separately.
"""

from __future__ import annotations

import httpx
from fastapi import BackgroundTasks

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("notify.bot")


async def _post(payload: dict) -> None:
    if not settings.notify_bot_url:
        return
    try:
        async with httpx.AsyncClient(timeout=settings.notify_bot_timeout_seconds) as client:
            resp = await client.post(
                settings.notify_bot_url,
                json=payload,
                headers={"X-Ingest-Secret": settings.notify_bot_secret},
            )
            resp.raise_for_status()
        logger.info("notify.sent", application_id=payload.get("application_id"))
    except Exception as exc:  # noqa: BLE001 — never break the user request
        logger.error(
            "notify.failed",
            application_id=payload.get("application_id"),
            error=str(exc),
        )


def enqueue_application_created(bg: BackgroundTasks, *, payload: dict) -> None:
    """Schedule the push after the response is sent. No-op if unconfigured."""
    if not settings.notify_bot_url or not payload:
        return
    bg.add_task(_post, payload)
