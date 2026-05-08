"""Redis-backed retry queue for CRM events.

Storage layout
--------------
- ZSET `crm:pending`  — score = unix epoch when the entry becomes due
- LIST `crm:dlq`      — JSON-encoded items that exceeded MAX_ATTEMPTS

Entry shape (JSON)
------------------
{
    "id":             "<uuid>",
    "event":          "applicant_lead" | "applicant_status" | "contract_signed",
    "payload":        {...},
    "attempts":       0,
    "first_seen_at":  <unix>,
    "last_error":     "...",      # optional, set on failure
    "dlq_at":         <unix>,     # only when in DLQ
}

Atomicity
---------
`claim_due` uses a Lua script so that "fetch + remove" happens in a single
Redis round-trip — even with multiple workers, an entry is dispatched at most
once per attempt window.
"""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

from redis.asyncio import Redis

PENDING_KEY = "crm:pending"
DLQ_KEY = "crm:dlq"

# Backoff ladder (seconds): 1m → 2m → 4m → 8m → 16m → 30m
ATTEMPT_DELAYS: list[int] = [60, 120, 240, 480, 960, 1800]
# Total tries: 1 initial attempt + len(ATTEMPT_DELAYS) retries = 7
MAX_ATTEMPTS = len(ATTEMPT_DELAYS) + 1


_CLAIM_DUE_LUA = """
local items = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, ARGV[2])
if #items > 0 then
    redis.call('ZREM', KEYS[1], unpack(items))
end
return items
"""


def backoff_for(attempts_already_made: int) -> int:
    """Returns delay before the next retry."""
    idx = min(attempts_already_made, len(ATTEMPT_DELAYS) - 1)
    return ATTEMPT_DELAYS[idx]


class CrmQueue:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    # ---------- enqueue ----------
    async def enqueue(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        when: int | None = None,
    ) -> str:
        item: dict[str, Any] = {
            "id": uuid4().hex,
            "event": event_type,
            "payload": payload,
            "attempts": 0,
            "first_seen_at": int(time.time()),
        }
        score = when if when is not None else int(time.time())
        await self.redis.zadd(PENDING_KEY, {json.dumps(item): score})
        return item["id"]

    # ---------- worker primitives ----------
    async def claim_due(self, max_count: int = 10) -> list[dict[str, Any]]:
        now = int(time.time())
        raw_items = await self.redis.eval(
            _CLAIM_DUE_LUA, 1, PENDING_KEY, str(now), str(max_count)
        )
        return [json.loads(s) for s in (raw_items or [])]

    async def reschedule(
        self,
        item: dict[str, Any],
        *,
        delay: int,
        error: str | None = None,
    ) -> None:
        item["attempts"] = int(item.get("attempts", 0)) + 1
        if error is not None:
            item["last_error"] = error
        when = int(time.time()) + delay
        await self.redis.zadd(PENDING_KEY, {json.dumps(item): when})

    async def move_to_dlq(self, item: dict[str, Any], *, error: str) -> None:
        item["last_error"] = error
        item["dlq_at"] = int(time.time())
        await self.redis.lpush(DLQ_KEY, json.dumps(item))

    # ---------- introspection / admin ----------
    async def pending_count(self) -> int:
        return await self.redis.zcard(PENDING_KEY) or 0

    async def dlq_count(self) -> int:
        return await self.redis.llen(DLQ_KEY) or 0

    async def list_pending(self, limit: int = 50) -> list[dict[str, Any]]:
        items = await self.redis.zrange(PENDING_KEY, 0, limit - 1, withscores=True)
        out: list[dict[str, Any]] = []
        for raw, score in items:
            data = json.loads(raw)
            data["next_attempt_at"] = int(score)
            out.append(data)
        return out

    async def list_dlq(self, limit: int = 100) -> list[dict[str, Any]]:
        items = await self.redis.lrange(DLQ_KEY, 0, limit - 1)
        return [json.loads(s) for s in items]

    async def requeue_dlq(self, item_id: str) -> bool:
        items = await self.redis.lrange(DLQ_KEY, 0, -1)
        for raw in items:
            data = json.loads(raw)
            if data.get("id") == item_id:
                await self.redis.lrem(DLQ_KEY, 1, raw)
                data["attempts"] = 0
                data.pop("last_error", None)
                data.pop("dlq_at", None)
                await self.redis.zadd(PENDING_KEY, {json.dumps(data): int(time.time())})
                return True
        return False

    async def drop_dlq(self, item_id: str) -> bool:
        items = await self.redis.lrange(DLQ_KEY, 0, -1)
        for raw in items:
            if json.loads(raw).get("id") == item_id:
                await self.redis.lrem(DLQ_KEY, 1, raw)
                return True
        return False
