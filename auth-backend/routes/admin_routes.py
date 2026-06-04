from flask import Blueprint, request, g
import services.user_service as user_service
from helpers.response_helper import success_response, error_response
from middleware.auth_middleware import require_auth, require_permission
from helpers.email_helper import STAKEHOLDER_ROLES, normalize_role_name

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/pending-users", methods=["GET"])
@require_auth
@require_permission("users.approve")
def list_pending():
    result = user_service.get_pending_users()
    if "error" in result:
        return error_response(result["error"], result.get("status", 500))
    return success_response(data=result["data"])


@admin_bp.route("/approve-user/<int:user_id>", methods=["POST"])
@require_auth
@require_permission("users.approve")
def approve(user_id):
    data = request.get_json() or {}
    role_id = data.get("role_id")
    role_name = data.get("role")

    if role_id:
        result = user_service.approve_user(user_id, role_id, g.user.get("sub"))
    elif role_name:
        role_name = normalize_role_name(role_name)
        if role_name not in STAKEHOLDER_ROLES and role_name not in (
            "Super Admin", "Secondary Admin", "Normal Admin"
        ):
            return error_response(
                f"Invalid role. Choose one of: {', '.join(STAKEHOLDER_ROLES)}", 400
            )
        result = user_service.approve_user_by_role_name(user_id, role_name, g.user.get("sub"))
    else:
        return error_response("role_id or role is required", 400)

    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(data=result.get("data"), message=result.get("message"))


# Backward-compatible path used by older clients
@admin_bp.route("/users/<int:user_id>/approve", methods=["POST"])
@require_auth
@require_permission("users.approve")
def approve_legacy(user_id):
    return approve(user_id)


@admin_bp.route("/reject-user/<int:user_id>", methods=["POST"])
@require_auth
@require_permission("users.approve")
def reject(user_id):
    data = request.get_json() or {}
    result = user_service.reject_user(user_id, g.user.get("sub"), reason=data.get("reason"))
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(data=result.get("data"), message=result.get("message"))


@admin_bp.route("/users/<int:user_id>/reject", methods=["POST"])
@require_auth
@require_permission("users.approve")
def reject_legacy(user_id):
    return reject(user_id)
