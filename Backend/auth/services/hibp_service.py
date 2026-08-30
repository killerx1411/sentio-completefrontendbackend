"""Have I Been Pwned password check with circuit breaker and cache."""

from __future__ import annotations

import hashlib
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from enum import Enum
from typing import ClassVar

from auth.config import get_config
from auth.helpers.audit_helper import log_activity

logger = logging.getLogger(__name__)
config = get_config()


class HIBPResult(Enum):
    CLEAN = "clean"
    BREACHED = "breached"
    UNAVAILABLE = "unavailable"


class HIBPService:
    _circuit_open: ClassVar[bool] = False
    _circuit_open_until: ClassVar[datetime | None] = None
    _cache: ClassVar[dict[str, tuple[HIBPResult, datetime]]] = {}
    CIRCUIT_BREAKER_TIMEOUT = 60

    @classmethod
    def check_password(cls, password: str) -> HIBPResult:
        if cls._circuit_open and cls._circuit_open_until:
            if datetime.utcnow() < cls._circuit_open_until:
                return HIBPResult.UNAVAILABLE
            cls._circuit_open = False

        try:
            result = cls._query_hibp(password)
            cls._circuit_open = False
            return result
        except (TimeoutError, urllib.error.URLError, ConnectionError, OSError) as exc:
            logger.warning("HIBP unavailable: %s", exc)
            cls._circuit_open = True
            cls._circuit_open_until = datetime.utcnow() + timedelta(
                seconds=cls.CIRCUIT_BREAKER_TIMEOUT
            )
            return HIBPResult.UNAVAILABLE

    @classmethod
    def _query_hibp(cls, password: str) -> HIBPResult:
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        cache_key = prefix
        cached = cls._cache.get(cache_key)
        if cached:
            suffixes, expires = cached
            if datetime.utcnow() < expires:
                return (
                    HIBPResult.BREACHED if suffix in suffixes else HIBPResult.CLEAN
                )

        body_suffixes = cls._fetch_range(prefix)
        cls._cache[cache_key] = (
            body_suffixes,
            datetime.utcnow() + timedelta(seconds=config.HIBP_CACHE_TTL_SECONDS),
        )
        return HIBPResult.BREACHED if suffix in body_suffixes else HIBPResult.CLEAN

    @classmethod
    def _fetch_range(cls, prefix: str) -> set[str]:
        url = f"https://api.pwnedpasswords.com/range/{prefix}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "SentioMind-Auth"}
        )
        with urllib.request.urlopen(req, timeout=config.HIBP_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
        suffixes = set()
        for line in body.splitlines():
            if ":" in line:
                suffixes.add(line.split(":")[0])
        return suffixes

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
        cls._circuit_open = False
        cls._circuit_open_until = None


def validate_password_not_breached(
    password: str, user_id: int | None = None
) -> dict | None:
    """Return error dict for API layer, or None if password is acceptable."""
    result = HIBPService.check_password(password)
    if result == HIBPResult.BREACHED:
        return {
            "error": "Password found in a known data breach",
            "status": 400,
        }
    if result == HIBPResult.UNAVAILABLE:
        if config.STRICT_PASSWORD_BREACH_CHECK:
            return {
                "error": "Cannot verify password safety, please try again",
                "status": 503,
            }
        log_activity(
            user_id,
            "hibp_check_skipped",
            "Security",
            "reason=service_unavailable",
            severity="WARNING",
        )
    return None
