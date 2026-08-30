from flask import Blueprint, request, make_response, g, jsonify, current_app

from auth.config import get_config
from auth.constants.applications import (
    APPLICATIONS,
    DEFAULT_APPLICATION,
    normalize_application,
)
from auth.middleware.auth_middleware import require_authority_auth
from auth.middleware.csrf import csrf_required, generate_csrf_token
from auth.middleware.rate_limiter import limit_ip, limiter
from auth.helpers.cookie_helper import (
    clear_csrf_cookie,
    clear_refresh_cookie,
    set_csrf_cookie,
    set_refresh_cookie,
)
from auth.helpers.response_helper import success_response, error_response, sanitize_user_output
from auth.helpers.validation_helper import sanitize_email, sanitize_string
from auth.helpers.request_helper import get_client_ip
from auth.helpers.jwt_helper import decode_token, TokenExpiredError, TokenInvalidError
from auth.services.auth_service import (
    login_user,
    register_user,
    signup_user,
    refresh_session,
    logout_user,
    request_password_reset,
    reset_password,
)
from auth.constants.cookies import REFRESH_COOKIE

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
config = get_config()

# Clients declare which registered application they are logging into, either in
# the JSON body ("application") or via this header. Sentio Mobile Admin sends
# "sentio-mobile"; the B2B web product sends nothing and gets the default.
APPLICATION_HEADER = "X-Sentio-Application"


def _requested_application():
    """Resolve the application for this request, or None if unregistered."""
    data = request.get_json(silent=True) or {}
    raw = data.get("application") or request.headers.get(APPLICATION_HEADER)
    return normalize_application(raw)


@auth_bp.route("/login", methods=["POST"])
@limit_ip(config.RATELIMIT_LOGIN)
def login():
    data = request.get_json() or {}
    if not data.get("email") or not data.get("password"):
        return error_response("Email and password are required", 400)

    try:
        email = sanitize_email(data.get("email"))
    except ValueError as exc:
        return error_response(str(exc), 400)

    application = _requested_application()
    if application is None:
        return error_response(
            "Unknown application. Expected one of: " + ", ".join(APPLICATIONS), 400
        )

    remember = bool(data.get("remember"))
    result = login_user(
        email,
        data.get("password"),
        device_info=request.headers.get("User-Agent"),
        ip_address=get_client_ip(),
        accept_language=request.headers.get("Accept-Language"),
        accept_encoding=request.headers.get("Accept-Encoding"),
        remember=remember,
        application=application,
    )

    if "error" in result:
        return error_response(result["error"], result.get("status", 400))

    if result.get("mfa_required"):
        return success_response(
            data={
                "mfa_required": True,
                "pending_token": result["pending_token"],
                "application": application,
            },
            message="MFA verification required",
        )

    # Client must store csrf_token in JS memory (not localStorage) and send as X-CSRF-Token
    # on POST /api/auth/refresh and /api/auth/logout.
    csrf_token = generate_csrf_token(result["user"]["id"])
    resp = make_response(
        success_response(
            data={
                "access_token": result["access_token"],
                "user": sanitize_user_output(result["user"]),
                "csrf_token": csrf_token,
                "application": result.get("application", application),
            },
            message="Successfully logged in",
        )
    )
    set_csrf_cookie(resp, csrf_token)
    return set_refresh_cookie(resp, result["refresh_token"], remember)


@auth_bp.route("/signup", methods=["POST"])
@limit_ip(config.RATELIMIT_SIGNUP)
def signup():
    data = request.get_json() or {}
    if not data.get("email") or not data.get("full_name"):
        return error_response("Full name and email are required", 400)

    if data.get("terms_accepted") is not True:
        return jsonify(
            {
                "error": "terms_not_accepted",
                "message": "You must accept the Terms & Conditions",
            }
        ), 400

    try:
        email = sanitize_email(data.get("email"))
        full_name = sanitize_string(data.get("full_name"), 120, "full_name")
        organization = (
            sanitize_string(data["organization"], 200, "organization")
            if data.get("organization")
            else None
        )
    except ValueError as exc:
        return error_response(str(exc), 400)

    result = signup_user(
        full_name=full_name,
        email=email,
        phone=data.get("phone"),
        organization=organization,
        signup_message=data.get("message"),
        terms_accepted=True,
        ip_address=get_client_ip(),
        user_agent=request.headers.get("User-Agent"),
    )

    if "error" in result:
        return error_response(result["error"], result.get("status", 400))

    user = result.get("user")
    if user:
        user = sanitize_user_output(user)

    return success_response(
        data=user,
        message=result.get("message"),
        status_code=201,
    )


@auth_bp.route("/register", methods=["POST"])
@limit_ip(config.RATELIMIT_REGISTER)
def register():
    if not current_app.config.get("ENABLE_OPEN_REGISTRATION", False):
        return jsonify({"error": "Registration is disabled."}), 403

    data = request.get_json() or {}
    if not data.get("email") or not data.get("password") or not data.get("full_name"):
        return error_response("Full name, email, and password are required", 400)

    if data.get("terms_accepted") is not True:
        return jsonify(
            {
                "error": "terms_not_accepted",
                "message": "You must accept the Terms & Conditions",
            }
        ), 400

    try:
        email = sanitize_email(data.get("email"))
        full_name = sanitize_string(data.get("full_name"), 120, "full_name")
        department = (
            sanitize_string(data["department"], 100, "department")
            if data.get("department")
            else None
        )
        employee_id = (
            sanitize_string(data["employee_id"], 50, "employee_id")
            if data.get("employee_id")
            else None
        )
    except ValueError as exc:
        return error_response(str(exc), 400)

    result = register_user(
        full_name=full_name,
        email=email,
        password=data.get("password"),
        phone=data.get("phone"),
        department=department,
        employee_id=employee_id,
        terms_accepted=True,
        ip_address=get_client_ip(),
        user_agent=request.headers.get("User-Agent"),
    )

    if "error" in result:
        return error_response(result["error"], result.get("status", 400))

    user = result.get("user")
    if user:
        user = sanitize_user_output(user)

    return success_response(data=user, message=result.get("message"), status_code=201)


