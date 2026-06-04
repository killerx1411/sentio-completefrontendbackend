from flask import Blueprint, request, g
import services.role_service as role_service
from helpers.response_helper import success_response, error_response
from middleware.auth_middleware import require_auth, require_permission

role_bp = Blueprint("roles", __name__, url_prefix="/api")


@role_bp.route("/roles", methods=["POST"])
@require_auth
@require_permission("permissions.manage")
def create_role():
    data = request.get_json()
    if not data or not data.get("name"):
        return error_response("Role name is required", 400)

    admin_id = g.user.get("sub") if hasattr(g, "user") and g.user else None
    result = role_service.create_role(data.get("name"), data.get("description", ""), admin_id=admin_id)
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(data=result["data"], message="Role created", status_code=201)


@role_bp.route("/roles", methods=["GET"])
@require_auth
@require_permission("users.read")
def get_roles():
    result = role_service.get_all_roles()
    if "error" in result:
        return error_response(result["error"], result.get("status", 500))
    return success_response(data=result["data"])


@role_bp.route("/permissions", methods=["POST"])
@require_auth
@require_permission("permissions.manage")
def create_permission():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("module") or not data.get("action"):
        return error_response("Name, module, and action are required", 400)

    admin_id = g.user.get("sub") if hasattr(g, "user") and g.user else None
    result = role_service.create_permission(
        data.get("name"),
        data.get("module"),
        data.get("action"),
        data.get("description", ""),
        admin_id=admin_id,
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(data=result["data"], message="Permission created", status_code=201)


@role_bp.route("/roles/<int:role_id>/permissions/<int:permission_id>", methods=["POST"])
@require_auth
@require_permission("permissions.manage")
def assign_permission(role_id, permission_id):
    admin_id = g.user.get("sub") if hasattr(g, "user") and g.user else None
    result = role_service.assign_permission_to_role(role_id, permission_id, admin_id=admin_id)
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(message=result["data"])


@role_bp.route("/users/<int:user_id>/roles/<int:role_id>", methods=["POST"])
@require_auth
@require_permission("roles.assign")
def assign_role_to_user(user_id, role_id):
    current_user_id = g.user.get("sub")

    from routes.user_routes import get_role_name, is_user_super_admin

    role_name = get_role_name(role_id)
    if role_name in ("Super Admin", "Secondary Admin", "Normal Admin") and not is_user_super_admin(current_user_id):
        return error_response(
            "Forbidden: Only Super Admin can assign admin-tier roles", 403
        )

    if is_user_super_admin(user_id) and not is_user_super_admin(current_user_id):
        return error_response("Forbidden: You cannot modify a Super Admin user", 403)

    result = role_service.assign_role_to_user(user_id, role_id, admin_id=current_user_id)
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(message=result["data"])
