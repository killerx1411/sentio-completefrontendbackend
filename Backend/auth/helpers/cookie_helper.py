"""HttpOnly refresh cookie helpers."""

from __future__ import annotations

from flask import Response

from auth.config import get_config
from auth.constants.cookies import REFRESH_COOKIE

config = get_config()
CSRF_COOKIE = "sentio_csrf"


def _cookie_secure() -> bool:
    return bool(config.SESSION_COOKIE_SECURE)


def set_refresh_cookie(response: Response, refresh_token: str, remember: bool) -> Response:
    max_age = config.JWT_REFRESH_DAYS * 24 * 60 * 60 if remember else None
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="Lax",
        max_age=max_age,
        path="/api/auth",
    )
    return response


def clear_refresh_cookie(response: Response) -> Response:
    response.set_cookie(
        REFRESH_COOKIE,
        "",
        httponly=True,
        secure=_cookie_secure(),
        samesite="Lax",
        max_age=0,
        path="/api/auth",
    )
    return response


def set_csrf_cookie(response: Response, csrf_token: str) -> None:
    """Readable CSRF cookie for double-submit pattern.

    SECURITY NOTE (SEC-008): httponly=False is intentional — the frontend JS
    must read this cookie to send it back as the X-CSRF-Token header (double-
    submit CSRF defense). An XSS that can read this cookie can also forge
    CSRF-protected requests, but XSS is mitigated by:
      • Strict Content-Security-Policy in nginx (no inline scripts, no eval)
      • No use of dangerouslySetInnerHTML in the React frontend
      • SameSite=Lax + Secure flags on all cookies
    """
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=_cookie_secure(),
        samesite="Lax",
        path="/",
        max_age=config.JWT_REFRESH_DAYS * 24 * 60 * 60,
    )


def clear_csrf_cookie(response: Response) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        "",
        httponly=False,
        secure=_cookie_secure(),
        samesite="Lax",
        max_age=0,
        path="/",
    )
