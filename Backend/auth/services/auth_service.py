"""
Auth service — login, sessions, refresh, logout.

Migration SQL:
ALTER TABLE auth_enabler.user_sessions
    ADD COLUMN IF NOT EXISTS device_fingerprint VARCHAR(64);
"""

import datetime
import hashlib
import logging
import secrets

from psycopg2.errors import UniqueViolation

from auth.config import get_config
from auth.constants.applications import (
    DEFAULT_APPLICATION,
    label_for,
    normalize_application,
)
from auth.constants.roles import ROLE_CONFIG, applications_for_role
from auth.db_connection import get_db_connection, release_db_connection
from auth.helpers.audit_helper import log_activity
from auth.helpers.jwt_helper import (
    generate_access_token,
    generate_refresh_token_value,
    revoke_access_token,
)
from auth.helpers.password_helper import (
    hash_password,
    verify_password,
    validate_password_strength,
)
from auth.services.hibp_service import validate_password_not_breached
from auth.services.refresh_token_service import (
    create_refresh_token_row,
    device_hash_from_request,
    hash_token,
    revoke_all_refresh_tokens_for_user,
    revoke_family_for_token,
    rotate_refresh_token,
)
from auth.helpers.email_helper import send_password_reset_email
from auth.helpers.rate_limit_helper import (
    clear_attempts,
    get_failed_attempt_count,
    is_locked_out,
    is_password_reset_rate_limited,
    record_failed_attempt,
    record_password_reset_request,
)
from auth.queries.auth_queries import CREATE_PENDING_USER, CREATE_USER, GET_USER_BY_EMAIL

logger = logging.getLogger(__name__)
config = get_config()

from auth.constants.cookies import REFRESH_COOKIE

MAX_ACTIVE_SESSIONS = 10
PASSWORD_RESET_EXPIRY_MINUTES = 15

# Computed once at import: used to burn the same bcrypt time on unknown-email
# logins as on wrong-password logins, so response latency can't be used to
# enumerate which emails have accounts.
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _device_fingerprint(user_agent: str, accept_language: str, accept_encoding: str) -> str:
    raw = f"{user_agent or ''}|{accept_language or ''}|{accept_encoding or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _login_failed_severity(email: str) -> str:
    count = get_failed_attempt_count(email)
    return "CRITICAL" if count >= 3 else "WARNING"


def _enforce_session_limit(cur, user_id: int) -> None:
    cur.execute(
        """
        SELECT id FROM auth_enabler.user_sessions
        WHERE user_id = %s AND revoked = FALSE
        ORDER BY created_at ASC
        """,
        (user_id,),
    )
    sessions = cur.fetchall()
    excess = len(sessions) - MAX_ACTIVE_SESSIONS + 1
    if excess > 0:
        for row in sessions[:excess]:
            cur.execute(
                """
                UPDATE auth_enabler.user_sessions
                SET revoked = TRUE, updated_at = NOW()
                WHERE id = %s
                """,
                (row["id"],),
            )


def _get_user_roles(cur, user_id: int):
    cur.execute(
        """
        SELECT r.id, r.name
        FROM auth_enabler.user_roles ur
        JOIN auth_enabler.roles r ON ur.role_id = r.id
        WHERE ur.user_id = %s
        """,
        (user_id,),
    )
    return cur.fetchall()


def _resolve_role_claims(primary_role: str):
    if not primary_role or primary_role not in ROLE_CONFIG:
        return None, None, []
    cfg = ROLE_CONFIG[primary_role]
    role_jwt = primary_role.upper().replace(" ", "_")
    return role_jwt, cfg["scope"], cfg["permissions"]


def _assert_application_entitlement(primary_role: str, application: str):
    """Return an error dict if the role may not sign in to this application."""
    if application in applications_for_role(primary_role):
        return None
    return {
        "error": f"Your role is not authorized for {label_for(application)}.",
        "status": 403,
    }


def _user_response(user, roles):
    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "status": user["status"],
        "registration_status": user.get("registration_status"),
        "is_first_login": user.get("is_first_login", False),
        "roles": roles,
        "requested_role": user.get("requested_role"),
        "organization": user.get("organization"),
    }


