GET_USER_BY_EMAIL = """
    SELECT id, full_name, email, password_hash, status, registration_status,
           is_first_login, temp_password_expiry, requested_role, organization
    FROM auth_enabler.users
    WHERE email = %s;
"""

CREATE_USER = """
    INSERT INTO auth_enabler.users (
        full_name, email, password_hash, status, registration_status,
        phone, department, employee_id
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id, full_name, email, status, registration_status, phone, department, employee_id, created_at;
"""

CREATE_PENDING_USER = """
    INSERT INTO auth_enabler.users (
        full_name, email, password_hash, status, registration_status,
        phone, organization, signup_message
    )
    VALUES (%s, %s, %s, %s, 'PENDING', %s, %s, %s)
    RETURNING id, full_name, email, status, registration_status, organization, created_at;
"""
