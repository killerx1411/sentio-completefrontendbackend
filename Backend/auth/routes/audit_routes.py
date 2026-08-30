from flask import Blueprint, request, g
import logging

from auth.helpers.response_helper import success_response, error_response
from auth.helpers.audit_helper import get_audit_logs_for_user
from auth.middleware.auth_middleware import require_auth, require_permission
from auth.db_connection import get_db_connection, release_db_connection

audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit-logs")
logger = logging.getLogger(__name__)


def _is_super_admin(user_id: int) -> bool:
    """Check if the given user holds the Super Admin role."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM auth_enabler.user_roles ur
            JOIN auth_enabler.roles r ON ur.role_id = r.id
            WHERE ur.user_id = %s AND r.name = 'Super Admin'
            """,
            (user_id,),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        release_db_connection(conn)


@audit_bp.route("", methods=["GET"])
@require_auth
@require_permission("audit.read")
def get_audit_logs():
    current_user_id = g.user.get("sub")
    requested_user_id = request.args.get("user_id", type=int)

    # SEC-005 FIX: Restrict user_id filter to self unless the caller is
    # Super Admin.  Any other audit.read holder can only view the global
    # log (no user_id filter) or their own trail.
    if requested_user_id:
        if requested_user_id != current_user_id and not _is_super_admin(current_user_id):
            return error_response(
                "Forbidden: You can only view your own audit trail", 403
            )
        logs = get_audit_logs_for_user(requested_user_id, limit=100)
        return success_response(data=logs)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.id, u.email AS user_email, a.action, a.module, a.description,
                   a.severity, a.details, a.user_agent, a.created_at
            FROM auth_enabler.audit_logs a
            LEFT JOIN auth_enabler.users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT 100;
            """
        )
        logs = cur.fetchall()
        for row in logs:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
        return success_response(data=logs)
    except Exception as e:
        logger.error("Error fetching audit logs: %s", e, exc_info=True)
        return error_response("Failed to fetch audit logs", 500)
    finally:
        release_db_connection(conn)
