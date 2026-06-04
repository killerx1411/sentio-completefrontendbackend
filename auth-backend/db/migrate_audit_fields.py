import sys
import os

# Adjust path to import connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_db_connection

def run_migration():
    print("Connecting to database for audit fields migration...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print("Checking and adding audit columns and indexes to tables...")
        
        queries = [
            # 1. users
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "CREATE INDEX IF NOT EXISTS idx_users_created_by ON auth_enabler.users (created_by);",
            "CREATE INDEX IF NOT EXISTS idx_users_updated_by ON auth_enabler.users (updated_by);",

            # 2. roles
            "ALTER TABLE auth_enabler.roles ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.roles ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.roles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_roles_created_by ON auth_enabler.roles (created_by);",
            "CREATE INDEX IF NOT EXISTS idx_roles_updated_by ON auth_enabler.roles (updated_by);",

            # 3. permissions
            "ALTER TABLE auth_enabler.permissions ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.permissions ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.permissions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE auth_enabler.permissions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_permissions_created_by ON auth_enabler.permissions (created_by);",
            "CREATE INDEX IF NOT EXISTS idx_permissions_updated_by ON auth_enabler.permissions (updated_by);",

            # 4. role_permissions
            "ALTER TABLE auth_enabler.role_permissions ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.role_permissions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_role_permissions_created_by ON auth_enabler.role_permissions (created_by);",

            # 5. user_roles
            "ALTER TABLE auth_enabler.user_roles ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.user_roles ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_user_roles_created_by ON auth_enabler.user_roles (created_by);",
            
            # Triggers
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_roles_updated_at') THEN
                    CREATE TRIGGER update_roles_updated_at
                    BEFORE UPDATE ON auth_enabler.roles
                    FOR EACH ROW
                    EXECUTE FUNCTION auth_enabler.update_updated_at_column();
                END IF;
            END $$;
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_permissions_updated_at') THEN
                    CREATE TRIGGER update_permissions_updated_at
                    BEFORE UPDATE ON auth_enabler.permissions
                    FOR EACH ROW
                    EXECUTE FUNCTION auth_enabler.update_updated_at_column();
                END IF;
            END $$;
            """
        ]
        
        for q in queries:
            cur.execute(q)
            
        conn.commit()
        print("Database schema upgraded successfully with audit fields, indexes, and triggers!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error executing migration: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
