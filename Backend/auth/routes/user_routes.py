from flask import Blueprint, request, g
import logging

import auth.services.user_service as user_service
from auth.constants.roles import PRIVILEGED_ROLES
from auth.helpers.response_helper import success_response, error_response, sanitize_user_output
from auth.helpers.validation_helper import sanitize_email, sanitize_string
from auth.middleware.auth_middleware import require_auth, require_permission
from auth.db_connection import get_db_connection, release_db_connection

logger = logging.getLogger(__name__)

user_bp = Blueprint("users", __name__, url_prefix="/api")


def get_role_name(role_id):
    if not role_id:
        return None
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM auth_enabler.roles WHERE id = %s;", (role_id,))
        res = cur.fetchone()
        return res["name"] if res else None
    except Exception:
        return None
    finally:
        release_db_connection(conn)


def is_user_super_admin(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM auth_enabler.user_roles ur
            JOIN auth_enabler.roles r ON ur.role_id = r.id
            WHERE ur.user_id = %s AND r.name = 'Super Admin';
            """,
            (user_id,),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        release_db_connection(conn)


def is_user_secondary_admin(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM auth_enabler.user_roles ur
            JOIN auth_enabler.roles r ON ur.role_id = r.id
            WHERE ur.user_id = %s AND r.name = 'Secondary Admin';
            """,
            (user_id,),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        release_db_connection(conn)


def _sanitize_users_list(users):
    return [sanitize_user_output(dict(u)) for u in users]


@user_bp.route("/users", methods=["GET"])
@require_auth
@require_permission("users.read")
def get_users():
    result = user_service.get_all_users()
    if "error" in result:
        return error_response(result["error"], result.get("status", 500))
    return success_response(data=_sanitize_users_list(result["data"]))


@user_bp.route("/users/<int:user_id>", methods=["GET"])
@require_auth
@require_permission("users.read")
def get_user_detail(user_id):
    result = user_service.get_user_by_id(user_id)
    if "error" in result:
        return error_response(result["error"], result.get("status", 500))
    data = result["data"]
    data["user"] = sanitize_user_output(data["user"])
    current_user_id = g.user.get("sub")
    if not is_user_super_admin(current_user_id):
        data["audit_logs"] = []
    return success_response(data=data)


@user_bp.route("/users", methods=["POST"])
@require_auth
@require_permission("users.write")
def create_user():
    data = request.get_json()
    if not data or not data.get("full_name") or not data.get("email") or not data.get("password"):
        return error_response("Full name, email, and password are required", 400)

    try:
        email = sanitize_email(data.get("email"))
        full_name = sanitize_string(data.get("full_name"), 120, "full_name")
        department = (
            sanitize_string(data["department"], 100, "department")
            if data.get("department")
            else None
        )
        employee_id = (
            sanitize_string(data["employee_id"], 50, "employee_id")
            if data.get("employee_id")
            else None
        )
    except ValueError as exc:
        return error_response(str(exc), 400)

    current_user_id = g.user.get("sub")
    role_id = data.get("role_id")
    role_name = get_role_name(role_id)
    if role_name in PRIVILEGED_ROLES and not is_user_super_admin(current_user_id):
        return error_response(
            "Forbidden: Only Super Admin can assign admin-tier roles", 403
        )

    result = user_service.create_user(
        full_name=full_name,
        email=email,
        password=data.get("password"),
        status=data.get("status", "active"),
        role_id=role_id,
        phone=data.get("phone"),
        department=department,
        employee_id=employee_id,
        mfa_enabled=data.get("mfa_enabled", False),
        profile_image=data.get("profile_image"),
        assigned_school=data.get("assigned_school"),
        assigned_class=data.get("assigned_class"),
        admin_id=current_user_id,
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(
        data=sanitize_user_output(result["data"]),
        message="User created successfully",
        status_code=201,
    )


@user_bp.route("/users/<int:user_id>", methods=["PUT"])
@require_auth
@require_permission("users.write")
def update_user(user_id):
    data = request.get_json()
    if not data or not data.get("full_name") or not data.get("email"):
        return error_response("Full name and email are required", 400)

    try:
        email = sanitize_email(data.get("email"))
        full_name = sanitize_string(data.get("full_name"), 120, "full_name")
        department = (
            sanitize_string(data["department"], 100, "department")
            if data.get("department")
            else None
        )
        employee_id = (
            sanitize_string(data["employee_id"], 50, "employee_id")
            if data.get("employee_id")
            else None
        )
    except ValueError as exc:
        return error_response(str(exc), 400)

    current_user_id = g.user.get("sub")
    is_current_super = is_user_super_admin(current_user_id)

    if is_user_super_admin(user_id) and not is_current_super:
        return error_response("Forbidden: You cannot modify a Super Admin user", 403)

    role_id = data.get("role_id")
    role_name = get_role_name(role_id)
    if role_name in PRIVILEGED_ROLES and not is_current_super:
        return error_response("Forbidden: Only Super Admin can assign admin-tier roles", 403)

    result = user_service.update_user(
        user_id=user_id,
        full_name=full_name,
        email=email,
        status=data.get("status", "active"),
        role_id=role_id,
        phone=data.get("phone"),
        department=department,
        employee_id=employee_id,
        mfa_enabled=data.get("mfa_enabled", False),
        profile_image=data.get("profile_image"),
        assigned_school=data.get("assigned_school"),
        assigned_class=data.get("assigned_class"),
        password=data.get("password"),
        admin_id=current_user_id,
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(
        data=sanitize_user_output(result["data"]),
        message="User updated successfully",
    )


@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_auth
@require_permission("users.delete")
def delete_user(user_id):
    current_user_id = g.user.get("sub")
    if is_user_super_admin(user_id) and not is_user_super_admin(current_user_id):
        return error_response("Forbidden: You cannot delete a Super Admin user", 403)

    result = user_service.delete_user(user_id, admin_id=current_user_id)
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(message=result["data"])


@user_bp.route("/dashboard/stats", methods=["GET"])
@require_auth
@require_permission("users.read")
def get_dashboard_stats():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS count FROM auth_enabler.users;")
        total_users = cur.fetchone()["count"]
        cur.execute("SELECT COUNT(*) AS count FROM auth_enabler.roles;")
        active_roles = cur.fetchone()["count"]
        cur.execute("SELECT COUNT(*) AS count FROM auth_enabler.permissions;")
        total_permissions = cur.fetchone()["count"]
        cur.execute(
            "SELECT COUNT(*) AS count FROM auth_enabler.audit_logs WHERE action = 'LOGIN_SUCCESS';"
        )
        recent_logins = cur.fetchone()["count"]
        return success_response(
            data={
                "total_users": total_users,
                "active_roles": active_roles,
                "total_permissions": total_permissions,
                "recent_logins": recent_logins,
            }
        )
    except Exception as e:
        logger.error("Error fetching dashboard stats: %s", e, exc_info=True)
        return error_response("Failed to fetch dashboard stats", 500)
    finally:
        release_db_connection(conn)
