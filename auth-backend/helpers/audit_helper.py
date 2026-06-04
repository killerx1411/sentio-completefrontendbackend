import logging
from db.connection import get_db_connection

logger = logging.getLogger(__name__)

def log_activity(user_id, action, module, description=None, ip_address=None):
    """
    Inserts a record into the audit_logs table.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = """
            INSERT INTO auth_enabler.audit_logs (user_id, action, module, description, ip_address, created_by, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (user_id, action, module, description, ip_address, user_id, user_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to write audit log: {e}")
    finally:
        if conn:
            conn.close()
