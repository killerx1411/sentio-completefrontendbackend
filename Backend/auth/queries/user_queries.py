GET_ALL_USERS = """
    SELECT u.id, u.full_name, u.email, u.status, u.registration_status, u.phone, u.department,
           u.employee_id, u.mfa_enabled, u.last_login, u.profile_image, u.approved_by, u.approved_at,
           u.is_first_login, u.temp_password_expiry, u.school_id AS assigned_school, u.class_id AS assigned_class,
           u.organization, u.requested_role, u.created_at, u.updated_at,
           COALESCE(json_agg(json_build_object('id', r.id, 'name', r.name))
             FILTER (WHERE r.id IS NOT NULL), '[]') AS roles
    FROM auth_enabler.users u
    LEFT JOIN auth_enabler.user_roles ur ON u.id = ur.user_id
    LEFT JOIN auth_enabler.roles r ON ur.role_id = r.id
    GROUP BY u.id
    ORDER BY u.created_at DESC;
"""

GET_USER_BY_ID = """
    SELECT u.id, u.full_name, u.email, u.status, u.registration_status, u.phone, u.department,
           u.employee_id, u.mfa_enabled, u.last_login, u.profile_image, u.approved_by, u.approved_at,
           u.is_first_login, u.temp_password_expiry, u.school_id AS assigned_school, u.class_id AS assigned_class,
           u.organization, u.requested_role, u.created_at, u.updated_at,
           COALESCE(json_agg(json_build_object('id', r.id, 'name', r.name))
             FILTER (WHERE r.id IS NOT NULL), '[]') AS roles
    FROM auth_enabler.users u
    LEFT JOIN auth_enabler.user_roles ur ON u.id = ur.user_id
    LEFT JOIN auth_enabler.roles r ON ur.role_id = r.id
    WHERE u.id = %s
    GROUP BY u.id;
"""

GET_PENDING_USERS = """
    SELECT u.id, u.full_name, u.email, u.status, u.registration_status, u.phone, u.department,
           u.employee_id, u.mfa_enabled, u.profile_image, u.organization, u.signup_message,
           u.requested_role, u.created_at, u.updated_at,
           COALESCE(json_agg(json_build_object('id', r.id, 'name', r.name))
             FILTER (WHERE r.id IS NOT NULL), '[]') AS roles
    FROM auth_enabler.users u
    LEFT JOIN auth_enabler.user_roles ur ON u.id = ur.user_id
    LEFT JOIN auth_enabler.roles r ON ur.role_id = r.id
    WHERE u.registration_status = 'PENDING'
    GROUP BY u.id
    ORDER BY u.created_at DESC;
"""

CREATE_USER = """
    INSERT INTO auth_enabler.users (
        full_name, email, password_hash, status, registration_status, is_first_login,
        phone, department, employee_id, mfa_enabled, profile_image, created_by, updated_by
    )
    VALUES (%s, %s, %s, %s, 'APPROVED', FALSE, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id, full_name, email, status, registration_status, phone, department, employee_id,
              mfa_enabled, profile_image, created_at, updated_at;
"""

UPDATE_USER = """
    UPDATE auth_enabler.users
    SET full_name = %s, email = %s, status = %s, phone = %s, department = %s, employee_id = %s,
        mfa_enabled = %s, profile_image = %s, school_id = %s, class_id = %s, updated_by = %s
    WHERE id = %s
    RETURNING id, full_name, email, status, registration_status, phone, department, employee_id,
              mfa_enabled, profile_image, school_id AS assigned_school, class_id AS assigned_class, updated_at;
"""

DELETE_USER = """
    DELETE FROM auth_enabler.users
    WHERE id = %s;
"""

CLEAR_USER_ROLES = """
    DELETE FROM auth_enabler.user_roles
    WHERE user_id = %s;
"""

ASSIGN_ROLE_TO_USER = """
    INSERT INTO auth_enabler.user_roles (user_id, role_id, created_by, updated_by)
    VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;
"""

APPROVE_USER = """
    UPDATE auth_enabler.users
    SET registration_status = 'APPROVED', status = 'active', approved_by = %s, approved_at = NOW(),
        password_hash = %s, is_first_login = TRUE, temp_password_expiry = %s, updated_by = %s
    WHERE id = %s
    RETURNING id, full_name, email, status, registration_status, phone, department, employee_id,
              mfa_enabled, profile_image, approved_at;
"""

REJECT_USER = """
    UPDATE auth_enabler.users
    SET registration_status = 'REJECTED', status = 'inactive', updated_by = %s
    WHERE id = %s
    RETURNING id, full_name, email, status, registration_status;
"""
