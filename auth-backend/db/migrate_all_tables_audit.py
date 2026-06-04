import sys
import os

# Adjust path to import connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_db_connection

def run_migration():
    print("Connecting to database for ALL tables audit fields migration...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print("Checking and adding audit columns, indexes, and triggers to all tables...")
        
        queries = [
            # 1. users
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE auth_enabler.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_users_created_by ON auth_enabler.users (created_by);",
            "CREATE INDEX IF NOT EXISTS idx_users_updated_by ON auth_enabler.users (updated_by);",
            
            # 2. roles
            "ALTER TABLE auth_enabler.roles ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.roles ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.roles ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
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
            "ALTER TABLE auth_enabler.role_permissions ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.role_permissions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE auth_enabler.role_permissions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_role_permissions_created_by ON auth_enabler.role_permissions (created_by);",
            "CREATE INDEX IF NOT EXISTS idx_role_permissions_updated_by ON auth_enabler.role_permissions (updated_by);",
            
            # 5. user_roles
            "ALTER TABLE auth_enabler.user_roles ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.user_roles ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.user_roles ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE auth_enabler.user_roles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_user_roles_created_by ON auth_enabler.user_roles (created_by);",
            "CREATE INDEX IF NOT EXISTS idx_user_roles_updated_by ON auth_enabler.user_roles (updated_by);",
            
            # 6. user_sessions
            "ALTER TABLE auth_enabler.user_sessions ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.user_sessions ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.user_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE auth_enabler.user_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_created_by ON auth_enabler.user_sessions (created_by);",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_updated_by ON auth_enabler.user_sessions (updated_by);",
            
            # 7. audit_logs
            "ALTER TABLE auth_enabler.audit_logs ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.audit_logs ADD COLUMN IF NOT EXISTS updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;",
            "ALTER TABLE auth_enabler.audit_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "ALTER TABLE auth_enabler.audit_logs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_by ON auth_enabler.audit_logs (created_by);",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_updated_by ON auth_enabler.audit_logs (updated_by);",
            
            # Triggers for all 7 tables
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
                    CREATE TRIGGER update_users_updated_at
                    BEFORE UPDATE ON auth_enabler.users
                    FOR EACH ROW
                    EXECUTE FUNCTION auth_enabler.update_updated_at_column();
                END IF;
            END $$;
            """,
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
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_role_permissions_updated_at') THEN
                    CREATE TRIGGER update_role_permissions_updated_at
                    BEFORE UPDATE ON auth_enabler.role_permissions
                    FOR EACH ROW
                    EXECUTE FUNCTION auth_enabler.update_updated_at_column();
                END IF;
            END $$;
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_roles_updated_at') THEN
                    CREATE TRIGGER update_user_roles_updated_at
                    BEFORE UPDATE ON auth_enabler.user_roles
                    FOR EACH ROW
                    EXECUTE FUNCTION auth_enabler.update_updated_at_column();
                END IF;
            END $$;
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_sessions_updated_at') THEN
                    CREATE TRIGGER update_user_sessions_updated_at
                    BEFORE UPDATE ON auth_enabler.user_sessions
                    FOR EACH ROW
                    EXECUTE FUNCTION auth_enabler.update_updated_at_column();
                END IF;
            END $$;
            """,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_audit_logs_updated_at') THEN
                    CREATE TRIGGER update_audit_logs_updated_at
                    BEFORE UPDATE ON auth_enabler.audit_logs
                    FOR EACH ROW
                    EXECUTE FUNCTION auth_enabler.update_updated_at_column();
                END IF;
            END $$;
            """
        ]
        
        for q in queries:
            cur.execute(q)
            
        conn.commit()
        print("Database schema successfully upgraded with audit fields for ALL tables!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error executing migration: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
