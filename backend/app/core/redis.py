"""Async Redis client (process-wide pool).

Used for: OTP storage, rate limits, Eskiz token cache, future caching needs.
"""

from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from app.config import settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


def get_redis() -> Redis:
    """FastAPI-compatible factory. Returns a client that uses the shared pool."""
    return Redis(connection_pool=get_pool())


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.disconnect(inuse_connections=True)
        _pool = None
