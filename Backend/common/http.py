"""HTTP hardening helpers shared by every Sentio Flask application.

Both the stakeholder/auth service (``app_factory``) and the CV service
(``cv_analysis.app``) apply the identical proxy handling, CORS header set and
response security headers. Keeping them here means neither service has to
import the other just to stay hardened.
"""
from __future__ import annotations

import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "X-CSRF-Token"]


def apply_proxy_fix(flask_app: Flask) -> None:
    """Trust X-Forwarded-* from nginx so request.remote_addr is the client IP."""
    trusted = int(os.environ.get("TRUSTED_PROXY_COUNT", "1"))
    if trusted > 0:
        flask_app.wsgi_app = ProxyFix(
            flask_app.wsgi_app,
            x_for=trusted,
            x_proto=1,
            x_host=1,
        )


def apply_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    )
    return response
