import datetime
import logging
import random
import string

from db.connection import get_db_connection
import queries.user_queries as queries
from helpers.password_helper import hash_password
from helpers.audit_helper import log_activity
from constants.roles import ROLE_CONFIG, ADMIN_ROLES
from psycopg2.errors import UniqueViolation

logger = logging.getLogger(__name__)


def _format_user_datetime(user_dict):
    if not user_dict:
        return
    for field in ["created_at", "updated_at", "last_login", "approved_at", "temp_password_expiry"]:
        if user_dict.get(field) and not isinstance(user_dict[field], str):
            user_dict[field] = user_dict[field].isoformat()


def get_all_users():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.GET_ALL_USERS)
        users = cur.fetchall()
        for u in users:
            _format_user_datetime(u)
        return {"data": users}
    except Exception as e:
        logger.error("Error fetching users: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.GET_USER_BY_ID, (user_id,))
        user = cur.fetchone()
        if not user:
            return {"error": "User not found", "status": 404}

        _format_user_datetime(user)

        cur.execute(
            """
            SELECT DISTINCT p.id, p.name, p.module, p.action, p.description
            FROM auth_enabler.user_roles ur
            JOIN auth_enabler.role_permissions rp ON ur.role_id = rp.role_id
            JOIN auth_enabler.permissions p ON rp.permission_id = p.id
            WHERE ur.user_id = %s;
            """,
            (user_id,),
        )
        permissions = cur.fetchall()

        cur.execute(
            """
            SELECT id, action, module, description, created_at
            FROM auth_enabler.audit_logs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 20;
            """,
            (user_id,),
        )
        audit_logs = cur.fetchall()
        for log in audit_logs:
            if log.get("created_at"):
                log["created_at"] = log["created_at"].isoformat()

        return {"data": {"user": user, "permissions": permissions, "audit_logs": audit_logs}}
    except Exception as e:
        logger.error("Error fetching user by ID: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()


def _get_user_role_names(cur, user_id):
    cur.execute(
        """
        SELECT r.name
        FROM auth_enabler.user_roles ur
        JOIN auth_enabler.roles r ON ur.role_id = r.id
        WHERE ur.user_id = %s
        """,
        (user_id,),
    )
    return [row["name"] for row in cur.fetchall()]


def _validate_role_assignment(cur, admin_roles, role_id_to_assign):
    cur.execute("SELECT name FROM auth_enabler.roles WHERE id = %s", (role_id_to_assign,))
    role_row = cur.fetchone()
    if not role_row:
        return {"error": "The assigned role does not exist", "status": 400}
    role_name = role_row["name"]

    if "Super Admin" in admin_roles:
        return {"role_name": role_name}

    if "Secondary Admin" in admin_roles:
        if role_name in ADMIN_ROLES:
            return {
                "error": "Forbidden: Secondary Admins cannot assign Super Admin, Secondary Admin, or Normal Admin roles",
                "status": 403,
            }
        return {"role_name": role_name}

    return {"error": "Forbidden: You do not have permission to assign roles", "status": 403}


def create_user(
    full_name: str,
    email: str,
    password: str,
    status: str,
    role_id: int = None,
    phone: str = None,
    department: str = None,
    employee_id: str = None,
    mfa_enabled: bool = False,
    profile_image: str = None,
    assigned_school: str = None,
    assigned_class: str = None,
    admin_id: int = None,
):
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if role_id:
            admin_roles = _get_user_role_names(cur, admin_id)
            val_res = _validate_role_assignment(cur, admin_roles, role_id)
            if "error" in val_res:
                return val_res

        hashed_pw = hash_password(password)
        cur.execute(
            queries.CREATE_USER,
            (
                full_name, email, hashed_pw, status or "active",
                phone, department, employee_id, mfa_enabled, profile_image,
                admin_id, admin_id,
            ),
        )
        new_user = cur.fetchone()
        user_id = new_user["id"]

        if assigned_school or assigned_class:
            cur.execute(
                """
                UPDATE auth_enabler.users
                SET assigned_school = %s, assigned_class = %s
                WHERE id = %s
                """,
                (assigned_school, assigned_class, user_id),
            )

        role_info = []
        if role_id:
            cur.execute(queries.ASSIGN_ROLE_TO_USER, (user_id, role_id, admin_id, admin_id))
            cur.execute("SELECT id, name FROM auth_enabler.roles WHERE id = %s", (role_id,))
            role = cur.fetchone()
            if role:
                role_info.append(role)

        conn.commit()
        _format_user_datetime(new_user)
        user_data = {**new_user, "roles": role_info}
        log_activity(
            admin_id, "CREATE_USER", "Users",
            f"Created user: {email} with role: {role_info[0]['name'] if role_info else 'None'}",
        )
        return {"data": user_data}
    except UniqueViolation:
        conn.rollback()
        return {"error": "User with this email already exists", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error("Error creating user: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()


def update_user(
    user_id: int,
    full_name: str,
    email: str,
    status: str,
    role_id: int = None,
    phone: str = None,
    department: str = None,
    employee_id: str = None,
    mfa_enabled: bool = False,
    profile_image: str = None,
    assigned_school: str = None,
    assigned_class: str = None,
    password: str = None,
    admin_id: int = None,
):
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        target_roles = _get_user_role_names(cur, user_id)
        if "Super Admin" in target_roles:
            admin_roles = _get_user_role_names(cur, admin_id)
            if "Super Admin" not in admin_roles:
                return {"error": "Forbidden: Only Super Admin can modify a Super Admin user", "status": 403}

        if role_id:
            admin_roles = _get_user_role_names(cur, admin_id)
            val_res = _validate_role_assignment(cur, admin_roles, role_id)
            if "error" in val_res:
                return val_res

        cur.execute(
            queries.UPDATE_USER,
            (
                full_name, email, status, phone, department, employee_id,
                mfa_enabled, profile_image, assigned_school, assigned_class,
                admin_id, user_id,
            ),
        )
        updated_user = cur.fetchone()
        if not updated_user:
            conn.rollback()
            return {"error": "User not found", "status": 404}

        if password:
            hashed_pw = hash_password(password)
            cur.execute(
                "UPDATE auth_enabler.users SET password_hash = %s WHERE id = %s",
                (hashed_pw, user_id),
            )
            log_activity(admin_id, "RESET_PASSWORD", "Users", f"Reset password for user {email}")

        cur.execute(queries.CLEAR_USER_ROLES, (user_id,))
        role_info = []
        if role_id:
            cur.execute(queries.ASSIGN_ROLE_TO_USER, (user_id, role_id, admin_id, admin_id))
            cur.execute("SELECT id, name FROM auth_enabler.roles WHERE id = %s", (role_id,))
            role = cur.fetchone()
            if role:
                role_info.append(role)

        conn.commit()
        _format_user_datetime(updated_user)
        user_data = {**updated_user, "roles": role_info}
        log_activity(
            admin_id, "UPDATE_USER", "Users",
            f"Updated user: {email} (role: {role_info[0]['name'] if role_info else 'None'}, status: {status})",
        )
        return {"data": user_data}
    except UniqueViolation:
        conn.rollback()
        return {"error": "Email address already in use by another user", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error("Error updating user: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()


def delete_user(user_id: int, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        target_roles = _get_user_role_names(cur, user_id)
        if "Super Admin" in target_roles:
            admin_roles = _get_user_role_names(cur, admin_id)
            if "Super Admin" not in admin_roles:
                return {"error": "Forbidden: Only Super Admin can delete a Super Admin user", "status": 403}

        cur.execute("SELECT email FROM auth_enabler.users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            return {"error": "User not found", "status": 404}

        cur.execute(queries.DELETE_USER, (user_id,))
        conn.commit()
        log_activity(admin_id, "DELETE_USER", "Users", f"Deleted user: {user['email']} (ID: {user_id})")
        return {"data": "User deleted successfully"}
    except Exception as e:
        conn.rollback()
        logger.error("Error deleting user: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()


def get_pending_users():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.GET_PENDING_USERS)
        users = cur.fetchall()
        for u in users:
            _format_user_datetime(u)
        return {"data": users}
    except Exception as e:
        logger.error("Error fetching pending users: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()


def approve_user(user_id: int, role_id: int, admin_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT email, registration_status FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        user = cur.fetchone()
        if not user:
            return {"error": "User not found", "status": 404}
        if user["registration_status"] != "PENDING":
            return {
                "error": f"User is not in PENDING state (current: {user['registration_status']})",
                "status": 400,
            }

        admin_roles = _get_user_role_names(cur, admin_id)
        if "Super Admin" not in admin_roles:
            return {"error": "Forbidden: Only Super Admin can approve users", "status": 403}

        val_res = _validate_role_assignment(cur, admin_roles, role_id)
        if "error" in val_res:
            return val_res
        role_name = val_res["role_name"]

        alphabet = string.ascii_letters + string.digits
        temp_password = "".join(random.choices(alphabet, k=8))
        hashed_temp_password = hash_password(temp_password)
        temp_password_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)

        cur.execute(
            queries.APPROVE_USER,
            (admin_id, hashed_temp_password, temp_password_expiry, admin_id, user_id),
        )
        approved_user = cur.fetchone()

        cur.execute(queries.CLEAR_USER_ROLES, (user_id,))
        cur.execute(queries.ASSIGN_ROLE_TO_USER, (user_id, role_id, admin_id, admin_id))
        conn.commit()

        from helpers.email_helper import send_credentials_email

        cur.execute("SELECT full_name FROM auth_enabler.users WHERE id = %s", (user_id,))
        profile = cur.fetchone()
        send_credentials_email(
            user["email"],
            profile["full_name"] if profile else user["email"],
            role_name,
            temp_password,
        )

        log_activity(admin_id, "APPROVE_USER", "Users", f"Approved user: {user['email']} with role: {role_name}")
        _format_user_datetime(approved_user)

        return {
            "data": {
                "user": approved_user,
                "role": {"id": role_id, "name": role_name},
                "temp_password": temp_password,
            },
            "message": f"User approved as {role_name}. Login credentials sent by email.",
        }
    except Exception as e:
        conn.rollback()
        logger.error("Error approving user: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()


def approve_user_by_role_name(user_id: int, role_name: str, admin_id: int):
    """Legacy helper for signup approval flows that pass role name instead of role_id."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM auth_enabler.roles WHERE name = %s", (role_name,))
        role = cur.fetchone()
        if not role:
            return {"error": f"Role '{role_name}' not found", "status": 400}
        return approve_user(user_id, role["id"], admin_id)
    finally:
        if conn:
            conn.close()


def reject_user(user_id: int, admin_id: int, reason: str = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT email, registration_status FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        user = cur.fetchone()
        if not user:
            return {"error": "User not found", "status": 404}
        if user["registration_status"] != "PENDING":
            return {
                "error": f"User is not in PENDING state (current: {user['registration_status']})",
                "status": 400,
            }

        admin_roles = _get_user_role_names(cur, admin_id)
        if "Super Admin" not in admin_roles:
            return {"error": "Forbidden: Only Super Admin can reject users", "status": 403}

        cur.execute(queries.REJECT_USER, (admin_id, user_id))
        rejected_user = cur.fetchone()
        conn.commit()

        desc = f"Rejected signup for {user['email']}"
        if reason:
            desc += f": {reason}"
        log_activity(admin_id, "REJECT_USER", "Users", desc)
        _format_user_datetime(rejected_user)

        return {"data": rejected_user, "message": "Signup request rejected."}
    except Exception as e:
        conn.rollback()
        logger.error("Error rejecting user: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()
