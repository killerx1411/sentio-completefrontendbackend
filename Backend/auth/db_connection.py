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


def _pool_size(env_var: str, default: int) -> int:
    """Read a pool bound from the environment, falling back on bad input.

    Pool size is per *worker process*: gunicorn_config.py sets
    preload_app = False, so every gunicorn worker builds its own pool and the
    connections a single Cloud Run instance holds is workers x maxconn. On a
    small Cloud SQL tier (db-f1-micro caps max_connections near 25) the
    defaults below can exhaust the server during a revision rollout, when the
    old and new revisions overlap. Shrink them there rather than editing code.
    """
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r is not an integer; using %d", env_var, raw, default)
        return default
    if value < 1:
        logger.warning("%s=%d must be >= 1; using %d", env_var, value, default)
        return default
    return value


def _get_pool() -> pool.ThreadedConnectionPool:
    global _POOL
    if _POOL is None:
        if not _DB_URL:
            raise RuntimeError(
                "SENTIO_DB_URL environment variable is not set."
            )
        maxconn = _pool_size("SENTIO_DB_POOL_MAX", 10)
        minconn = _pool_size("SENTIO_DB_POOL_MIN", 2)
        if minconn > maxconn:
            # psycopg2 opens minconn connections eagerly and then refuses to
            # take them back, so an inverted pair fails on the first request
            # rather than at startup. Clamp instead.
            logger.warning(
                "SENTIO_DB_POOL_MIN=%d exceeds SENTIO_DB_POOL_MAX=%d; using %d",
                minconn,
                maxconn,
                maxconn,
            )
            minconn = maxconn
        _POOL = pool.ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
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