def _validate_new_password(password: str, user_id: int | None = None) -> dict | None:
    ok, reason = validate_password_strength(password)
    if not ok:
        return {"error": reason, "status": 400}
    return validate_password_not_breached(password, user_id=user_id)


def signup_user(
    full_name: str,
    email: str,
    phone: str = None,
    organization: str = None,
    signup_message: str = None,
    terms_accepted: bool = False,
    ip_address: str = None,
    user_agent: str = None,
):
    if not terms_accepted:
        return {
            "error": "You must accept the Terms & Conditions",
            "error_code": "terms_not_accepted",
            "status": 400,
        }

    accepted_at = datetime.datetime.utcnow()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        placeholder_hash = hash_password(secrets.token_urlsafe(32))
        cur.execute(
            """
            INSERT INTO auth_enabler.users (
                full_name, email, password_hash, status, registration_status,
                phone, organization, signup_message, terms_accepted_at
            )
            VALUES (%s, %s, %s, %s, 'PENDING', %s, %s, %s, %s)
            RETURNING id, full_name, email, status, registration_status, organization, created_at;
            """,
            (
                full_name,
                email,
                placeholder_hash,
                "inactive",
                phone,
                organization,
                signup_message,
                accepted_at,
            ),
        )
        new_user = cur.fetchone()
        log_activity(
            new_user["id"],
            "terms_accepted",
            "Authentication",
            "Terms & Conditions accepted during signup",
            ip_address=ip_address,
            severity="INFO",
            user_agent=user_agent,
            details={
                "terms_version": "1.0",
                "accepted_at": accepted_at.replace(tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "registration_flow": True,
            },
            cur=cur,
        )
        conn.commit()
        return {
            "message": "Thank you — we will reach out to you shortly.",
            "user": {
                "id": new_user["id"],
                "full_name": new_user["full_name"],
                "email": new_user["email"],
                "status": new_user["status"],
                "registration_status": new_user.get("registration_status"),
            },
        }
    except UniqueViolation:
        conn.rollback()
        return {
            "message": "Thank you — we will reach out to you shortly.",
            "user": None,
        }
    except Exception as e:
        conn.rollback()
        logger.error("Signup error: %s", e, exc_info=True)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        release_db_connection(conn)


def login_user(
    email: str,
    password: str,
    device_info: str = None,
    ip_address: str = None,
    accept_language: str = None,
    accept_encoding: str = None,
    remember: bool = False,
    application: str = DEFAULT_APPLICATION,
):
    application = normalize_application(application)
    if application is None:
        return {"error": "Unknown application", "status": 400}
    email = (email or "").strip().lower()
    ip_address = ip_address or ""

    if is_locked_out(email, ip_address):
        return {
            "error": "Too many failed attempts. Try again later.",
            "status": 429,
        }

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(GET_USER_BY_EMAIL, (email,))
        user = cur.fetchone()

        def _fail(description: str, user_id=None):
            record_failed_attempt(email, ip_address)
            log_activity(
                user_id,
                "LOGIN_FAILED",
                "Authentication",
                description,
                ip_address=ip_address,
                severity=_login_failed_severity(email),
            )
            return {"error": "Invalid email or password", "status": 401}

        if not user:
            verify_password(password, _DUMMY_PASSWORD_HASH)  # normalize timing vs. known-email path
            return _fail(f"Failed login for unknown email: {email}")

        reg_status = user.get("registration_status", "PENDING")
        if reg_status == "PENDING":
            return {
                "error": "Your account is awaiting approval. We will email you when it is ready.",
                "status": 403,
            }
        if reg_status == "REJECTED":
            return {"error": "Your registration has been rejected.", "status": 403}
        if reg_status == "SUSPENDED":
            return {"error": "Your account is suspended.", "status": 403}
        if reg_status != "APPROVED":
            return {"error": "Your registration is not approved.", "status": 403}

        if user["status"] != "active":
            record_failed_attempt(email, ip_address)
            return {"error": "User account is disabled", "status": 403}

        if not verify_password(password, user["password_hash"]):
            return _fail(f"Invalid password for {email}", user["id"])

        if user.get("mfa_enabled"):
            from auth.helpers.jwt_helper import generate_mfa_pending_token

            pending = generate_mfa_pending_token(
                user["id"],
                user["email"],
                remember=remember,
                application=application,
            )
            clear_attempts(email)
            return {
                "mfa_required": True,
                "pending_token": pending,
            }

        if user.get("is_first_login"):
            expiry = user.get("temp_password_expiry")
            if expiry:
                now = (
                    datetime.datetime.now(expiry.tzinfo)
                    if getattr(expiry, "tzinfo", None)
                    else datetime.datetime.utcnow()
                )
                if now > expiry:
                    record_failed_attempt(email, ip_address)
                    return {
                        "error": "Temporary password has expired. Please contact an administrator.",
                        "status": 401,
                    }

        roles = _get_user_roles(cur, user["id"])
        if not roles:
            return {
                "error": "No role assigned. Please contact your administrator.",
                "status": 403,
            }

        primary_role = roles[0]["name"]

        entitlement_error = _assert_application_entitlement(primary_role, application)
        if entitlement_error:
            log_activity(
                user["id"],
                "LOGIN_DENIED_APPLICATION",
                "Authentication",
                f"Role '{primary_role}' is not entitled to application '{application}'",
                ip_address=ip_address,
                severity="WARNING",
            )
            return entitlement_error

        role_jwt, scope_type, permissions = _resolve_role_claims(primary_role)

        access_token = generate_access_token(
            user["id"],
            user["email"],
            roles=roles,
            role=role_jwt,
            scope_type=scope_type,
            permissions=permissions,
            application=application,
        )
        refresh_token = generate_refresh_token_value()
        refresh_ref = hash_token(refresh_token)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(
            days=config.JWT_REFRESH_DAYS
        )
        fingerprint = _device_fingerprint(device_info, accept_language, accept_encoding)

        _enforce_session_limit(cur, user["id"])
        cur.execute(
            """
            INSERT INTO auth_enabler.user_sessions
            (user_id, refresh_token, device_info, ip_address, expires_at,
             device_fingerprint, application, created_by, updated_by, revoked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
            """,
            (
                user["id"],
                refresh_ref,
                device_info,
                ip_address,
                expires_at,
                fingerprint,
                application,
                user["id"],
                user["id"],
            ),
        )
        device_hash = device_hash_from_request(device_info, accept_language)
        create_refresh_token_row(
            cur,
            user["id"],
            refresh_token,
            device_hash,
            family_id=None,
            remember=remember,
            application=application,
        )
        conn.commit()
        clear_attempts(email)

        log_activity(
            user["id"],
            "LOGIN_SUCCESS",
            "Authentication",
            f"User {user['email']} successfully logged in.",
            ip_address=ip_address,
            severity="INFO",
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "application": application,
            "user": _user_response(user, roles),
        }
    except Exception as e:
        logger.error("Login error: %s", e, exc_info=True)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        release_db_connection(conn)


def complete_login_after_mfa(
    user_id: int,
    device_info: str = None,
    ip_address: str = None,
    accept_language: str = None,
    accept_encoding: str = None,
    remember: bool = False,
    application: str = DEFAULT_APPLICATION,
):
    """Issue full tokens after successful MFA verification."""
    application = normalize_application(application)
    if application is None:
        return {"error": "Unknown application", "status": 400}
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        user = cur.fetchone()
        if not user:
            return {"error": "User not found", "status": 404}
        roles = _get_user_roles(cur, user_id)
        primary_role = roles[0]["name"] if roles else None
        if not primary_role:
            return {
                "error": "No role assigned. Please contact your administrator.",
                "status": 403,
            }

        entitlement_error = _assert_application_entitlement(primary_role, application)
        if entitlement_error:
            log_activity(
                user_id,
                "LOGIN_DENIED_APPLICATION",
                "Authentication",
                f"Role '{primary_role}' is not entitled to application '{application}'",
                ip_address=ip_address,
                severity="WARNING",
            )
            return entitlement_error

        role_jwt, scope_type, permissions = _resolve_role_claims(primary_role)
        access_token = generate_access_token(
            user_id,
            user["email"],
            roles=roles,
            role=role_jwt,
            scope_type=scope_type,
            permissions=permissions,
            application=application,
        )
        refresh_token = generate_refresh_token_value()
        refresh_ref = hash_token(refresh_token)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(
            days=config.JWT_REFRESH_DAYS
        )
        fingerprint = _device_fingerprint(device_info, accept_language, accept_encoding)
        _enforce_session_limit(cur, user_id)
        cur.execute(
            """
            INSERT INTO auth_enabler.user_sessions
            (user_id, refresh_token, device_info, ip_address, expires_at,
             device_fingerprint, application, created_by, updated_by, revoked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
            """,
            (
                user_id,
                refresh_ref,
                device_info,
                ip_address,
                expires_at,
                fingerprint,
                application,
                user_id,
                user_id,
            ),
        )
        create_refresh_token_row(
            cur,
            user_id,
            refresh_token,
            device_hash_from_request(device_info, accept_language),
            remember=remember,
            application=application,
        )
        conn.commit()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": _user_response(user, roles),
            "remember": remember,
            "application": application,
        }
    except Exception as e:
        conn.rollback()
        logger.error("MFA complete login error: %s", e, exc_info=True)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        release_db_connection(conn)


