"""Async worker that drains the CRM retry queue.

Lifecycle
---------
- `start()` schedules a long-running task on the current event loop.
- The task polls Redis every `poll_interval` seconds for due entries.
- For each entry, payload is re-validated against its Pydantic schema and sent
  via `CrmClient`. On failure, the entry is rescheduled with exponential
  backoff or moved to the DLQ once `MAX_ATTEMPTS` is reached.

Scaling
-------
For a single backend container this is sufficient. For HA, run a dedicated
worker container and disable it on the API container — the queue itself is
already concurrency-safe (atomic claim).
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

from app.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.integrations.crm.client import CrmClient, CrmResult
from app.integrations.crm.queue import (
    MAX_ATTEMPTS,
    CrmQueue,
    backoff_for,
)
from app.integrations.crm.schemas import (
    ApplicantLead,
    ApplicantStatusUpdate,
    ContractCreatedEvent,
)

logger = get_logger("crm.worker")


# ---------- Event dispatch table ----------
_EVENT_TYPES: dict[str, type] = {
    "applicant_lead": ApplicantLead,
    "applicant_status": ApplicantStatusUpdate,
    "contract_signed": ContractCreatedEvent,
}


async def _send(client: CrmClient, event_type: str, payload) -> CrmResult:
    if event_type == "applicant_lead":
        return await client.send_applicant_lead(payload)
    if event_type == "applicant_status":
        return await client.update_applicant_status(payload)
    if event_type == "contract_signed":
        return await client.notify_contract_signed(payload)
    return CrmResult(success=False, error=f"unknown_event:{event_type}")


class CrmWorker:
    def __init__(self, *, poll_interval: float = 5.0, batch_size: int = 10) -> None:
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    # ---------- public lifecycle ----------
    def start(self) -> asyncio.Task:
        if self._task and not self._task.done():
            return self._task
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="crm-worker")
        logger.info("crm.worker.started", poll_interval=self.poll_interval)
        return self._task

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop.set()
        try:
            await asyncio.wait_for(self._task, timeout=10.0)
        except asyncio.TimeoutError:
            self._task.cancel()
            logger.warning("crm.worker.stop_timeout")
        logger.info("crm.worker.stopped")

    # ---------- internal ----------
    async def _run(self) -> None:
        redis = get_redis()
        queue = CrmQueue(redis)
        client = CrmClient(redis=redis)

        while not self._stop.is_set():
            try:
                items = await queue.claim_due(self.batch_size)
                for item in items:
                    await self._dispatch(item, queue, client)
            except Exception as exc:  # noqa: BLE001 — keep worker alive on any error
                logger.exception("crm.worker.iteration_error", error=str(exc))

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                pass

    async def _dispatch(
        self,
        item: dict[str, Any],
        queue: CrmQueue,
        client: CrmClient,
    ) -> None:
        event_type = item.get("event", "")
        schema_cls = _EVENT_TYPES.get(event_type)
        if schema_cls is None:
            logger.warning("crm.worker.unknown_event", event=event_type, item_id=item.get("id"))
            await queue.move_to_dlq(item, error=f"unknown_event:{event_type}")
            return

        # Validate payload (catches schema drift between enqueue + dispatch)
        try:
            payload = schema_cls.model_validate(item.get("payload"))
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "crm.worker.invalid_payload",
                event=event_type,
                item_id=item.get("id"),
                error=str(exc),
            )
            await queue.move_to_dlq(item, error=f"invalid_payload:{exc!s}")
            return

        # If CRM is disabled (no creds), keep entries pending so they're not
        # lost — but back off aggressively so we don't spin.
        if not client.enabled:
            await queue.reschedule(item, delay=300, error="crm_disabled")
            return

        try:
            result = await _send(client, event_type, payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "crm.worker.send_exception",
                event=event_type,
                item_id=item.get("id"),
                error=str(exc),
            )
            await self._on_failure(item, queue, error=str(exc))
            return

        if not result.success:
            await self._on_failure(item, queue, error=result.error or "unknown")
            return

        logger.info(
            "crm.worker.delivered",
            event=event_type,
            item_id=item.get("id"),
            crm_id=result.crm_id,
        )

    async def _on_failure(
        self,
        item: dict[str, Any],
        queue: CrmQueue,
        *,
        error: str,
    ) -> None:
        prior_attempts = int(item.get("attempts", 0))
        # `reschedule` increments attempts; we compare against the post-increment value.
        if prior_attempts + 1 >= MAX_ATTEMPTS:
            await queue.move_to_dlq(item, error=error)
            logger.warning(
                "crm.worker.dlq",
                event=item.get("event"),
                item_id=item.get("id"),
                attempts=prior_attempts + 1,
                error=error,
            )
            return

        delay = backoff_for(prior_attempts)
        await queue.reschedule(item, delay=delay, error=error)
        logger.info(
            "crm.worker.rescheduled",
            event=item.get("event"),
            item_id=item.get("id"),
            attempt=prior_attempts + 1,
            delay=delay,
            error=error,
        )


# Singleton — created once at app startup.
crm_worker: CrmWorker | None = None


def get_worker() -> CrmWorker:
    global crm_worker
    if crm_worker is None:
        crm_worker = CrmWorker(poll_interval=getattr(settings, "crm_worker_poll_seconds", 5.0))
    return crm_worker
