"""
In-process rate limiter backed by DB table auth_enabler.login_attempts.
Falls back to an in-memory dict if DB is unavailable.

Migration SQL (run once):
CREATE TABLE IF NOT EXISTS auth_enabler.login_attempts (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    ip_address TEXT,
    attempted_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_email_at
    ON auth_enabler.login_attempts (email, attempted_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_at
    ON auth_enabler.login_attempts (ip_address, attempted_at);
"""

import datetime
import logging
from collections import defaultdict

from auth.config import get_config
from auth.db_connection import get_db_connection, release_db_connection

logger = logging.getLogger(__name__)
config = get_config()

_memory_attempts: dict[tuple[str, str], list[datetime.datetime]] = defaultdict(list)
_memory_ip_attempts: dict[str, list[datetime.datetime]] = defaultdict(list)


def _lockout_window_start() -> datetime.datetime:
    # Must be timezone-aware: attempted_at is TIMESTAMPTZ, and a naive datetime
    # is interpreted by Postgres in the session timezone, which widened the
    # window by the server's UTC offset and counted long-expired attempts.
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        minutes=config.LOGIN_LOCKOUT_MINUTES
    )


def _prune_memory(key: tuple[str, str], since: datetime.datetime) -> list:
    attempts = _memory_attempts[key]
    _memory_attempts[key] = [t for t in attempts if t >= since]
    return _memory_attempts[key]


def _prune_memory_ip(ip: str, since: datetime.datetime) -> list:
    attempts = _memory_ip_attempts[ip]
    _memory_ip_attempts[ip] = [t for t in attempts if t >= since]
    return _memory_ip_attempts[ip]


def record_failed_attempt(email: str, ip: str) -> None:
    email = (email or "").strip().lower()
    ip = ip or ""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auth_enabler.login_attempts (email, ip_address)
            VALUES (%s, %s)
            """,
            (email, ip),
        )
        conn.commit()
    except Exception as e:
        logger.warning("DB login attempt record failed, using memory fallback: %s", e)
        since = _lockout_window_start()
        key = (email, ip)
        _prune_memory(key, since)
        _memory_attempts[key].append(datetime.datetime.now(datetime.timezone.utc))
        _prune_memory_ip(ip, since)
        _memory_ip_attempts[ip].append(datetime.datetime.now(datetime.timezone.utc))
    finally:
        if conn:
            release_db_connection(conn)


def _count_attempts_db(email: str, ip: str, since: datetime.datetime) -> int:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM auth_enabler.login_attempts
            WHERE email = %s AND ip_address = %s AND attempted_at >= %s
            """,
            (email, ip, since),
        )
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0
    finally:
        release_db_connection(conn)


def _count_ip_attempts_db(ip: str, since: datetime.datetime) -> int:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM auth_enabler.login_attempts
            WHERE ip_address = %s AND attempted_at >= %s
            """,
            (ip, since),
        )
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0
    finally:
        release_db_connection(conn)


def get_failed_attempt_count(email: str) -> int:
    """Recent failed attempts for email (used for audit severity)."""
    email = (email or "").strip().lower()
    since = _lockout_window_start()
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM auth_enabler.login_attempts
            WHERE email = %s AND attempted_at >= %s
            """,
            (email, since),
        )
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0
    except Exception as e:
        logger.warning("DB failed attempt count failed, using memory fallback: %s", e)
        total = 0
        for key, attempts in _memory_attempts.items():
            if key[0] == email:
                total += len(_prune_memory(key, since))
        return total
    finally:
        if conn:
            release_db_connection(conn)


def is_locked_out(email: str, ip: str) -> bool:
    email = (email or "").strip().lower()
    ip = ip or ""
    since = _lockout_window_start()
    try:
        count = _count_attempts_db(email, ip, since)
        ip_count = _count_ip_attempts_db(ip, since)
    except Exception as e:
        # SEC-012 FIX: Fail closed in ALL environments when DB is unavailable.
        # Previously only production failed closed; dev/staging failed open,
        # allowing brute force when the DB was down.
        logger.warning("DB lockout check failed — failing closed (locked): %s", e)
        return True
    if count >= config.MAX_LOGIN_ATTEMPTS:
        return True
    return ip_count >= config.MAX_IP_LOGIN_ATTEMPTS


PASSWORD_RESET_MAX_PER_HOUR = 3


def _reset_request_window_start() -> datetime.datetime:
    # Aware UTC: requested_at is TIMESTAMPTZ (see _lockout_window_start).
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)


def record_password_reset_request(email: str) -> None:
    email = (email or "").strip().lower()
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auth_enabler.password_reset_requests (email)
            VALUES (%s)
            """,
            (email,),
        )
        conn.commit()
    except Exception as e:
        logger.warning("DB password reset request record failed: %s", e)
    finally:
        if conn:
            release_db_connection(conn)


def is_password_reset_rate_limited(email: str) -> bool:
    email = (email or "").strip().lower()
    since = _reset_request_window_start()
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM auth_enabler.password_reset_requests
            WHERE email = %s AND requested_at >= %s
            """,
            (email, since),
        )
        row = cur.fetchone()
        count = int(row["cnt"]) if row else 0
        return count >= PASSWORD_RESET_MAX_PER_HOUR
    except Exception as e:
        logger.warning("DB password reset rate limit check failed: %s", e)
        return True
    finally:
        if conn:
            release_db_connection(conn)


def clear_attempts(email: str) -> None:
    email = (email or "").strip().lower()
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM auth_enabler.login_attempts WHERE email = %s",
            (email,),
        )
        conn.commit()
    except Exception as e:
        logger.warning("Failed to clear login attempts in DB: %s", e)
    finally:
        if conn:
            release_db_connection(conn)
    for key in list(_memory_attempts.keys()):
        if key[0] == email:
            del _memory_attempts[key]
