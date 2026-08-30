"""CSRF protection for cookie-authenticated refresh/logout flows (double-submit)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from functools import wraps

from flask import jsonify, request

from auth.config import get_config
from auth.constants.cookies import REFRESH_COOKIE
from auth.helpers.cookie_helper import CSRF_COOKIE
from auth.services.refresh_token_service import resolve_user_id_from_refresh_cookie

CSRF_HEADER = "X-CSRF-Token"
CSRF_TTL_SECONDS = 7 * 24 * 60 * 60
config = get_config()


def generate_csrf_token(user_id: int) -> str:
    """Stateless HMAC CSRF token bound to user_id (no Flask session required)."""
    nonce = secrets.token_hex(16)
    exp = int(time.time()) + CSRF_TTL_SECONDS
    sig = _sign_csrf(user_id, nonce, exp)
    return f"{nonce}.{exp}.{sig}"


def validate_csrf_token(user_id: int, token: str) -> bool:
    if not token or not user_id:
        return False
    parts = token.split(".")
    if len(parts) != 3:
        return False
    nonce, exp_str, sig = parts
    try:
        exp = int(exp_str)
    except ValueError:
        return False
    if exp < int(time.time()):
        return False
    expected = _sign_csrf(user_id, nonce, exp)
    return hmac.compare_digest(expected, sig)


def invalidate_csrf_token(user_id: int) -> None:
    """No-op: CSRF tokens are stateless and expire via embedded timestamp."""


def _sign_csrf(user_id: int, nonce: str, exp: int) -> str:
    msg = f"{user_id}:{nonce}:{exp}"
    return hmac.new(
        config.JWT_SECRET_KEY.encode(),
        msg.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def csrf_required(f):
    """Require matching sentio_csrf cookie, X-CSRF-Token header, and valid HMAC token."""

    @wraps(f)
    def decorated(*args, **kwargs):
        cookie_token = request.cookies.get(CSRF_COOKIE)
        header_token = request.headers.get(CSRF_HEADER)
        if not cookie_token or not header_token:
            return jsonify({"error": "csrf_validation_failed"}), 403
        if not secrets.compare_digest(cookie_token, header_token):
            return jsonify({"error": "csrf_validation_failed"}), 403

        refresh_token = request.cookies.get(REFRESH_COOKIE)
        user_id = resolve_user_id_from_refresh_cookie(refresh_token)
        if user_id is None or not validate_csrf_token(user_id, header_token):
            return jsonify({"error": "csrf_validation_failed"}), 403
        return f(*args, **kwargs)

    return decorated
