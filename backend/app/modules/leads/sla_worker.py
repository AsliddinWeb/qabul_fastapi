"""SLA worker for leads.

Periodically scans for OPEN leads that haven't moved between stages for more
than `LEADS_SLA_HOURS` (default 72 = 3 days) and writes a single audit log
entry per lead per day so the dashboard / notification bell can surface them.

Each lead gets a `last_sla_alert_at` extra in its activities; we never
double-alert within 24h of the previous alert.

Started in app lifespan via `LeadSlaWorker.start()`.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.logging import get_logger
from app.modules.leads.models import LeadActivity
from app.modules.leads.repository import LeadActivityRepository, LeadRepository

logger = get_logger("leads.sla")


class LeadSlaWorker:
    def __init__(self, *, hours: int = 72, poll_seconds: float = 3600) -> None:
        self.hours = hours
        self.poll_seconds = poll_seconds
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="leads-sla-worker")
        logger.info("leads.sla.started", hours=self.hours, poll_seconds=self.poll_seconds)

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                logger.warning("leads.sla.stop_timeout")
            except Exception:
                pass

    async def _run(self) -> None:
        engine = create_async_engine(settings.database_url)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        try:
            while not self._stop.is_set():
                try:
                    async with Session() as s:
                        await self._tick(s)
                except Exception as exc:
                    logger.error("leads.sla.tick_failed", error=str(exc))
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.poll_seconds)
                except asyncio.TimeoutError:
                    pass
        finally:
            await engine.dispose()

    async def _tick(self, session) -> None:
        # Gunicorn runs N workers; each one would otherwise call this
        # method concurrently and produce N copies of every alert because
        # the dedup check below races. Hold a Redis lock for the duration
        # of the scan so only one worker actually emits — others see the
        # lock and skip the tick. Lock TTL is half the poll interval so
        # if a worker crashes the next cycle can still run.
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            lock_ttl = max(60, int(self.poll_seconds // 2))
            got = await redis.set(
                "leads.sla.tick_lock", "1", nx=True, ex=lock_ttl,
            )
            if not got:
                logger.debug("leads.sla.skipped_lock_held")
                return
        except Exception as exc:
            # Redis unreachable: fall through and run anyway — duplicate
            # alerts are better than NO alerts.
            logger.warning("leads.sla.lock_unavailable", error=str(exc))

        repo = LeadRepository(session)
        acts = LeadActivityRepository(session)

        stale = await repo.stale_open_leads(hours=self.hours)
        if not stale:
            return

        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(hours=24)
        alerted = 0
        for lead in stale:
            # Skip if we've already alerted within the last 24h.
            existing = (await session.scalars(
                select(LeadActivity)
                .where(
                    LeadActivity.lead_id == lead.id,
                    LeadActivity.action == "sla_alert",
                    LeadActivity.created_at > recent_cutoff,
                )
                .limit(1)
            )).first()
            if existing:
                continue

            days = max(1, int((now.timestamp() - lead.stage_entered_at.timestamp()) // 86400))
            await acts.create(
                lead_id=lead.id,
                user_id=None,
                action="sla_alert",
                comment=f"Lead {days} kun davomida bosqichda harakatsiz turibdi.",
                extra={"days_in_stage": days, "hours_threshold": self.hours},
            )
            alerted += 1

        if alerted:
            await session.commit()
            logger.info("leads.sla.alerted", count=alerted)


_worker: LeadSlaWorker | None = None


def get_sla_worker() -> LeadSlaWorker:
    global _worker
    if _worker is None:
        _worker = LeadSlaWorker(
            hours=getattr(settings, "leads_sla_hours", 72),
            poll_seconds=getattr(settings, "leads_sla_poll_seconds", 3600),
        )
    return _worker
