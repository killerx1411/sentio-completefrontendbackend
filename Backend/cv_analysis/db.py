"""CV analysis persistence: persons / videos / frames / analysis / traits.

These tables are owned and written **only** by the CV system. They live in the
default (public) PostgreSQL schema and are entirely separate from the
``auth_enabler`` schema that owns identity, roles, sessions and audit — see
``auth/db/schema.sql``, which does not define any of them.

The one remaining CV -> Auth dependency is the connection pool: rather than
opening a second pool against the same database, the CV system borrows
``auth.db_connection``. When the CV service is extracted, only the two helpers
at the top of this file need to change (point them at ``CV_DATABASE_URL``);
no auth code and no SQL below has to move.
"""
from __future__ import annotations

import logging

from auth.db_connection import get_db_connection, release_db_connection

logger = logging.getLogger(__name__)


def get_db_conn():
    """Return a pooled psycopg2 connection (auth layer pool)."""
    return get_db_connection()


def _release_db_conn(conn):
    release_db_connection(conn)


def _db_available() -> bool:
    """Silent check — returns False if DB is unreachable so analysis still runs offline."""
    conn = None
    try:
        conn = get_db_conn()
        return True
    except Exception as e:
        logger.warning("DB not available — running in file-only mode: %s", e)
        return False
    finally:
        if conn:
            _release_db_conn(conn)

_USE_DB = _db_available()   # checked once at startup
# ─── DB WRITE HELPERS ─────────────────────────────────────────────────────────

def db_upsert_person(person_id: str, data: dict):
    """Insert or update a person row."""
    if not _USE_DB:
        return
    try:
        conn = get_db_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO persons
                        (person_id, name, school, first_seen, last_seen,
                         appearance_count, profile_image)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (person_id) DO UPDATE SET
                        name             = EXCLUDED.name,
                        last_seen        = EXCLUDED.last_seen,
                        appearance_count = EXCLUDED.appearance_count,
                        profile_image    = EXCLUDED.profile_image
                """, (
                    person_id,
                    data.get('name'),
                    data.get('school'),
                    data.get('first_seen'),
                    data.get('last_seen'),
                    data.get('appearance_count', 1),
                    data.get('profile_image', '')
                ))
        _release_db_conn(conn)
    except Exception as e:
        logger.error("db_upsert_person error: %s", e, exc_info=True)


def db_insert_video(video_name: str, school: str, date_str: str) -> int | None:
    """Insert a video row, return its video_id (or None on failure)."""
    if not _USE_DB:
        return None
    try:
        conn = get_db_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO videos (video_name, school, date)
                    VALUES (%s, %s, %s)
                    RETURNING video_id
                """, (video_name, school, date_str))
                video_id = cur.fetchone()[0]
        _release_db_conn(conn)
        return video_id
    except Exception as e:
        logger.error("db_insert_video error: %s", e, exc_info=True)
        return None


def db_insert_frame(video_id: int, frame_index: int, timestamp: float) -> int | None:
    """Insert a frame row, return frame_id."""
    if not _USE_DB or video_id is None:
        return None
    try:
        conn = get_db_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO frames (video_id, frame_index, timestamp)
                    VALUES (%s, %s, %s)
                    RETURNING frame_id
                """, (video_id, frame_index, timestamp))
                frame_id = cur.fetchone()[0]
        _release_db_conn(conn)
        return frame_id
    except Exception as e:
        logger.error("db_insert_frame error: %s", e, exc_info=True)
        return None


def db_insert_analysis_with_traits(
        frame_id: int,
        person_id: str,
        emotion: str,
        wellbeing_score: int,
        attention_score: int,
        posture_score: int,
        traits: dict) -> int | None:
    """
    Insert one analysis row + one traits row in a single transaction.
    Returns the analysis id, or None on failure.
    """
    if not _USE_DB or frame_id is None:
        return None
    try:
        conn = get_db_conn()
        with conn:
            with conn.cursor() as cur:
                # ── analysis row ──
                cur.execute("""
                    INSERT INTO analysis
                        (frame_id, person_id, emotion,
                         wellbeing_score, attention_score, posture_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    frame_id, person_id, emotion,
                    wellbeing_score, attention_score, posture_score
                ))
                analysis_id = cur.fetchone()[0]

                # ── traits row ──
                cur.execute("""
                    INSERT INTO traits
                        (analysis_id,
                         emotional_positivity, stress_resilience, social_engagement,
                         social_confidence,    physical_energy,   posture_health,
                         body_openness,        focus_alertness,   facial_relaxation,
                         vitality_glow)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    analysis_id,
                    traits.get('emotional_positivity', 50),
                    traits.get('stress_resilience',    50),
                    traits.get('social_engagement',    50),
                    traits.get('social_confidence',    50),
                    traits.get('physical_energy',      50),
                    traits.get('posture_health',       50),
                    traits.get('body_openness',        50),
                    traits.get('focus_alertness',      50),
                    traits.get('facial_relaxation',    50),
                    traits.get('vitality_glow',        50),
                ))
        _release_db_conn(conn)
        return analysis_id
    except Exception as e:
        logger.error("db_insert_analysis_with_traits error: %s", e, exc_info=True)
        return None
