import logging
from db.connection import get_db_connection
import queries.role_queries as queries
from helpers.audit_helper import log_activity
from psycopg2.errors import UniqueViolation
from flask import g

logger = logging.getLogger(__name__)

def create_role(name: str, description: str, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.CREATE_ROLE, (name, description, admin_id, admin_id))
        role = cur.fetchone()
        conn.commit()
        
        log_activity(admin_id, 'CREATE_ROLE', 'Roles', f"Created new role: {name}")
        
        return {"data": role}
    except UniqueViolation:
        conn.rollback()
        return {"error": "Role name already exists", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating role: {e}")
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()

def get_all_roles():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.GET_ALL_ROLES)
        roles = cur.fetchall()
        return {"data": roles}
    except Exception as e:
        logger.error(f"Error fetching roles: {e}")
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()

def create_permission(name: str, module: str, action: str, description: str, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.CREATE_PERMISSION, (name, module, action, description, admin_id, admin_id))
        permission = cur.fetchone()
        conn.commit()
        
        log_activity(admin_id, 'CREATE_PERMISSION', 'Roles', f"Created new permission: {name}")
        
        return {"data": permission}
    except UniqueViolation:
        conn.rollback()
        return {"error": "Permission name already exists", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating permission: {e}")
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()

def assign_permission_to_role(role_id: int, permission_id: int, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.ASSIGN_PERMISSION_TO_ROLE, (role_id, permission_id, admin_id, admin_id))
        conn.commit()
        
        log_activity(admin_id, 'ASSIGN_PERMISSION', 'Roles', f"Assigned permission {permission_id} to role {role_id}")
        
        return {"data": "Permission assigned to role successfully"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Error assigning permission: {e}")
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()

def assign_role_to_user(user_id: int, role_id: int, admin_id: int = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(queries.ASSIGN_ROLE_TO_USER, (user_id, role_id, admin_id, admin_id))
        conn.commit()
        
        log_activity(admin_id, 'ASSIGN_ROLE', 'Users', f"Assigned role {role_id} to user {user_id}")
        
        return {"data": "Role assigned to user successfully"}
    except Exception as e:
        conn.rollback()
        logger.error(f"Error assigning role to user: {e}")
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()