def refresh_session(
    refresh_token: str,
    ip_address: str = None,
    user_agent: str = None,
    accept_language: str = None,
    accept_encoding: str = None,
):
    if not refresh_token:
        return {"error": "Refresh token required", "status": 401}

    rotation = rotate_refresh_token(
        refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
        accept_language=accept_language,
    )
    if rotation.get("clear_cookie") or rotation.get("reason") == "token_reuse_detected":
        return {
            "error": "session_invalidated",
            "reason": "token_reuse_detected",
            "status": 401,
            "clear_cookie": True,
        }
    if "error" in rotation:
        return rotation
    if not rotation.get("rotated") or not rotation.get("refresh_token"):
        return {"error": "Invalid refresh token", "status": 401}

    user_id = rotation["user_id"]
    # The refresh family carries the application the session was opened for;
    # rotation must never let a session cross the application boundary.
    application = normalize_application(rotation.get("application")) or DEFAULT_APPLICATION
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT email, full_name, status, registration_status FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row or row.get("status") != "active" or row.get("registration_status") != "APPROVED":
            return {"error": "User account is not active", "status": 403}
        roles = _get_user_roles(cur, user_id)
        primary_role = roles[0]["name"] if roles else None

        # Roles can change between refreshes — re-check entitlement and kill the
        # session family if the user lost access to this application. A user
        # with no role at all keeps the pre-existing behaviour (a token with no
        # role/scope/permission claims); permission checks reject it downstream.
        entitlement_error = (
            _assert_application_entitlement(primary_role, application)
            if primary_role
            else None
        )
        if entitlement_error:
            revoke_family_for_token(rotation["refresh_token"])
            log_activity(
                user_id,
                "REFRESH_DENIED_APPLICATION",
                "Authentication",
                f"Role '{primary_role}' lost entitlement to application '{application}'",
                ip_address=ip_address,
                severity="WARNING",
            )
            return {**entitlement_error, "clear_cookie": True}

        role_jwt, scope_type, permissions = _resolve_role_claims(primary_role)
        access_token = generate_access_token(
            user_id,
            row["email"],
            roles=roles,
            role=role_jwt,
            scope_type=scope_type,
            permissions=permissions,
            application=application,
        )
        return {
            "access_token": access_token,
            "refresh_token": rotation["refresh_token"],
            "remember": bool(rotation.get("remember")),
            "user_id": user_id,
            "application": application,
        }
    except Exception as e:
        logger.error("Refresh error: %s", e, exc_info=True)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        release_db_connection(conn)


