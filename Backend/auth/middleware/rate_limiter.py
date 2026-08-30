"""Flask-Limiter integration with per-route limits and audit logging."""

from __future__ import annotations

import logging
from typing import Callable

from flask import Flask, g, jsonify, request
from flask_limiter import Limiter

from auth.helpers.audit_helper import log_activity
from auth.helpers.request_helper import get_client_ip

logger = logging.getLogger(__name__)


def _get_real_ip() -> str:
    return get_client_ip()


def _authenticated_key() -> str:
    """Rate-limit key: user id when authenticated, else client IP."""
    try:
        user = getattr(g, "user", None)
        if user and user.get("sub"):
            return f"user:{user['sub']}"
    except RuntimeError:
        pass
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from auth.helpers.jwt_helper import (
                TokenExpiredError,
                TokenInvalidError,
                decode_token,
            )

            payload = decode_token(auth.split(" ", 1)[1].strip())
            if payload.get("type") == "access" and payload.get("sub"):
                return f"user:{payload['sub']}"
        except (TokenExpiredError, TokenInvalidError):
            pass
    return _get_real_ip()


def _on_rate_limit_breach(_request_limit) -> None:
    user_id = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from auth.helpers.jwt_helper import (
                TokenExpiredError,
                TokenInvalidError,
                decode_token,
            )

            payload = decode_token(auth.split(" ", 1)[1].strip())
            user_id = payload.get("sub")
        except (TokenExpiredError, TokenInvalidError):
            pass

    log_activity(
        user_id,
        "rate_limit_exceeded",
        "Security",
        f"endpoint={request.path}",
        ip_address=_get_real_ip(),
        severity="WARNING",
    )


limiter = Limiter(
    key_func=_get_real_ip,
    default_limits=["200/minute"],
    strategy="fixed-window",
    headers_enabled=True,
    on_breach=_on_rate_limit_breach,
)


def init_rate_limiter(app: Flask) -> Limiter:
    """Bind limiter to Flask app using config storage URI."""
    app.config.setdefault("RATELIMIT_STORAGE_URI", "memory://")
    app.config.setdefault("RATELIMIT_STRATEGY", "fixed-window-elastic-expiry")
    app.config.setdefault("RATELIMIT_HEADERS_ENABLED", True)
    app.config.setdefault("RATELIMIT_DEFAULT", "200/minute")
    strategy = app.config.get("RATELIMIT_STRATEGY", "fixed-window")
    if strategy == "fixed-window-elastic-expiry":
        try:
            from limits import parse

            parse(strategy)
        except Exception:
            strategy = "fixed-window"
    app.config["RATELIMIT_STRATEGY"] = strategy
    limiter.init_app(app)
    limiter.enabled = True

    storage_uri = app.config.get("RATELIMIT_STORAGE_URI", "")
    flask_env = app.config.get("FLASK_ENV") or app.config.get("ENV", "")
    if storage_uri.startswith(("redis://", "rediss://")) and flask_env != "test":
        try:
            import redis

            client = redis.from_url(storage_uri)
            client.ping()
        except Exception as exc:
            raise RuntimeError(
                f"Redis unavailable for rate limiting: {exc}"
            ) from exc

    @app.errorhandler(429)
    def ratelimit_handler(exc):
        retry_after = getattr(exc, "retry_after", None) or 60
        resp = jsonify({"error": "rate_limit_exceeded", "retry_after": retry_after})
        resp.status_code = 429
        resp.headers["Retry-After"] = str(int(retry_after))
        return resp

    return limiter


def limit_authenticated(limit_string: str) -> Callable:
    """Decorator applying a per-user limit (falls back to IP)."""
    return limiter.limit(limit_string, key_func=_authenticated_key)


def limit_ip(limit_string: str) -> Callable:
    """Decorator applying a per-IP limit."""
    return limiter.limit(limit_string, key_func=_get_real_ip)
