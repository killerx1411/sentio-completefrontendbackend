import sys
import os

# Adjust path to import connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_db_connection

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