def logout_user(
    refresh_token: str,
    revoke_all: bool = False,
    access_jti: str = None,
    access_exp: int = None,
):
    if not refresh_token and not revoke_all:
        return {"message": "Logged out"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        user_id = None

        if refresh_token:
            from auth.middleware.csrf import invalidate_csrf_token
            from auth.services.refresh_token_service import (
                hash_token,
                resolve_user_id_from_refresh_cookie,
            )

            uid = resolve_user_id_from_refresh_cookie(refresh_token)
            if uid:
                invalidate_csrf_token(uid)
                user_id = uid
            revoke_family_for_token(refresh_token)
            token_ref = hash_token(refresh_token)
            cur.execute(
                """
                UPDATE auth_enabler.user_sessions
                SET revoked = TRUE, updated_at = NOW()
                WHERE refresh_token = %s AND revoked = FALSE
                RETURNING user_id
                """,
                (token_ref,),
            )
            row = cur.fetchone()
            if row and not user_id:
                user_id = row["user_id"]

        if revoke_all and user_id:
            cur.execute(
                """
                UPDATE auth_enabler.user_sessions
                SET revoked = TRUE, updated_at = NOW()
                WHERE user_id = %s AND revoked = FALSE
                """,
                (user_id,),
            )
            log_activity(
                user_id,
                "LOGOUT",
                "Authentication",
                "User logged out from all devices",
                severity="CRITICAL",
            )
        elif refresh_token and user_id:
            log_activity(
                user_id,
                "LOGOUT",
                "Authentication",
                "User logged out",
                severity="INFO",
            )

        conn.commit()

        if access_jti:
            exp_dt = datetime.datetime.utcnow() + datetime.timedelta(
                minutes=config.JWT_ACCESS_MINUTES
            )
            if access_exp:
                try:
                    exp_dt = datetime.datetime.utcfromtimestamp(access_exp)
                except (TypeError, ValueError, OSError):
                    pass
            revoke_access_token(access_jti, exp_dt)
            if user_id:
                log_activity(
                    user_id,
                    "TOKEN_REVOKED",
                    "Authentication",
                    "Access token revoked on logout",
                    severity="CRITICAL",
                )

        return {"message": "Logged out"}
    except Exception as e:
        logger.error("Logout error: %s", e, exc_info=True)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        release_db_connection(conn)


def change_temp_password(user_id: int, current_temp_pw: str, new_pw: str):
    pw_err = _validate_new_password(new_pw)
    if pw_err:
        return pw_err

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT email, password_hash, is_first_login FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        user = cur.fetchone()

        if not user:
            return {"error": "User not found", "status": 404}
        if not user["is_first_login"]:
            return {
                "error": "Password change only allowed during temporary password stage",
                "status": 400,
            }
        if not verify_password(current_temp_pw, user["password_hash"]):
            log_activity(
                user_id,
                "CHANGE_PASSWORD_FAILED",
                "Authentication",
                "Failed first login password change: invalid temporary password",
                severity="WARNING",
            )
            return {"error": "Invalid temporary password", "status": 400}

        hashed_pw = hash_password(new_pw)
        cur.execute(
            """
            UPDATE auth_enabler.users
            SET password_hash = %s, is_first_login = FALSE, temp_password_expiry = NULL,
                registration_status = 'APPROVED', status = 'active'
            WHERE id = %s
            """,
            (hashed_pw, user_id),
        )
        cur.execute(
            """
            UPDATE auth_enabler.user_sessions
            SET revoked = TRUE, updated_at = NOW()
            WHERE user_id = %s AND revoked = FALSE
            """,
            (user_id,),
        )
        revoke_all_refresh_tokens_for_user(user_id, cur=cur)
        conn.commit()
        log_activity(
            user_id,
            "RESET_PASSWORD",
            "Authentication",
            f"Successfully changed temporary password for {user['email']}",
            severity="WARNING",
        )
        return {"message": "Password changed successfully"}
    except Exception as e:
        conn.rollback()
        logger.error("Error resetting temp password: %s", e, exc_info=True)
        return {"error": "Internal server error", "status": 500}
    finally:
        release_db_connection(conn)


def register_user(
    full_name: str,
    email: str,
    password: str,
    phone: str = None,
    department: str = None,
    employee_id: str = None,
    terms_accepted: bool = False,
    ip_address: str = None,
    user_agent: str = None,
):
    if not terms_accepted:
        return {
            "error": "You must accept the Terms & Conditions",
            "error_code": "terms_not_accepted",
            "status": 400,
        }

    pw_err = _validate_new_password(password)
    if pw_err:
        return pw_err

    accepted_at = datetime.datetime.utcnow()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        hashed_pw = hash_password(password)
        cur.execute(
            """
            INSERT INTO auth_enabler.users (
                full_name, email, password_hash, status, registration_status,
                phone, department, employee_id, terms_accepted_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, full_name, email, status, registration_status,
                      phone, department, employee_id, created_at;
            """,
            (
                full_name,
                email,
                hashed_pw,
                "inactive",
                "PENDING",
                phone,
                department,
                employee_id,
                accepted_at,
            ),
        )
        new_user = cur.fetchone()
        log_activity(
            new_user["id"],
            "terms_accepted",
            "Authentication",
            "Terms & Conditions accepted during registration",
            ip_address=ip_address,
            severity="INFO",
            user_agent=user_agent,
            details={
                "terms_version": "1.0",
                "accepted_at": accepted_at.replace(tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                "registration_flow": True,
            },
            cur=cur,
        )
        conn.commit()
        if new_user.get("created_at") and not isinstance(new_user["created_at"], str):
            new_user["created_at"] = new_user["created_at"].isoformat()
        return {
            "message": "User successfully registered. Waiting for admin approval.",
            "user": new_user,
        }
    except UniqueViolation:
        conn.rollback()
        return {"error": "User with this email already exists", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error("Registration error: %s", e, exc_info=True)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        release_db_connection(conn)


def request_password_reset(email: str, ip_address: str = None):
    """
    Always returns success-shaped result — never reveals whether email exists.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, status FROM auth_enabler.users WHERE email = %s",
            (email,),
        )
        user = cur.fetchone()

        log_activity(
            user["id"] if user else None,
            "FORGOT_PASSWORD_REQUEST",
            "Authentication",
            "Password reset requested",
            ip_address=ip_address,
            severity="INFO",
        )

        if not user or user.get("status") != "active":
            return {"message": "ok"}

        if is_password_reset_rate_limited(email):
            return {"message": "ok"}

        record_password_reset_request(email)

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_reset_token(raw_token)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(
            minutes=PASSWORD_RESET_EXPIRY_MINUTES
        )

        cur.execute(
            """
            INSERT INTO auth_enabler.password_reset_tokens
                (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user["id"], token_hash, expires_at),
        )
        conn.commit()

        send_password_reset_email(user["email"], raw_token)
        return {"message": "ok"}
    except Exception as e:
        conn.rollback()
        logger.error("Forgot password error: %s", e, exc_info=True)
        return {"message": "ok"}
    finally:
        release_db_connection(conn)


def reset_password(token: str, new_password: str, ip_address: str = None):
    if not token or not token.strip():
        return {"error": "Invalid or expired token.", "status": 400}

    pw_err = _validate_new_password(new_password)
    if pw_err:
        return pw_err

    token_hash = _hash_reset_token(token.strip())
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT prt.id, prt.user_id, prt.expires_at, prt.used_at, u.email
            FROM auth_enabler.password_reset_tokens prt
            JOIN auth_enabler.users u ON u.id = prt.user_id
            WHERE prt.token_hash = %s
            ORDER BY prt.created_at DESC
            LIMIT 1
            """,
            (token_hash,),
        )
        row = cur.fetchone()

        if not row:
            return {"error": "Invalid or expired token.", "status": 400}

        if row.get("used_at"):
            return {"error": "Token already used.", "status": 400}

        expires_at = row["expires_at"]
        now = datetime.datetime.utcnow()
        if expires_at and hasattr(expires_at, "tzinfo") and expires_at.tzinfo:
            now = datetime.datetime.now(datetime.timezone.utc)

        if not expires_at or now > expires_at:
            return {"error": "Invalid or expired token.", "status": 400}

        user_id = row["user_id"]
        hashed_pw = hash_password(new_password)

        cur.execute(
            """
            UPDATE auth_enabler.users
            SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (hashed_pw, user_id),
        )
        cur.execute(
            """
            UPDATE auth_enabler.password_reset_tokens
            SET used_at = NOW()
            WHERE id = %s
            """,
            (row["id"],),
        )
        cur.execute(
            """
            UPDATE auth_enabler.user_sessions
            SET revoked = TRUE, updated_at = NOW()
            WHERE user_id = %s AND revoked = FALSE
            """,
            (user_id,),
        )
        revoke_all_refresh_tokens_for_user(user_id, cur=cur)
        conn.commit()

        log_activity(
            user_id,
            "PASSWORD_RESET_SUCCESS",
            "Authentication",
            f"Password reset completed for {row['email']}",
            ip_address=ip_address,
            severity="WARNING",
        )
        return {"message": "Password reset successfully."}
    except Exception as e:
        conn.rollback()
        logger.error("Reset password error: %s", e, exc_info=True)
        return {"error": "Reset failed.", "status": 500}
    finally:
        release_db_connection(conn)
