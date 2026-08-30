"""Refresh token rotation, family tracking, and reuse detection."""

from __future__ import annotations

import datetime
import hashlib
import logging
import uuid
from typing import Any

from auth.config import get_config
from auth.constants.applications import DEFAULT_APPLICATION, normalize_application
from auth.db_connection import get_db_connection, release_db_connection
from auth.helpers.audit_helper import log_activity
from auth.constants.cookies import REFRESH_COOKIE

logger = logging.getLogger(__name__)
config = get_config()


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def device_hash_from_request(
    user_agent: str | None,
    accept_language: str | None,
) -> str:
    raw = f"{user_agent or ''}|{accept_language or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def resolve_user_id_from_refresh_cookie(refresh_token: str | None) -> int | None:
    """Resolve user id from opaque refresh token (DB lookup)."""
    if not refresh_token:
        return None
    token_hash = hash_token(refresh_token)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id FROM auth_enabler.refresh_tokens
            WHERE token_hash = %s AND revoked_at IS NULL
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        return int(row["user_id"]) if row else None
    except Exception as exc:
        logger.warning("Refresh cookie lookup failed: %s", exc)
        return None
    finally:
        release_db_connection(conn)


def create_refresh_token_row(
    cur,
    user_id: int,
    raw_token: str,
    device_hash: str,
    family_id: uuid.UUID | None = None,
    replaced_by: uuid.UUID | None = None,
    remember: bool = False,
    application: str = DEFAULT_APPLICATION,
) -> uuid.UUID:
    """Insert a new refresh_tokens row; returns row id.

    ``application`` binds the whole rotation family to the application the
    session was opened for (see auth/constants/applications.py).
    """
    token_hash = hash_token(raw_token)
    family = family_id or uuid.uuid4()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(
        days=config.JWT_REFRESH_DAYS
    )
    row_id = uuid.uuid4()
    cur.execute(
        """
        INSERT INTO auth_enabler.refresh_tokens
            (id, user_id, token_hash, device_hash, family_id, expires_at, replaced_by,
             remember, application)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            str(row_id),
            user_id,
            token_hash,
            device_hash,
            str(family),
            expires_at,
            str(replaced_by) if replaced_by else None,
            remember,
            normalize_application(application) or DEFAULT_APPLICATION,
        ),
    )
    return row_id


def rotate_refresh_token(
    raw_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    accept_language: str | None = None,
) -> dict[str, Any]:
    """
    Validate refresh token, rotate on success, detect reuse on revoked/unknown tokens.
    Returns dict with access_token, refresh_token, or error keys.
    """
    if not raw_token:
        return {"error": "Refresh token required", "status": 401}

    token_hash = hash_token(raw_token)
    device_hash = device_hash_from_request(user_agent, accept_language)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, family_id, device_hash, revoked_at, expires_at,
                   remember, application
            FROM auth_enabler.refresh_tokens
            WHERE token_hash = %s
            """,
            (token_hash,),
        )
        row = cur.fetchone()

        if not row:
            return {"error": "Invalid refresh token", "status": 401}

        if row.get("revoked_at"):
            _revoke_family(cur, row["family_id"], row["user_id"], ip_address)
            conn.commit()
            return {
                "error": "session_invalidated",
                "reason": "token_reuse_detected",
                "status": 401,
                "clear_cookie": True,
            }

        expires = row["expires_at"]
        now = datetime.datetime.utcnow()
        if expires and hasattr(expires, "tzinfo") and expires.tzinfo:
            now = datetime.datetime.now(datetime.timezone.utc)
        if expires and now > expires:
            return {"error": "Refresh token expired", "status": 401}

        stored_device = row.get("device_hash") or ""
        if stored_device and device_hash and stored_device != device_hash:
            log_activity(
                row["user_id"],
                "REFRESH_DEVICE_MISMATCH",
                "Authentication",
                "Device fingerprint changed on refresh",
                ip_address=ip_address,
                severity="CRITICAL",
            )
            _revoke_family(cur, row["family_id"], row["user_id"], ip_address)
            conn.commit()
            return {
                "error": "session_invalidated",
                "reason": "device_mismatch",
                "status": 401,
                "clear_cookie": True,
            }

        remember = bool(row.get("remember"))
        application = normalize_application(row.get("application")) or DEFAULT_APPLICATION
        new_raw = str(uuid.uuid4())
        new_id = create_refresh_token_row(
            cur,
            row["user_id"],
            new_raw,
            device_hash,
            family_id=uuid.UUID(str(row["family_id"])),
            replaced_by=uuid.UUID(str(row["id"])),
            remember=remember,
            application=application,
        )
        cur.execute(
            """
            UPDATE auth_enabler.refresh_tokens
            SET revoked_at = NOW(), replaced_by = %s
            WHERE id = %s
            """,
            (str(new_id), str(row["id"])),
        )
        conn.commit()
        return {
            "user_id": row["user_id"],
            "refresh_token": new_raw,
            "remember": remember,
            "application": application,
            "rotated": True,
        }
    except Exception as exc:
        conn.rollback()
        logger.error("Refresh rotation error: %s", exc, exc_info=True)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        release_db_connection(conn)


def _revoke_family(cur, family_id: str, user_id: int, ip_address: str | None) -> None:
    cur.execute(
        """
        UPDATE auth_enabler.refresh_tokens
        SET revoked_at = NOW()
        WHERE family_id = %s AND revoked_at IS NULL
        """,
        (str(family_id),),
    )
    log_activity(
        user_id,
        "refresh_token_reuse",
        "Security",
        f"family_id={family_id}",
        ip_address=ip_address,
        severity="CRITICAL",
    )


def revoke_family_for_token(raw_token: str) -> None:
    if not raw_token:
        return
    token_hash = hash_token(raw_token)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT family_id, user_id FROM auth_enabler.refresh_tokens
            WHERE token_hash = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        if row:
            _revoke_family(cur, row["family_id"], row["user_id"], None)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("Revoke family error: %s", exc)
    finally:
        release_db_connection(conn)


def revoke_all_refresh_tokens_for_user(user_id: int, cur=None) -> None:
    """Revoke every active refresh token for a user (password reset, admin pw change)."""
    sql = """
        UPDATE auth_enabler.refresh_tokens
        SET revoked_at = NOW()
        WHERE user_id = %s AND revoked_at IS NULL
    """
    if cur is not None:
        cur.execute(sql, (user_id,))
        return
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, (user_id,))
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error("Revoke all refresh tokens for user %s failed: %s", user_id, exc)
    finally:
        release_db_connection(conn)
