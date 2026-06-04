from functools import wraps
from flask import request, g
from helpers.jwt_helper import decode_token
from helpers.response_helper import error_response
from db.connection import get_db_connection
from queries.role_queries import CHECK_USER_PERMISSION

FIRST_LOGIN_ALLOWED_PATHS = {
    "/api/auth/change-temp-password",
    "/api/auth/logout",
    "/api/auth/refresh",
}


def require_auth(f):
    """
    Middleware decorator to ensure a valid JWT token is present in the Authorization header.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return error_response("Missing or invalid Authorization header", 401)

        token = auth_header.split(" ")[1]
        decoded = decode_token(token)

        if isinstance(decoded, str):
            return error_response(decoded, 401)

        g.user = decoded

        user_id = decoded.get("sub")
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT is_first_login, registration_status, status
                FROM auth_enabler.users WHERE id = %s;
                """,
                (user_id,),
            )
            user_row = cur.fetchone()
            if not user_row:
                return error_response("User account not found", 401)

            reg_status = user_row.get("registration_status", "PENDING")
            if reg_status != "APPROVED":
                return error_response(
                    f"Forbidden: Account registration status is {reg_status}", 403
                )

            if user_row.get("status") != "active":
                return error_response("User account is inactive", 403)

            if user_row.get("is_first_login") and request.path not in FIRST_LOGIN_ALLOWED_PATHS:
                return error_response("Password change required on first login.", 403)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Middleware user verification error: {e}")
            return error_response("Internal Server Error", 500)
        finally:
            if conn:
                conn.close()

        return f(*args, **kwargs)
    return decorated


def get_implied_permissions(permission_name):
    """
    Returns permission names that satisfy the requested permission via hierarchy:
    DELETE -> WRITE -> READ
    """
    hierarchy = {
        "read": ["read", "view", "write", "create", "edit", "delete"],
        "view": ["read", "view", "write", "create", "edit", "delete"],
        "write": ["write", "create", "edit", "delete"],
        "create": ["write", "create", "edit", "delete"],
        "edit": ["write", "create", "edit", "delete"],
        "delete": ["delete"],
        "approve": ["approve"],
        "assign": ["assign"],
        "manage": ["manage"],
    }

    implied = [permission_name]

    if "." in permission_name:
        module, action = permission_name.rsplit(".", 1)
        if action in hierarchy:
            for satisfying_action in hierarchy[action]:
                implied.append(f"{module}.{satisfying_action}")

    return list(set(implied))


def require_permission(permission_name):
    """
    Middleware decorator to check if the authenticated user has a specific permission.
    Supports permission inheritance hierarchy.
    Must be stacked under @require_auth.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = g.user.get("sub")

            if not user_id:
                return error_response("Unauthorized", 401)

            allowed_perms = get_implied_permissions(permission_name)
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                cur.execute(CHECK_USER_PERMISSION, (user_id, allowed_perms))
                result = cur.fetchone()

                if not result:
                    return error_response(
                        f"Forbidden: You do not have the '{permission_name}' permission.", 403
                    )

                return f(*args, **kwargs)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Permission check error: {e}")
                return error_response("Internal Server Error", 500)
            finally:
                if conn:
                    conn.close()

        return decorated_function
    return decorator
