from flask import Blueprint, request, g

import auth.services.user_service as user_service
from auth.constants.roles import ALL_ROLES
from auth.helpers.email_helper import STAKEHOLDER_ROLES, normalize_role_name
from auth.helpers.response_helper import success_response, error_response, sanitize_user_output
from auth.middleware.auth_middleware import require_auth, require_permission
from auth.middleware.rate_limiter import limit_authenticated
from auth.config import get_config

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
config = get_config()
_admin_limit = limit_authenticated(config.RATELIMIT_ADMIN)


def _sanitize_pending(users):
    return [sanitize_user_output(dict(u)) for u in users]


@admin_bp.route("/pending-users", methods=["GET"])
@_admin_limit
@require_auth
@require_permission("users.approve")
def list_pending():
    result = user_service.get_pending_users()
    if "error" in result:
        return error_response(result["error"], result.get("status", 500))
    return success_response(data=_sanitize_pending(result["data"]))


@admin_bp.route("/approve-user/<int:user_id>", methods=["POST"])
@_admin_limit
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
        if role_name not in ALL_ROLES:
            return error_response(
                f"Invalid role. Choose one of: {', '.join(ALL_ROLES)}", 400
            )
        result = user_service.approve_user_by_role_name(user_id, role_name, g.user.get("sub"))
    else:
        return error_response("role_id or role is required", 400)

    if "error" in result:
        return error_response(result["error"], result.get("status", 400))

    payload = result.get("data")
    if payload and payload.get("user"):
        payload = {**payload, "user": sanitize_user_output(payload["user"])}

    return success_response(data=payload, message=result.get("message"))


@admin_bp.route("/users/<int:user_id>/approve", methods=["POST"])
@_admin_limit
@require_auth
@require_permission("users.approve")
def approve_legacy(user_id):
    return approve(user_id)


@admin_bp.route("/reject-user/<int:user_id>", methods=["POST"])
@_admin_limit
@require_auth
@require_permission("users.approve")
def reject(user_id):
    data = request.get_json() or {}
    result = user_service.reject_user(user_id, g.user.get("sub"), reason=data.get("reason"))
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    data_out = sanitize_user_output(result.get("data")) if result.get("data") else None
    return success_response(data=data_out, message=result.get("message"))


@admin_bp.route("/users/<int:user_id>/reject", methods=["POST"])
@_admin_limit
@require_auth
@require_permission("users.approve")
def reject_legacy(user_id):
    return reject(user_id)
