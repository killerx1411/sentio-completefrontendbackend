import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_db_connection


def run_migration():
    print("Connecting to database for IAM workflow migration...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        queries = [
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS registration_status VARCHAR(50) DEFAULT 'PENDING';",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS is_first_login BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS temp_password_expiry TIMESTAMP WITH TIME ZONE;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS assigned_school VARCHAR(255);",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS assigned_class VARCHAR(255);",
            "CREATE INDEX IF NOT EXISTS idx_users_approved_by ON auth_enabler.users (approved_by);",
            # Existing active users should be treated as approved
            """
            UPDATE auth_enabler.users
            SET registration_status = 'APPROVED', is_first_login = FALSE
            WHERE status = 'active' AND (registration_status IS NULL OR registration_status = 'PENDING');
            """,
            # Legacy signup pending rows
            """
            UPDATE auth_enabler.users
            SET registration_status = 'PENDING', status = 'inactive'
            WHERE status = 'pending';
            """,
            """
            UPDATE auth_enabler.users
            SET registration_status = 'REJECTED', status = 'inactive'
            WHERE status = 'rejected';
            """,
        ]

        for q in queries:
            cur.execute(q)

        conn.commit()
        print("IAM workflow columns migrated successfully.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error executing IAM migration: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
