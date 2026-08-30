import datetime
import logging
import secrets
import string

from psycopg2.errors import UniqueViolation

import auth.queries.user_queries as queries
from auth.config import get_config
from auth.constants.roles import PRIVILEGED_ROLES
from auth.db_connection import get_db_connection, release_db_connection
from auth.helpers.audit_helper import log_activity
from auth.helpers.password_helper import (
    hash_password,
    validate_password_strength,
    is_password_pwned,
)

logger = logging.getLogger(__name__)
config = get_config()

MAX_SUPER_ADMINS = 2
_TEMP_ALPHABET = string.ascii_letters + string.digits + "!@#$%"


def _format_user_datetime(user_dict):
    if not user_dict:
        return
    for field in [
        "created_at", "updated_at", "last_login", "approved_at", "temp_password_expiry",
    ]:
        if user_dict.get(field) and not isinstance(user_dict[field], str):
            user_dict[field] = user_dict[field].isoformat()


def _validate_password_or_error(password: str) -> dict | None:
    ok, reason = validate_password_strength(password)
    if not ok:
        return {"error": reason, "status": 400}
    if is_password_pwned(password):
        return {
            "error": "This password has appeared in a data breach. Choose a different password.",
            "status": 400,
        }
    return None


def get_super_admin_count(cur) -> int:
    cur.execute(
        """
        SELECT COUNT(DISTINCT ur.user_id) AS cnt
        FROM auth_enabler.user_roles ur
        JOIN auth_enabler.roles r ON ur.role_id = r.id
        WHERE r.name = 'Super Admin'
        """
    )
    row = cur.fetchone()
    return int(row["cnt"]) if row else 0


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
        logger.error("Error fetching users: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


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
            SELECT id, action, module, description, severity, created_at
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
        logger.error("Error fetching user by ID: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


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

    if role_name == "Super Admin":
        if get_super_admin_count(cur) >= MAX_SUPER_ADMINS:
            return {
                "error": "Super Admin seat limit reached. Demote an existing Super Admin first.",
                "status": 403,
            }

    if "Super Admin" in admin_roles:
        return {"role_name": role_name}

    if "Secondary Admin" in admin_roles:
        if role_name in PRIVILEGED_ROLES:
            return {
                "error": (
                    "Forbidden: Secondary Admins cannot assign admin-tier roles "
                    "(B2B or Mobile Admin)"
                ),
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
    pw_err = _validate_password_or_error(password)
    if pw_err:
        return pw_err

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
            admin_id,
            "CREATE_USER",
            "Users",
            f"Created user: {email} with role: {role_info[0]['name'] if role_info else 'None'}",
            severity="WARNING",
        )
        return {"data": user_data}
    except UniqueViolation:
        conn.rollback()
        return {"error": "User with this email already exists", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error("Error creating user: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


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
    if password:
        pw_err = _validate_password_or_error(password)
        if pw_err:
            return pw_err

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        target_roles = _get_user_role_names(cur, user_id)
        if "Super Admin" in target_roles:
            admin_roles = _get_user_role_names(cur, admin_id)
            if "Super Admin" not in admin_roles:
                return {
                    "error": "Forbidden: Only Super Admin can modify a Super Admin user",
                    "status": 403,
                }

        if role_id:
            admin_roles = _get_user_role_names(cur, admin_id)
            val_res = _validate_role_assignment(cur, admin_roles, role_id)
            if "error" in val_res:
                return val_res

        if mfa_enabled:
            cur.execute(
                "SELECT mfa_secret FROM auth_enabler.users WHERE id = %s",
                (user_id,),
            )
            mfa_row = cur.fetchone()
            if not mfa_row or not mfa_row.get("mfa_secret"):
                return {
                    "error": "Cannot enable MFA without completing TOTP setup via /api/auth/mfa/setup",
                    "status": 400,
                }

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
            cur.execute(
                """
                UPDATE auth_enabler.user_sessions
                SET revoked = TRUE, updated_at = NOW()
                WHERE user_id = %s AND revoked = FALSE
                """,
                (user_id,),
            )
            from auth.services.refresh_token_service import revoke_all_refresh_tokens_for_user

            revoke_all_refresh_tokens_for_user(user_id, cur=cur)
            log_activity(
                admin_id,
                "RESET_PASSWORD",
                "Users",
                f"Reset password for user {email}",
                severity="WARNING",
            )

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
            admin_id,
            "UPDATE_USER",
            "Users",
            f"Updated user: {email} (role: {role_info[0]['name'] if role_info else 'None'}, status: {status})",
            severity="WARNING",
        )
        return {"data": user_data}
    except UniqueViolation:
        conn.rollback()
        return {"error": "Email address already in use by another user", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error("Error updating user: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


def delete_user(user_id: int, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        target_roles = _get_user_role_names(cur, user_id)
        if "Super Admin" in target_roles:
            admin_roles = _get_user_role_names(cur, admin_id)
            if "Super Admin" not in admin_roles:
                return {
                    "error": "Forbidden: Only Super Admin can delete a Super Admin user",
                    "status": 403,
                }

        cur.execute("SELECT email FROM auth_enabler.users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            return {"error": "User not found", "status": 404}

        cur.execute(queries.DELETE_USER, (user_id,))
        conn.commit()
        log_activity(
            admin_id,
            "DELETE_USER",
            "Users",
            f"Deleted user: {user['email']} (ID: {user_id})",
            severity="CRITICAL",
        )
        return {"data": "User deleted successfully"}
    except Exception as e:
        conn.rollback()
        logger.error("Error deleting user: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


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
        logger.error("Error fetching pending users: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


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

        temp_password = "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(12))
        hashed_temp_password = hash_password(temp_password)
        temp_password_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            hours=config.TEMP_PASSWORD_EXPIRY_HOURS
        )

        cur.execute(
            queries.APPROVE_USER,
            (admin_id, hashed_temp_password, temp_password_expiry, admin_id, user_id),
        )
        approved_user = cur.fetchone()

        cur.execute(queries.CLEAR_USER_ROLES, (user_id,))
        cur.execute(queries.ASSIGN_ROLE_TO_USER, (user_id, role_id, admin_id, admin_id))
        conn.commit()

        from auth.helpers.email_helper import send_credentials_email

        cur.execute("SELECT full_name FROM auth_enabler.users WHERE id = %s", (user_id,))
        profile = cur.fetchone()
        send_credentials_email(
            user["email"],
            profile["full_name"] if profile else user["email"],
            role_name,
            temp_password,
        )

        log_activity(
            admin_id,
            "APPROVE_USER",
            "Users",
            f"Approved user: {user['email']} with role: {role_name}",
            severity="CRITICAL",
        )
        _format_user_datetime(approved_user)

        return {
            "data": {
                "user": approved_user,
                "role": {"id": role_id, "name": role_name},
            },
            "message": f"User approved as {role_name}. Login credentials sent by email.",
        }
    except Exception as e:
        conn.rollback()
        logger.error("Error approving user: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


def approve_user_by_role_name(user_id: int, role_name: str, admin_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM auth_enabler.roles WHERE name = %s", (role_name,))
        role = cur.fetchone()
        if not role:
            return {"error": f"Role '{role_name}' not found", "status": 400}
        role_id = role["id"]
    finally:
        release_db_connection(conn)
    return approve_user(user_id, role_id, admin_id)


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
        log_activity(admin_id, "REJECT_USER", "Users", desc, severity="WARNING")
        _format_user_datetime(rejected_user)

        return {"data": rejected_user, "message": "Signup request rejected."}
    except Exception as e:
        conn.rollback()
        logger.error("Error rejecting user: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)
