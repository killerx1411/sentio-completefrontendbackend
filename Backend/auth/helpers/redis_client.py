"""Redis client helper with in-memory fallback for development and tests."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

_redis_client: Any = None
_memory_store: dict[str, tuple[str, float]] = {}


class RedisUnavailableError(RuntimeError):
    """Production requires shared Redis and it could not be reached."""


def _production() -> bool:
    return os.environ.get("FLASK_ENV", "").strip().lower() == "production"


def get_redis_client():
    """Return a Redis client, or None when the in-memory fallback is allowed.

    The fallback is per-process, so on Cloud Run (many instances, many gunicorn
    workers) it does not actually share the state it is standing in for —
    lockout counters and one-time-use markers would be enforced only within one
    worker. Outside production that is an acceptable convenience; in production
    it is a security hole dressed as a working feature, so we raise instead.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        if _production():
            raise RedisUnavailableError(
                "REDIS_URL must be set in production; the in-memory fallback is "
                "per-process and does not share state across Cloud Run instances"
            )
        return None

    try:
        import redis

        client = redis.from_url(url, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        if _production():
            logger.error("Redis unavailable in production: %s", exc)
            raise RedisUnavailableError(f"Redis unavailable: {exc}") from exc
        logger.warning("Redis unavailable, using in-memory store: %s", exc)
        return None


def redis_set(key: str, value: str, ttl_seconds: int) -> None:
    client = get_redis_client()
    if client:
        client.setex(key, ttl_seconds, value)
        return
    _memory_store[key] = (value, time.time() + ttl_seconds)


def redis_get(key: str) -> str | None:
    client = get_redis_client()
    if client:
        val = client.get(key)
        return val if val else None
    entry = _memory_store.get(key)
    if not entry:
        return None
    value, expires = entry
    if time.time() > expires:
        _memory_store.pop(key, None)
        return None
    return value


def redis_delete(key: str) -> None:
    client = get_redis_client()
    if client:
        client.delete(key)
        return
    _memory_store.pop(key, None)


def redis_clear_memory() -> None:
    """Test helper to reset in-memory Redis fallback."""
    _memory_store.clear()
