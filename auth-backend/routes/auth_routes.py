from flask import Blueprint, request, make_response
from services.auth_service import (
    login_user,
    register_user,
    signup_user,
    refresh_session,
    logout_user,
    REFRESH_COOKIE,
)
from helpers.response_helper import success_response, error_response
from middleware.auth_middleware import require_auth
from config import get_config

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
config = get_config()


def _set_refresh_cookie(response, refresh_token: str, remember: bool):
    max_age = config.JWT_REFRESH_DAYS * 24 * 60 * 60 if remember else None
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        secure=config.FLASK_ENV == "production",
        samesite="Lax",
        max_age=max_age,
        path="/api/auth",
    )
    return response


def _clear_refresh_cookie(response):
    response.set_cookie(
        REFRESH_COOKIE,
        "",
        httponly=True,
        secure=config.FLASK_ENV == "production",
        samesite="Lax",
        max_age=0,
        path="/api/auth",
    )
    return response


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    if not data.get("email") or not data.get("password"):
        return error_response("Email and password are required", 400)

    remember = bool(data.get("remember"))
    result = login_user(
        data.get("email"),
        data.get("password"),
        device_info=request.headers.get("User-Agent"),
        ip_address=request.remote_addr,
    )

    if "error" in result:
        return error_response(result["error"], result.get("status", 400))

    resp = make_response(
        success_response(
            data={
                "access_token": result["access_token"],
                "user": result["user"],
            },
            message="Successfully logged in",
        )
    )
    return _set_refresh_cookie(resp, result["refresh_token"], remember)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    if not data.get("email") or not data.get("full_name"):
        return error_response("Full name and email are required", 400)

    result = signup_user(
        full_name=data.get("full_name"),
        email=data.get("email").strip().lower(),
        phone=data.get("phone"),
        organization=data.get("organization"),
        signup_message=data.get("message"),
    )

    if "error" in result:
        return error_response(result["error"], result.get("status", 400))

    return success_response(
        data=result.get("user"),
        message=result.get("message"),
        status_code=201,
    )


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    if not data.get("email") or not data.get("password") or not data.get("full_name"):
        return error_response("Full name, email, and password are required", 400)

    result = register_user(
        full_name=data.get("full_name"),
        email=data.get("email"),
        password=data.get("password"),
        phone=data.get("phone"),
        department=data.get("department"),
        employee_id=data.get("employee_id"),
    )

    if "error" in result:
        return error_response(result["error"], result.get("status", 400))

    return success_response(data=result.get("user"), message=result.get("message"), status_code=201)


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    refresh_token = request.cookies.get(REFRESH_COOKIE) or (request.get_json() or {}).get(
        "refresh_token"
    )
    result = refresh_session(refresh_token)

    if "error" in result:
        resp = make_response(error_response(result["error"], result.get("status", 401)))
        return _clear_refresh_cookie(resp)

    resp = make_response(
        success_response(data={"access_token": result["access_token"]})
    )
    return _set_refresh_cookie(resp, result["refresh_token"], True)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    refresh_token = request.cookies.get(REFRESH_COOKIE) or (request.get_json() or {}).get(
        "refresh_token"
    )
    logout_user(refresh_token)
    resp = make_response(success_response(message="Logged out"))
    return _clear_refresh_cookie(resp)


@auth_bp.route("/change-temp-password", methods=["POST"])
@require_auth
def change_temp_password_route():
    data = request.get_json() or {}
    if not data.get("temp_password") or not data.get("new_password"):
        return error_response("Temporary password and new password are required", 400)

    from flask import g
    from services.auth_service import change_temp_password

    user_id = g.user.get("sub")
    if not user_id:
        return error_response("Unauthorized", 401)

    result = change_temp_password(
        user_id, data.get("temp_password"), data.get("new_password")
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(message=result.get("message"))


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    from flask import g
    from db.connection import get_db_connection

    user_id = g.user.get("sub")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT u.id, u.full_name, u.email, u.status, u.registration_status, u.is_first_login,
                   COALESCE(json_agg(json_build_object('id', r.id, 'name', r.name))
                     FILTER (WHERE r.id IS NOT NULL), '[]') AS roles
            FROM auth_enabler.users u
            LEFT JOIN auth_enabler.user_roles ur ON u.id = ur.user_id
            LEFT JOIN auth_enabler.roles r ON ur.role_id = r.id
            WHERE u.id = %s
            GROUP BY u.id
            """,
            (user_id,),
        )
        user = cur.fetchone()
        if not user:
            return error_response("User not found", 404)
        return success_response(data=user)
    finally:
        if conn:
            conn.close()
