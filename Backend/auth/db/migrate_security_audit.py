"""Security audit migrations: terms acceptance, refresh token remember, session migration."""

import hashlib
import sys
import os
import uuid
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.db_connection import get_db_connection, release_db_connection


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def run_migration():
    print("Running security audit migrations...")
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "ALTER TABLE auth_enabler.users "
            "ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP NULL DEFAULT NULL;"
        )
        cur.execute(
            "ALTER TABLE auth_enabler.refresh_tokens "
            "ADD COLUMN IF NOT EXISTS remember BOOLEAN DEFAULT FALSE;"
        )
        cur.execute(
            "ALTER TABLE auth_enabler.audit_logs "
            "ADD COLUMN IF NOT EXISTS details JSONB;"
        )
        cur.execute(
            "ALTER TABLE auth_enabler.audit_logs "
            "ADD COLUMN IF NOT EXISTS user_agent TEXT;"
        )

        cur.execute(
            """
            SELECT s.user_id, s.refresh_token, s.device_fingerprint, s.expires_at
            FROM auth_enabler.user_sessions s
            WHERE s.refresh_token IS NOT NULL
              AND s.revoked = FALSE
              AND s.expires_at > NOW()
            """
        )
        legacy_sessions = cur.fetchall()
        migrated = 0
        for row in legacy_sessions:
            raw = row["refresh_token"]
            if not raw:
                continue
            token_hash = _hash_token(raw)
            cur.execute(
                """
                SELECT 1 FROM auth_enabler.refresh_tokens WHERE token_hash = %s
                """,
                (token_hash,),
            )
            if cur.fetchone():
                continue
            family_id = str(uuid.uuid4())
            row_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO auth_enabler.refresh_tokens
                    (id, user_id, token_hash, device_hash, family_id, expires_at, remember)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                ON CONFLICT (token_hash) DO NOTHING
                """,
                (
                    row_id,
                    row["user_id"],
                    token_hash,
                    row.get("device_fingerprint") or "",
                    family_id,
                    row["expires_at"],
                ),
            )
            migrated += 1

        cur.execute(
            """
            UPDATE auth_enabler.user_sessions
            SET refresh_token = NULL
            WHERE refresh_token IS NOT NULL
            """
        )

        conn.commit()
        print(
            f"Security migrations complete. Migrated {migrated} legacy refresh tokens."
        )
    except Exception as exc:
        conn.rollback()
        print(f"Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        release_db_connection(conn)


if __name__ == "__main__":
    run_migration()
