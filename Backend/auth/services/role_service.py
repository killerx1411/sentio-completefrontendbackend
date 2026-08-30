import logging

from psycopg2.errors import UniqueViolation

import auth.queries.role_queries as queries
from auth.db_connection import get_db_connection, release_db_connection
from auth.helpers.audit_helper import log_activity

logger = logging.getLogger(__name__)


def create_role(name: str, description: str, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.CREATE_ROLE, (name, description, admin_id, admin_id))
        role = cur.fetchone()
        conn.commit()

        log_activity(admin_id, "CREATE_ROLE", "Roles", f"Created new role: {name}", severity="INFO")

        return {"data": role}
    except UniqueViolation:
        conn.rollback()
        return {"error": "Role name already exists", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error("Error creating role: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


def get_all_roles():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.GET_ALL_ROLES)
        roles = cur.fetchall()
        return {"data": roles}
    except Exception as e:
        logger.error("Error fetching roles: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


def create_permission(name: str, module: str, action: str, description: str, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            queries.CREATE_PERMISSION,
            (name, module, action, description, admin_id, admin_id),
        )
        permission = cur.fetchone()
        conn.commit()

        log_activity(
            admin_id, "CREATE_PERMISSION", "Roles",
            f"Created new permission: {name}", severity="INFO",
        )

        return {"data": permission}
    except UniqueViolation:
        conn.rollback()
        return {"error": "Permission name already exists", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error("Error creating permission: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


def assign_permission_to_role(role_id: int, permission_id: int, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            queries.ASSIGN_PERMISSION_TO_ROLE,
            (role_id, permission_id, admin_id, admin_id),
        )
        conn.commit()

        log_activity(
            admin_id,
            "ASSIGN_PERMISSION",
            "Roles",
            f"Assigned permission {permission_id} to role {role_id}",
            severity="CRITICAL",
        )

        return {"data": "Permission assigned to role successfully"}
    except Exception as e:
        conn.rollback()
        logger.error("Error assigning permission: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


def assign_role_to_user(user_id: int, role_id: int, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM auth_enabler.roles WHERE id = %s", (role_id,))
        role_row = cur.fetchone()
        if role_row and role_row["name"] == "Super Admin":
            from auth.services.user_service import get_super_admin_count, MAX_SUPER_ADMINS

            if get_super_admin_count(cur) >= MAX_SUPER_ADMINS:
                return {
                    "error": "Super Admin seat limit reached. Demote an existing Super Admin first.",
                    "status": 403,
                }

        cur.execute(
            "DELETE FROM auth_enabler.user_roles WHERE user_id = %s",
            (user_id,),
        )
        cur.execute(
            "INSERT INTO auth_enabler.user_roles (user_id, role_id, created_by, updated_by) "
            "VALUES (%s, %s, %s, %s)",
            (user_id, role_id, admin_id, admin_id),
        )
        conn.commit()

        log_activity(
            admin_id, "ASSIGN_ROLE", "Users",
            f"Assigned role {role_id} to user {user_id}", severity="WARNING",
        )

        return {"data": "Role assigned to user successfully"}
    except Exception as e:
        conn.rollback()
        logger.error("Error assigning role to user: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)
