"""
Audit logging helpers.

Migration SQL:
ALTER TABLE auth_enabler.audit_logs
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'INFO';
ALTER TABLE auth_enabler.audit_logs
    ADD COLUMN IF NOT EXISTS details JSONB;
ALTER TABLE auth_enabler.audit_logs
    ADD COLUMN IF NOT EXISTS user_agent TEXT;

CREATE OR REPLACE FUNCTION auth_enabler.prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'audit_logs rows are append-only and cannot be deleted';
    END IF;
    IF (to_jsonb(NEW) - 'user_id' - 'created_by' - 'updated_by' - 'updated_at')
       = (to_jsonb(OLD) - 'user_id' - 'created_by' - 'updated_by' - 'updated_at')
       AND (NEW.user_id    IS NULL OR NEW.user_id    = OLD.user_id)
       AND (NEW.created_by IS NULL OR NEW.created_by = OLD.created_by)
       AND (NEW.updated_by IS NULL OR NEW.updated_by = OLD.updated_by)
    THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'audit_logs rows are append-only and cannot be modified';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_logs_append_only ON auth_enabler.audit_logs;
CREATE TRIGGER audit_logs_append_only
BEFORE UPDATE OR DELETE ON auth_enabler.audit_logs
FOR EACH ROW EXECUTE FUNCTION auth_enabler.prevent_audit_log_modification();
"""

import json
import logging

from auth.db_connection import get_db_connection, release_db_connection

logger = logging.getLogger(__name__)

_VALID_SEVERITIES = frozenset({"INFO", "WARNING", "CRITICAL"})


def log_activity(
    user_id,
    action,
    module,
    description=None,
    ip_address=None,
    severity: str = "INFO",
    details=None,
    user_agent=None,
    cur=None,
):
    """Insert an append-only audit log row."""
    if severity not in _VALID_SEVERITIES:
        severity = "INFO"

    details_json = json.dumps(details) if details is not None else None

    sql = """
        INSERT INTO auth_enabler.audit_logs
            (user_id, action, module, description, ip_address, severity,
             created_by, details, user_agent)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
    """
    params = (
        user_id,
        action,
        module,
        description,
        ip_address,
        severity,
        user_id,
        details_json,
        user_agent,
    )

    if cur is not None:
        cur.execute(sql, params)
        return

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("Failed to write audit log: %s", e)
    finally:
        release_db_connection(conn)


def get_audit_logs_for_user(user_id: int, limit: int = 50) -> list:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, action, module, description, ip_address, severity,
                   details, user_agent, created_at
            FROM auth_enabler.audit_logs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
        for row in rows:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
        return rows
    except Exception as e:
        logger.error("Failed to fetch audit logs for user %s: %s", user_id, e)
        return []
    finally:
        release_db_connection(conn)
