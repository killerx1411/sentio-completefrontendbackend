"""MFA setup, confirm, verify, and disable endpoints."""

from __future__ import annotations

from flask import Blueprint, g, make_response, request

from auth.middleware.auth_middleware import require_authority_auth
from auth.middleware.rate_limiter import limit_ip
from auth.config import get_config
from auth.constants.applications import DEFAULT_APPLICATION, normalize_application
from auth.helpers.jwt_helper import (
    TokenExpiredError,
    TokenInvalidError,
    decode_token,
    token_application,
)
from auth.helpers.response_helper import error_response, success_response
from auth.middleware.csrf import generate_csrf_token
from auth.helpers.cookie_helper import set_csrf_cookie, set_refresh_cookie
from auth.services import auth_service
from auth.services.mfa_service import (
    confirm_mfa,
    disable_mfa,
    generate_secret,
    get_provisioning_uri,
    qr_code_base64,
    store_pending_mfa_secret,
    verify_recovery_code,
    verify_totp,
)
from auth.helpers.audit_helper import log_activity
from auth.helpers.request_helper import get_client_ip

mfa_bp = Blueprint("mfa", __name__, url_prefix="/api/auth/mfa")
config = get_config()


@mfa_bp.route("/setup", methods=["POST"])
@require_authority_auth
def mfa_setup():
    if g.user.get("type") == "mfa_pending":
        return error_response("Invalid token type", 401)
    user_id = int(g.user["sub"])
    email = g.user.get("email", "")
    secret = generate_secret()
    store_pending_mfa_secret(user_id, secret)
    uri = get_provisioning_uri(email, secret)
    return success_response(
        data={
            "qr_code_base64": qr_code_base64(uri),
        }
    )


@mfa_bp.route("/confirm", methods=["POST"])
@require_authority_auth
def mfa_confirm():
    data = request.get_json() or {}
    code = data.get("totp_code", "")
    result = confirm_mfa(int(g.user["sub"]), code)
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(data={"recovery_codes": result["recovery_codes"]})


@mfa_bp.route("/disable", methods=["POST"])
@require_authority_auth
def mfa_disable():
    data = request.get_json() or {}
    result = disable_mfa(
        int(g.user["sub"]),
        data.get("password", ""),
        data.get("totp_code", ""),
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 400))
    return success_response(message=result.get("message"))


@mfa_bp.route("/verify", methods=["POST"])
@limit_ip(config.RATELIMIT_MFA_VERIFY)
def mfa_verify():
    data = request.get_json() or {}
    pending = data.get("pending_token", "")
    totp_code = data.get("totp_code")
    recovery_code = data.get("recovery_code")

    if not pending:
        return error_response("pending_token required", 400)

    try:
        payload = decode_token(pending)
    except TokenExpiredError:
        log_activity(None, "mfa_verify_failed", "Security", "Expired pending token", severity="WARNING")
        return error_response("Invalid or expired pending token", 401)
    except TokenInvalidError:
        log_activity(None, "mfa_verify_failed", "Security", "Invalid pending token", severity="WARNING")
        return error_response("Invalid or expired pending token", 401)

    if payload.get("type") != "mfa_pending":
        return error_response("Invalid token type", 401)

    user_id = int(payload["sub"])
    conn = None
    from auth.db_connection import get_db_connection, release_db_connection

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT email, mfa_secret, mfa_enabled FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        user = cur.fetchone()
    finally:
        release_db_connection(conn)

    if not user or not user.get("mfa_enabled"):
        return error_response("MFA not required", 400)

    verified = False
    if totp_code and user.get("mfa_secret"):
        verified = verify_totp(user["mfa_secret"], totp_code)
    elif recovery_code:
        verified = verify_recovery_code(user_id, recovery_code)

    if not verified:
        log_activity(user_id, "mfa_verify_failed", "Security", "Invalid MFA code", severity="WARNING")
        return error_response("Invalid MFA code", 401)

    log_activity(user_id, "mfa_verify_success", "Security", "MFA verified", severity="INFO")
    remember = bool(payload.get("remember"))
    # The pending token carries the application the user started logging into,
    # so MFA completion cannot cross the application boundary.
    application = (
        normalize_application(token_application(payload)) or DEFAULT_APPLICATION
    )
    result = auth_service.complete_login_after_mfa(
        user_id,
        device_info=request.headers.get("User-Agent"),
        ip_address=get_client_ip(),
        accept_language=request.headers.get("Accept-Language"),
        accept_encoding=request.headers.get("Accept-Encoding"),
        remember=remember,
        application=application,
    )
    if "error" in result:
        return error_response(result["error"], result.get("status", 500))

    csrf = generate_csrf_token(user_id)
    resp = make_response(
        success_response(
            data={
                "access_token": result["access_token"],
                "user": result["user"],
                "csrf_token": csrf,
                "application": result.get("application", application),
            },
            message="Successfully logged in",
        )
    )
    set_csrf_cookie(resp, csrf)
    return set_refresh_cookie(resp, result["refresh_token"], remember)
