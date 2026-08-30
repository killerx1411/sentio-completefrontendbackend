import logging
from functools import wraps

from flask import request, g, redirect

from auth.config import get_config
from auth.constants.applications import normalize_application
from auth.helpers.jwt_helper import (
    decode_token,
    TokenExpiredError,
    TokenInvalidError,
    is_token_revoked,
    token_application,
)
from auth.helpers.response_helper import error_response
from auth.helpers.audit_helper import log_activity
from auth.helpers.request_helper import get_client_ip
from auth.db_connection import get_db_connection, release_db_connection
from auth.queries.role_queries import CHECK_USER_PERMISSION

logger = logging.getLogger(__name__)
config = get_config()

FIRST_LOGIN_ALLOWED_PATHS = {
    "/api/auth/change-temp-password",
    "/api/auth/logout",
    "/api/auth/refresh",
}


def _audit_token_failure(description: str, user_id=None):
    log_activity(
        user_id,
        "LOGIN_FAILED_TOKEN",
        "auth",
        description=description,
        ip_address=get_client_ip(),
        severity="WARNING",
    )


def _accepted_applications(application=None):
    """Applications whose tokens the current route accepts."""
    if application is None:
        return set(config.SERVICE_APPLICATIONS)
    if isinstance(application, str):
        return {application}
    return set(application)


def require_authority_auth(f=None, *, redirect_url=None):
    """Authenticate against the applications this deployment is the AUTHORITY for.

    Use on endpoints that belong to the authentication authority itself rather
    than to one product's resource server: identity (``/api/auth/me``),
    introspection for consumer backends, first-login password change and MFA
    enrolment. Those must work for every application the authority mints for.

    ``require_auth`` (the ``SERVICE_APPLICATIONS`` set) stays the right choice
    for business routes. On https://b2bapi.sentiomind.in that is
    ``SERVICE_APPLICATIONS=sentio-b2b``, so a Mobile Admin token authenticates
    for identity and MFA but is still refused by every B2B business route.
    """
    return require_auth(
        f,
        redirect_url=redirect_url,
        application=config.AUTH_AUTHORITY_APPLICATIONS,
    )


def require_auth(f=None, *, redirect_url=None, application=None):
    """Authenticate the bearer token.

    ``application`` narrows the route to token(s) minted for specific
    application(s) (see ``auth/constants/applications.py``). When omitted the
    deployment-wide ``SERVICE_APPLICATIONS`` set applies, so a Sentio Mobile
    Admin token can never be replayed against a B2B-only deployment and vice
    versa.
    """
    accepted = _accepted_applications(application)

    def decorator(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            if request.args.get("token") or request.args.get("access_token"):
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response("Tokens must be sent in Authorization header only", 401)

            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                _audit_token_failure("Missing or invalid Authorization header")
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response("Missing or invalid Authorization header", 401)

            token = auth_header.split(" ", 1)[1].strip()
            if not token:
                _audit_token_failure("Empty bearer token")
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response("Missing or invalid Authorization header", 401)

            try:
                payload = decode_token(token)
            except TokenExpiredError:
                _audit_token_failure("Expired access token")
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response("Signature expired. Please log in again.", 401)
            except TokenInvalidError:
                _audit_token_failure("Invalid access token")
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response("Invalid token. Please log in again.", 401)

            token_type = payload.get("type")
            if token_type == "mfa_pending":
                _audit_token_failure("MFA pending token used as access token")
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response("Invalid token type", 401)
            if token_type != "access":
                _audit_token_failure("Non-access token used as access token")
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response("Invalid token type", 401)

            token_app = token_application(payload)
            if token_app not in accepted:
                _audit_token_failure(
                    f"Token issued for application '{token_app}' rejected",
                    payload.get("sub"),
                )
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response(
                    "Token was not issued for this application", 401
                )

            jti = payload.get("jti")
            if is_token_revoked(jti):
                _audit_token_failure("Revoked access token", payload.get("sub"))
                if redirect_url:
                    return redirect(redirect_url, code=302)
                return error_response("Token has been revoked", 401)

            g.user = payload
            g.jti = jti
            g.application = token_app

            user_id = payload.get("sub")
            conn = None
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT is_first_login, registration_status, status
                    FROM auth_enabler.users WHERE id = %s;
                    """,
                    (user_id,),
                )
                user_row = cur.fetchone()
                if not user_row:
                    _audit_token_failure("User account not found", user_id)
                    if redirect_url:
                        return redirect(redirect_url, code=302)
                    return error_response("User account not found", 401)

                reg_status = user_row.get("registration_status", "PENDING")
                if reg_status != "APPROVED":
                    if redirect_url:
                        return redirect(redirect_url, code=302)
                    return error_response(
                        "Forbidden: Account is not approved", 403
                    )

                if user_row.get("status") != "active":
                    if redirect_url:
                        return redirect(redirect_url, code=302)
                    return error_response("User account is inactive", 403)

                if user_row.get("is_first_login") and request.path not in FIRST_LOGIN_ALLOWED_PATHS:
                    if redirect_url:
                        return redirect(redirect_url, code=302)
                    return error_response("Password change required on first login.", 403)
            except Exception:
                logger.error("Middleware user verification error", exc_info=True)
                return error_response("Internal Server Error", 500)
            finally:
                release_db_connection(conn)

            return fn(*args, **kwargs)

        return decorated

    if f is not None:
        return decorator(f)
    return decorator


def require_application(*applications):
    """Restrict a route to tokens minted for the given application(s).

    Use on top of ``require_auth`` when a single deployment serves more than
    one application and a route belongs to only one of them.
    """
    allowed = {normalize_application(a) for a in applications}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current = getattr(g, "application", None) or token_application(
                getattr(g, "user", None) or {}
            )
            if current not in allowed:
                return error_response(
                    "Forbidden: token is not valid for this application", 403
                )
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_implied_permissions(permission_name):
    hierarchy = {
        "read": ["read", "view", "write", "create", "edit", "delete"],
        "view": ["read", "view", "write", "create", "edit", "delete"],
        "write": ["write", "create", "edit", "delete"],
        "create": ["write", "create", "edit", "delete"],
        "edit": ["write", "create", "edit", "delete"],
        "delete": ["delete"],
        "approve": ["approve"],
        "assign": ["assign"],
        "manage": ["manage"],
    }

    implied = [permission_name]

    if "." in permission_name:
        module, action = permission_name.rsplit(".", 1)
        if action in hierarchy:
            for satisfying_action in hierarchy[action]:
                implied.append(f"{module}.{satisfying_action}")

    return list(set(implied))


def require_permission(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = g.user.get("sub")

            if not user_id:
                return error_response("Unauthorized", 401)

            allowed_perms = get_implied_permissions(permission_name)
            conn = None
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(CHECK_USER_PERMISSION, (user_id, allowed_perms))
                result = cur.fetchone()

                if not result:
                    return error_response(
                        f"Forbidden: You do not have the '{permission_name}' permission.",
                        403,
                    )

                return f(*args, **kwargs)
            except Exception:
                logger.error("Permission check error", exc_info=True)
                return error_response("Internal Server Error", 500)
            finally:
                release_db_connection(conn)

        return decorated_function

    return decorator
