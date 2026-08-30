"""
JWT helpers for Sentio Mind auth.

Migration SQL (run once):
CREATE TABLE IF NOT EXISTS auth_enabler.revoked_tokens (
    jti TEXT PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires
    ON auth_enabler.revoked_tokens (expires_at);
"""

import datetime
import logging
import uuid

import jwt

from auth.config import get_config
from auth.constants.applications import (
    DEFAULT_APPLICATION,
    KNOWN_AUDIENCES,
    application_for_audience,
    audience_for,
    normalize_application,
)
from auth.db_connection import get_db_connection, release_db_connection

logger = logging.getLogger(__name__)
config = get_config()

SUPPORTED_ALGORITHMS = ["HS256"]
JWT_ISSUER = "sentio-mind-auth"
# Historical single-audience constant, kept for callers/tests that reference it.
# The audience actually stamped on a token is derived from its application.
JWT_AUDIENCE = audience_for(DEFAULT_APPLICATION)


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


class TokenApplicationError(Exception):
    """Token is valid but was minted for a different application."""


def generate_access_token(
    user_id: int,
    email: str,
    roles: list = None,
    role: str = None,
    scope_type: str = None,
    permissions: list = None,
    application: str = DEFAULT_APPLICATION,
) -> str:
    app = normalize_application(application)
    if app is None:
        raise TokenInvalidError(f"Unknown application: {application}")
    role_names = [r["name"] if isinstance(r, dict) else r for r in (roles or [])]
    now = datetime.datetime.utcnow()
    payload = {
        "exp": now + datetime.timedelta(minutes=config.JWT_ACCESS_MINUTES),
        "iat": now,
        "sub": str(user_id),
        "email": email,
        "roles": role_names,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iss": JWT_ISSUER,
        "aud": audience_for(app),
        "app": app,
    }
    if role:
        payload["role"] = role
    if scope_type:
        payload["scope_type"] = scope_type
    if permissions:
        payload["permissions"] = permissions
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=SUPPORTED_ALGORITHMS[0])


def generate_refresh_token_value() -> str:
    return str(uuid.uuid4())


def generate_mfa_pending_token(
    user_id: int,
    email: str,
    remember: bool = False,
    application: str = DEFAULT_APPLICATION,
) -> str:
    """Short-lived token issued when MFA is required after password login.

    Carries the application so the eventual access token stays bound to the
    application the user actually logged into.
    """
    app = normalize_application(application)
    if app is None:
        raise TokenInvalidError(f"Unknown application: {application}")
    now = datetime.datetime.utcnow()
    payload = {
        "exp": now + datetime.timedelta(minutes=5),
        "iat": now,
        "sub": str(user_id),
        "email": email,
        "type": "mfa_pending",
        "remember": bool(remember),
        "jti": str(uuid.uuid4()),
        "iss": JWT_ISSUER,
        "aud": audience_for(app),
        "app": app,
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=SUPPORTED_ALGORITHMS[0])

def token_application(payload: dict) -> str | None:
    """Application a decoded payload belongs to (falls back to its audience)."""
    app = payload.get("app")
    if app:
        return normalize_application(app)
    return application_for_audience(payload.get("aud"))


def decode_token(auth_token: str, expected_application: str = None) -> dict:
    """Decode and verify a token issued by this authority.

    Any registered application audience is accepted at the signature layer;
    pass ``expected_application`` to additionally bind the token to one
    application (raises :class:`TokenApplicationError` on mismatch).
    """
    try:
        payload = jwt.decode(
            auth_token,
            config.JWT_SECRET_KEY,
            algorithms=SUPPORTED_ALGORITHMS,
            issuer=JWT_ISSUER,
            audience=KNOWN_AUDIENCES,
        )
    except jwt.ExpiredSignatureError as exc:
        logger.info("JWT expired: %s", exc)
        raise TokenExpiredError("Signature expired. Please log in again.") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT invalid: %s", exc)
        raise TokenInvalidError("Invalid token. Please log in again.") from exc

    app = token_application(payload)
    if app is None:
        raise TokenInvalidError("Invalid token. Please log in again.")
    payload["app"] = app

    if expected_application is not None and app != expected_application:
        logger.warning(
            "JWT application mismatch: token=%s expected=%s", app, expected_application
        )
        raise TokenApplicationError(
            "Token was not issued for this application."
        )

    return payload


def revoke_access_token(jti: str, expires_at: datetime.datetime) -> None:
    if not jti:
        return
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auth_enabler.revoked_tokens (jti, expires_at)
            VALUES (%s, %s)
            ON CONFLICT (jti) DO NOTHING
            """,
            (jti, expires_at),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning("Failed to revoke access token jti: %s", e)
    finally:
        release_db_connection(conn)


def is_token_revoked(jti: str) -> bool:
    if not jti:
        return False
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM auth_enabler.revoked_tokens WHERE jti = %s",
            (jti,),
        )
        return cur.fetchone() is not None
    except Exception as e:
        from flask import current_app

        current_app.logger.error(
            f"[SECURITY] revocation check failed, treating as revoked: {e}"
        )
        return True
    finally:
        if conn is not None:
            release_db_connection(conn)


def generate_token(
    user_id: int,
    email: str,
    role: str = None,
    scope_type: str = None,
    permissions: list = None,
    application: str = DEFAULT_APPLICATION,
) -> str:
    """Backward-compatible alias used by legacy callers."""
    return generate_access_token(
        user_id,
        email,
        role=role,
        scope_type=scope_type,
        permissions=permissions,
        application=application,
    )
