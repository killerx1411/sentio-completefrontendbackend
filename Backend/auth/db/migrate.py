import sys
import os

# Adjust path to import connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.db_connection import get_db_connection

def run_migration():
    print("Connecting to database...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print("Checking and adding columns to auth_enabler.users...")
        
        queries = [
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS department VARCHAR(100);",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS employee_id VARCHAR(50);",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS organization VARCHAR(255);",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS signup_message TEXT;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS requested_role VARCHAR(100);",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS approved_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS profile_image TEXT;",
            "ALTER TABLE auth_enabler.user_sessions ADD COLUMN IF NOT EXISTS revoked BOOLEAN DEFAULT FALSE;",
            """
            CREATE TABLE IF NOT EXISTS auth_enabler.password_reset_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES auth_enabler.users(id) ON DELETE CASCADE,
                token_hash VARCHAR(64) NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_password_reset_token_hash ON auth_enabler.password_reset_tokens (token_hash);",
            "CREATE INDEX IF NOT EXISTS idx_password_reset_user_id ON auth_enabler.password_reset_tokens (user_id);",
            """
            CREATE TABLE IF NOT EXISTS auth_enabler.password_reset_requests (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                requested_at TIMESTAMPTZ DEFAULT NOW()
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_password_reset_requests_email_at ON auth_enabler.password_reset_requests (email, requested_at);",
        ]
        
        for q in queries:
            cur.execute(q)
            
        conn.commit()
        print("Database schema successfully upgraded! Columns added to auth_enabler.users.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error executing migration: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
