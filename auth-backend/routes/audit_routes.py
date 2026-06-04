from flask import Blueprint
from db.connection import get_db_connection
from helpers.response_helper import success_response, error_response
from middleware.auth_middleware import require_auth, require_permission
import logging

audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit-logs')
logger = logging.getLogger(__name__)

@audit_bp.route('', methods=['GET'])
@require_auth
@require_permission('audit.read')
def get_audit_logs():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = """
            SELECT a.id, u.email as user_email, a.action, a.module, a.description, a.created_at
            FROM auth_enabler.audit_logs a
            LEFT JOIN auth_enabler.users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT 100;
        """
        cur.execute(query)
        logs = cur.fetchall()
        return success_response(data=logs)
    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        return error_response("Failed to fetch audit logs", 500)
    finally:
        if conn:
            conn.close()
