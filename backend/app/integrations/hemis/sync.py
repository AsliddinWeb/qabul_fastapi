"""HEMIS existence-sync background job.

Iterates every application, asks HEMIS whether the applicant exists (by
passport PIN + number), and stamps applications.auto_hemis_check
('topildi' / 'topilmadi') + hemis_checked_at.

Runs across a 4-worker gunicorn fleet, so the lock AND the progress live in
Redis (never in-process memory): exactly ONE sync runs at a time (otherwise
two would double the HEMIS request rate and blow the 10 req/sec cap), and the
status endpoint reads the same progress from whichever worker serves it.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.db.session import async_session_factory
from app.integrations.hemis.client import HemisClient, extract_passport_number

log = get_logger("hemis.sync")

LOCK_KEY = "hemis:sync:lock"
STATE_KEY = "hemis:sync:state"
LOCK_TTL = 180  # seconds; refreshed while running so a dead worker frees it

# Keep a strong ref to the running task — asyncio only holds a weak ref, so an
# un-referenced background task can be garbage-collected mid-run.
_bg_tasks: set = set()


def _blank(**over) -> dict:
    s = {
        "running": False, "total": 0, "checked": 0,
        "found": 0, "not_found": 0, "skipped": 0, "errors": 0,
        "started_at": None, "finished_at": None, "error": None,
    }
    s.update(over)
    return s


async def get_state() -> dict:
    redis = get_redis()
    try:
        raw = await redis.get(STATE_KEY)
        state = json.loads(raw) if raw else _blank()
        # A worker crash leaves running=True but the lock expires — report it
        # as stopped so the UI can re-trigger instead of waiting forever.
        if state.get("running") and not await redis.exists(LOCK_KEY):
            state["running"] = False
            state["error"] = state.get("error") or "Sinxron uzilib qoldi (qayta urinib ko'ring)"
        return state
    finally:
        await redis.aclose()


async def _save(redis, state: dict) -> None:
    await redis.set(STATE_KEY, json.dumps(state))


async def start_sync() -> bool:
    """Acquire the Redis lock and launch the sync on this worker's loop.
    Returns False if a sync is already running (lock held)."""
    redis = get_redis()
    got = await redis.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL)
    await redis.aclose()
    if not got:
        return False
    task = asyncio.create_task(_run())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return True


async def _run() -> None:
    redis = get_redis()
    state = _blank(running=True, started_at=datetime.now(timezone.utc).isoformat())
    await _save(redis, state)
    try:
        client = HemisClient()
        if not client.configured:
            state["error"] = "HEMIS_API_TOKEN sozlanmagan"
            return

        from app.modules.applicants.models import Applicant
        from app.modules.applications.models import Application
        from sqlalchemy import select

        async with async_session_factory() as s:
            rows = (await s.execute(
                select(Application.id, Applicant.pinfl, Applicant.passport_series)
                .join(Applicant, Applicant.id == Application.applicant_id)
            )).all()
        state["total"] = len(rows)
        await _save(redis, state)

        interval = 1.0 / max(settings.hemis_rate_per_sec, 1.0)
        batch: list[tuple] = []
        async with httpx.AsyncClient(timeout=settings.hemis_timeout_seconds) as http:
            for app_id, pinfl, passport_series in rows:
                passport_number = extract_passport_number(passport_series)
                status: str | None = None
                if not pinfl or not passport_number:
                    state["skipped"] += 1
                else:
                    t0 = time.monotonic()
                    try:
                        found = await client.student_found(
                            http, pinfl=pinfl, passport_number=passport_number
                        )
                        status = "topildi" if found else "topilmadi"
                        state["found" if found else "not_found"] += 1
                    except Exception as exc:  # noqa: BLE001
                        state["errors"] += 1
                        log.error("hemis.check_failed", app_id=str(app_id), error=str(exc))
                    dt = time.monotonic() - t0
                    if dt < interval:
                        await asyncio.sleep(interval - dt)

                state["checked"] += 1
                if status is not None:
                    batch.append((app_id, status))
                if len(batch) >= 50:
                    await _flush(batch); batch = []
                if state["checked"] % 20 == 0:
                    await _save(redis, state)
                    await redis.expire(LOCK_KEY, LOCK_TTL)  # keep the lock alive
            if batch:
                await _flush(batch)
    except Exception as exc:  # noqa: BLE001
        state["error"] = str(exc)
        log.error("hemis.sync_failed", error=str(exc))
    finally:
        state["running"] = False
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        await _save(redis, state)
        await redis.delete(LOCK_KEY)
        await redis.aclose()


async def _flush(batch: list[tuple]) -> None:
    from sqlalchemy import update
    from app.modules.applications.models import Application
    now = datetime.now(timezone.utc)
    async with async_session_factory() as s:
        for app_id, status in batch:
            await s.execute(
                update(Application)
                .where(Application.id == app_id)
                .values(auto_hemis_check=status, hemis_checked_at=now)
            )
        await s.commit()
