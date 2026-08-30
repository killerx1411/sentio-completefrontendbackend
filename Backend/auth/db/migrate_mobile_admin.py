"""Migration: multi-application support + Sentio Mobile Admin roles.

Idempotent. Adds the ``application`` binding to sessions/refresh tokens and
seeds the Mobile Admin roles and their ``mobile.*`` permissions straight from
``auth.constants.roles.ROLE_CONFIG`` so the DB can never drift from the code's
single source of truth.

    python -m auth.db.migrate_mobile_admin
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from auth.constants.applications import APP_MOBILE, DEFAULT_APPLICATION
from auth.constants.roles import MOBILE_ADMIN_ROLES, ROLE_CONFIG, roles_for_application
from auth.db_connection import get_db_connection

ROLE_DESCRIPTIONS = {
    "mobile_super_admin": "Sentio Mobile Admin — full control of the Mobile application.",
    "mobile_secondary_admin": "Sentio Mobile Admin — operational management, no admin management.",
}

# permission name -> (module, action, description)
PERMISSION_META = {
    "mobile.users.read": ("Mobile Users", "READ", "View Sentio Mobile end users"),
    "mobile.users.write": ("Mobile Users", "WRITE", "Create and edit Sentio Mobile end users"),
    "mobile.users.delete": ("Mobile Users", "DELETE", "Delete Sentio Mobile end users"),
    "mobile.users.approve": ("Mobile Users", "APPROVE", "Approve Sentio Mobile end user registrations"),
    "mobile.admins.manage": ("Mobile Admins", "MANAGE", "Manage Sentio Mobile administrators"),
    "mobile.content.read": ("Mobile Content", "READ", "View Sentio Mobile content"),
    "mobile.content.write": ("Mobile Content", "WRITE", "Create and edit Sentio Mobile content"),
    "mobile.reports.read": ("Mobile Reports", "READ", "View Sentio Mobile reports and analytics"),
    "mobile.settings.manage": ("Mobile Settings", "MANAGE", "Manage Sentio Mobile application settings"),
    "mobile.audit.read": ("Mobile Audit", "READ", "View Sentio Mobile audit and security logs"),
}

SCHEMA_QUERIES = [
    "ALTER TABLE auth_enabler.user_sessions "
    f"ADD COLUMN IF NOT EXISTS application VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_APPLICATION}';",
    "ALTER TABLE auth_enabler.refresh_tokens "
    f"ADD COLUMN IF NOT EXISTS application VARCHAR(64) NOT NULL DEFAULT '{DEFAULT_APPLICATION}';",
    "CREATE INDEX IF NOT EXISTS idx_user_sessions_application "
    "ON auth_enabler.user_sessions (application);",
    "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_application "
    "ON auth_enabler.refresh_tokens (application);",
]


def _missing_permission_meta() -> list:
    required = set()
    for role in roles_for_application(APP_MOBILE):
        required.update(ROLE_CONFIG[role]["permissions"])
    return sorted(required - set(PERMISSION_META))


def run_migration():
    missing = _missing_permission_meta()
    if missing:
        print(
            "Refusing to migrate: PERMISSION_META is missing entries for "
            + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(1)

    print("Connecting to database for Sentio Mobile Admin migration...")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        for q in SCHEMA_QUERIES:
            cur.execute(q)
        print("Application binding columns ensured on sessions and refresh tokens.")

        for role in sorted(MOBILE_ADMIN_ROLES):
            cur.execute(
                """
                INSERT INTO auth_enabler.roles (name, description)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                """,
                (role, ROLE_DESCRIPTIONS.get(role, f"Sentio Mobile Admin role: {role}")),
            )
        print(f"Seeded roles: {', '.join(sorted(MOBILE_ADMIN_ROLES))}")

        for name, (module, action, description) in PERMISSION_META.items():
            cur.execute(
                """
                INSERT INTO auth_enabler.permissions (name, module, action, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    module = EXCLUDED.module,
                    action = EXCLUDED.action,
                    description = EXCLUDED.description
                """,
                (name, module, action, description),
            )
        print(f"Seeded {len(PERMISSION_META)} mobile.* permissions.")

        for role in sorted(MOBILE_ADMIN_ROLES):
            permissions = ROLE_CONFIG[role]["permissions"]
            cur.execute(
                """
                INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM auth_enabler.roles r
                JOIN auth_enabler.permissions p ON p.name = ANY(%s)
                WHERE r.name = %s
                ON CONFLICT DO NOTHING
                """,
                (list(permissions), role),
            )
            # Drop grants the code no longer declares, so demotions take effect.
            cur.execute(
                """
                DELETE FROM auth_enabler.role_permissions rp
                USING auth_enabler.roles r, auth_enabler.permissions p
                WHERE rp.role_id = r.id AND rp.permission_id = p.id
                  AND r.name = %s
                  AND p.name LIKE 'mobile.%%'
                  AND NOT (p.name = ANY(%s))
                """,
                (role, list(permissions)),
            )
        print("Mapped mobile.* permissions to Mobile Admin roles from ROLE_CONFIG.")

        conn.commit()
        cur.close()
        print("Sentio Mobile Admin migration complete.")
    except Exception as e:
        if conn is not None:
            conn.rollback()
        print(f"Error executing Mobile Admin migration: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    run_migration()
