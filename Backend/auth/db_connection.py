import os
import time
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from auth.env_loader import load_env

load_env()

logger = logging.getLogger(__name__)

_DB_URL = os.environ.get("SENTIO_DB_URL", "")
_POOL: pool.ThreadedConnectionPool | None = None
_SLOW_QUERY_SECONDS = 5.0


def _connection_kwargs() -> dict:
    # SEC-015 FIX: sslmode is configurable for local dev (Postgres without SSL).
    # Defaults to 'require' for production safety. Set SENTIO_DB_SSLMODE=disable
    # or SENTIO_DB_SSLMODE=prefer for local development without SSL.
    sslmode = os.environ.get("SENTIO_DB_SSLMODE", "require")
    return {
        "sslmode": sslmode,
        "cursor_factory": RealDictCursor,
        "connect_timeout": 5,
        "options": "-c statement_timeout=30000",
    }


def _get_pool() -> pool.ThreadedConnectionPool:
    global _POOL
    if _POOL is None:
        if not _DB_URL:
            raise RuntimeError(
                "SENTIO_DB_URL environment variable is not set."
            )
        _POOL = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=_DB_URL,
            **_connection_kwargs(),
        )
    return _POOL


def get_db_connection():
    """Acquire a connection from the thread-safe pool."""
    conn = _get_pool().getconn()
    conn.autocommit = False
    return conn


def release_db_connection(conn) -> None:
    """Return a connection to the pool."""
    if conn is not None:
        try:
            _get_pool().putconn(conn)
        except Exception as e:
            logger.warning("Failed to release DB connection to pool: %s", e)


@contextmanager
def db_cursor():
    """Yield a cursor; commit on success, rollback on error, always release."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_db_connection(conn)


class _SlowQueryCursor:
    """Wraps cursor.execute to log queries exceeding the slow threshold."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, vars=None):
        start = time.monotonic()
        try:
            return self._cursor.execute(query, vars)
        finally:
            elapsed = time.monotonic() - start
            if elapsed > _SLOW_QUERY_SECONDS:
                logger.warning(
                    "Slow query (%.2fs): %s",
                    elapsed,
                    (query[:200] if isinstance(query, str) else "SQL"),
                )

    def __getattr__(self, name):
        return getattr(self._cursor, name)


def get_db_cursor():
    """Return (connection, slow-query-wrapped cursor) — caller must release."""
    conn = get_db_connection()
    return conn, _SlowQueryCursor(conn.cursor())


def init_auth_db():
    """Test pool connectivity at startup."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        logger.info("Auth DB connection pool established successfully via SENTIO_DB_URL.")
    except Exception as e:
        logger.error("Auth DB startup check failed: %s", e)
        raise
    finally:
        if conn:
            release_db_connection(conn)