@auth_bp.route("/refresh", methods=["POST"])
@csrf_required
@limit_ip(config.RATELIMIT_REFRESH)
def refresh():
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        return error_response("Refresh token required in cookie", 401)
    result = refresh_session(
        refresh_token,
        ip_address=get_client_ip(),
        user_agent=request.headers.get("User-Agent"),
        accept_language=request.headers.get("Accept-Language"),
        accept_encoding=request.headers.get("Accept-Encoding"),
    )

    if "error" in result:
        if result.get("reason") == "token_reuse_detected":
            resp = make_response(
                jsonify(
                    {
                        "error": "session_invalidated",
                        "reason": "token_reuse_detected",
                    }
                ),
                401,
            )
            return clear_refresh_cookie(resp)
        resp = make_response(error_response(result["error"], result.get("status", 401)))
        return clear_refresh_cookie(resp)

    user_id = result.get("user_id")
    if not user_id:
        return error_response("Unable to rotate session", 500)
    csrf_token = generate_csrf_token(user_id)
    resp = make_response(
        success_response(
            data={
                "access_token": result["access_token"],
                "csrf_token": csrf_token,
                "application": result.get("application", DEFAULT_APPLICATION),
            }
        )
    )
    set_csrf_cookie(resp, csrf_token)
    remember = bool(result.get("remember"))
    return set_refresh_cookie(resp, result["refresh_token"], remember)


@auth_bp.route("/logout", methods=["POST"])
@csrf_required
@limit_ip(config.RATELIMIT_LOGOUT)
def logout():
    data = request.get_json() or {}
    refresh_token = request.cookies.get(REFRESH_COOKIE) or data.get("refresh_token")
    revoke_all = bool(data.get("revoke_all"))

    access_jti = None
    access_exp = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
            access_jti = payload.get("jti")
            access_exp = payload.get("exp")
        except (TokenExpiredError, TokenInvalidError):
            pass
    elif hasattr(g, "jti"):
        access_jti = getattr(g, "jti", None)
        if hasattr(g, "user") and g.user:
            access_exp = g.user.get("exp")

    result = logout_user(
        refresh_token,
        revoke_all=revoke_all,
        access_jti=access_jti,
        access_exp=access_exp,
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 500))

    resp = make_response(success_response(message="Logged out"))
    clear_csrf_cookie(resp)
    return clear_refresh_cookie(resp)


@auth_bp.route("/change-temp-password", methods=["POST"])
@require_authority_auth
def change_temp_password_route():
    data = request.get_json() or {}
    if not data.get("temp_password") or not data.get("new_password"):
        return error_response("Temporary password and new password are required", 400)

    from auth.services.auth_service import change_temp_password

    user_id = g.user.get("sub")
    if not user_id:
        return error_response("Unauthorized", 401)

    result = change_temp_password(
        user_id, data.get("temp_password"), data.get("new_password")
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(message=result.get("message"))


@auth_bp.route("/forgot-password", methods=["POST"])
@limit_ip(config.RATELIMIT_PASSWORD_RESET)
@limiter.limit(
    config.RATELIMIT_FORGOT_PASSWORD_GLOBAL,
    key_func=lambda: "global:forgot-password",
)
def forgot_password():
    data = request.get_json() or {}
    if not data.get("email"):
        return success_response(message="ok")

    try:
        email = sanitize_email(data.get("email"))
    except ValueError:
        return success_response(message="ok")

    request_password_reset(email, ip_address=get_client_ip())
    return success_response(message="ok")


@auth_bp.route("/reset-password", methods=["POST"])
@limit_ip(config.RATELIMIT_PASSWORD_RESET)
def reset_password_route():
    data = request.get_json() or {}
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        return error_response("Invalid or expired token.", 400)

    result = reset_password(
        token,
        new_password,
        ip_address=get_client_ip(),
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(message=result.get("message"))


@auth_bp.route("/me", methods=["GET"])
@require_authority_auth
def me():
    from auth.db_connection import get_db_connection, release_db_connection
    from auth.helpers.audit_helper import log_activity

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
        log_activity(
            user_id,
            "VIEW_PROFILE",
            "Authentication",
            "User viewed own profile",
            ip_address=get_client_ip(),
            severity="INFO",
        )
        return success_response(data=sanitize_user_output(dict(user)))
    finally:
        release_db_connection(conn)


@auth_bp.route("/introspect", methods=["GET"])
@require_authority_auth
def introspect():
    """Token introspection for consumer backends (e.g. Sentio Mobile Admin).

    A resource server that does not hold the JWT signing key calls this with the
    end user's bearer token and gets the authoritative claims back. It performs
    no authentication of its own — this authority remains the only one.
    """
    payload = g.user
    return success_response(
        data={
            "active": True,
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "application": getattr(g, "application", None),
            "roles": payload.get("roles", []),
            "role": payload.get("role"),
            "scope_type": payload.get("scope_type"),
            "permissions": payload.get("permissions", []),
            "exp": payload.get("exp"),
            "jti": payload.get("jti"),
        }
    )
