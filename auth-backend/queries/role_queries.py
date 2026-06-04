# Roles
CREATE_ROLE = """
    INSERT INTO auth_enabler.roles (name, description, created_by, updated_by)
    VALUES (%s, %s, %s, %s)
    RETURNING id, name, description, created_at, updated_at;
"""

GET_ALL_ROLES = "SELECT * FROM auth_enabler.roles ORDER BY id ASC;"

# Permissions
CREATE_PERMISSION = """
    INSERT INTO auth_enabler.permissions (name, module, action, description, created_by, updated_by)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, name, module, action, description, created_at, updated_at;
"""

GET_ALL_PERMISSIONS = "SELECT * FROM auth_enabler.permissions;"

# Role-Permissions
ASSIGN_PERMISSION_TO_ROLE = """
    INSERT INTO auth_enabler.role_permissions (role_id, permission_id, created_by, updated_by)
    VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;
"""

REMOVE_PERMISSION_FROM_ROLE = """
    DELETE FROM auth_enabler.role_permissions
    WHERE role_id = %s AND permission_id = %s;
"""

# User-Roles
ASSIGN_ROLE_TO_USER = """
    INSERT INTO auth_enabler.user_roles (user_id, role_id, created_by, updated_by)
    VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;
"""

REMOVE_ROLE_FROM_USER = """
    DELETE FROM auth_enabler.user_roles
    WHERE user_id = %s AND role_id = %s;
"""

# Verification Query for Middleware
CHECK_USER_PERMISSION = """
    SELECT 1 
    FROM auth_enabler.user_roles ur
    JOIN auth_enabler.role_permissions rp ON ur.role_id = rp.role_id
    JOIN auth_enabler.permissions p ON rp.permission_id = p.id
    WHERE ur.user_id = %s AND p.name = ANY(%s);
"""
