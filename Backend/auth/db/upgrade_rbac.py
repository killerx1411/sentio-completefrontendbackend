import sys
import os

# Adjust path to import connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.db_connection import get_db_connection

def run_rbac_upgrade():
    print("Connecting to database...")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # 1. Ensure Roles exist
        roles = [
            ('Super Admin', 'Super administrator with system-wide controls.'),
            ('Admin', 'Secondary administrator for user operations.'),
            ('Teacher', 'Operational educator.'),
            ('Behaviour Scientist', 'Analytical role.'),
            ('Sentio Mind', 'Platform/business operational user.')
        ]
        
        print("Upserting roles...")
        for r_name, r_desc in roles:
            cur.execute("""
                INSERT INTO auth_enabler.roles (name, description) 
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                RETURNING id;
            """, (r_name, r_desc))
        
        # 2. Re-create Permissions
        print("Cleaning up old permissions and mapping tables...")
        cur.execute("DELETE FROM auth_enabler.role_permissions;")
        cur.execute("DELETE FROM auth_enabler.permissions;")
        
        permissions = [
            ('users.view', 'Users', 'READ', 'View list of users and detail profiles'),
            ('users.create', 'Users', 'CREATE', 'Create new user profiles'),
            ('users.edit', 'Users', 'UPDATE', 'Edit existing user profiles, reset passwords, deactivate accounts'),
            ('users.delete', 'Users', 'DELETE', 'Permanently delete user profiles'),
            ('roles.manage', 'Roles', 'ALL', 'Manage role-permission mappings and role architecture'),
            ('audit.view', 'Audit Logs', 'READ', 'View platform compliance and security logs'),
            ('reports.export', 'Reports', 'EXPORT', 'Export platform reports'),
            ('students.manage', 'Students', 'ALL', 'Manage student profiles and assignments'),
            ('ai.use', 'SentioMind', 'EXECUTE', 'Access to AI predictive modeling')
        ]
        
        print("Inserting granular permissions...")
        for p_name, p_mod, p_act, p_desc in permissions:
            cur.execute("""
                INSERT INTO auth_enabler.permissions (name, module, action, description) 
                VALUES (%s, %s, %s, %s);
            """, (p_name, p_mod, p_act, p_desc))
            
        # 3. Map Permissions to Roles
        # Super Admin: all
        print("Mapping permissions to Super Admin role...")
        cur.execute("""
            INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM auth_enabler.roles r CROSS JOIN auth_enabler.permissions p
            WHERE r.name = 'Super Admin'
            ON CONFLICT DO NOTHING;
        """)
        
        # Admin: all except roles.manage
        print("Mapping permissions to standard Admin role...")
        cur.execute("""
            INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM auth_enabler.roles r CROSS JOIN auth_enabler.permissions p
            WHERE r.name = 'Admin' AND p.name != 'roles.manage'
            ON CONFLICT DO NOTHING;
        """)
        
        # Teacher: users.view, students.manage
        print("Mapping permissions to Teacher role...")
        cur.execute("""
            INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM auth_enabler.roles r CROSS JOIN auth_enabler.permissions p
            WHERE r.name = 'Teacher' AND p.name IN ('users.view', 'students.manage')
            ON CONFLICT DO NOTHING;
        """)
        
        # Behaviour Scientist: reports.export
        print("Mapping permissions to Behaviour Scientist role...")
        cur.execute("""
            INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM auth_enabler.roles r CROSS JOIN auth_enabler.permissions p
            WHERE r.name = 'Behaviour Scientist' AND p.name = 'reports.export'
            ON CONFLICT DO NOTHING;
        """)
        
        # Sentio Mind: ai.use
        print("Mapping permissions to Sentio Mind role...")
        cur.execute("""
            INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM auth_enabler.roles r CROSS JOIN auth_enabler.permissions p
            WHERE r.name = 'Sentio Mind' AND p.name = 'ai.use'
            ON CONFLICT DO NOTHING;
        """)
        
        # 4. Migrate admin@sentiomind.com to Super Admin
        print("Migrating default admin user to 'Super Admin' role...")
        # Get role ID of Super Admin
        cur.execute("SELECT id FROM auth_enabler.roles WHERE name = 'Super Admin';")
        super_admin_role = cur.fetchone()
        
        if super_admin_role:
            super_admin_role_id = super_admin_role['id']
            # Get user ID of admin@sentiomind.com
            cur.execute("SELECT id FROM auth_enabler.users WHERE email = 'admin@sentiomind.com';")
            admin_user = cur.fetchone()
            
            if admin_user:
                admin_user_id = admin_user['id']
                # Clear existing roles
                cur.execute("DELETE FROM auth_enabler.user_roles WHERE user_id = %s;", (admin_user_id,))
                # Assign Super Admin role
                cur.execute("INSERT INTO auth_enabler.user_roles (user_id, role_id) VALUES (%s, %s);", (admin_user_id, super_admin_role_id))
                print(f"Default admin (user ID {admin_user_id}) successfully upgraded to 'Super Admin' role.")
            else:
                print("Warning: admin@sentiomind.com user not found in database.", file=sys.stderr)
        else:
            print("Error: 'Super Admin' role was not created successfully.", file=sys.stderr)
            
        conn.commit()
        print("RBAC Upgrade completed successfully!")
        
        cur.close()
        conn.close()
    except Exception as e:
        conn.rollback()
        print(f"Error during RBAC upgrade: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_rbac_upgrade()
