"""HTTP request helpers shared across auth routes and middleware."""

from __future__ import annotations

from flask import request


def get_client_ip() -> str:
    """Return the true client IP behind a trusted reverse proxy.

    Priority: X-Real-IP → first X-Forwarded-For hop → REMOTE_ADDR.
    nginx sets X-Real-IP via proxy_set_header; ProxyFix on the WSGI app
    also corrects request.remote_addr as a fallback.
    """
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"
