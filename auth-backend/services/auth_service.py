import datetime
import logging
import secrets

from db.connection import get_db_connection
from queries.auth_queries import GET_USER_BY_EMAIL, CREATE_USER, CREATE_PENDING_USER
from helpers.password_helper import verify_password, hash_password
from helpers.jwt_helper import (
    generate_access_token,
    generate_refresh_token_value,
)
from helpers.audit_helper import log_activity
from constants.roles import ROLE_CONFIG
from psycopg2.errors import UniqueViolation
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()

REFRESH_COOKIE = "sentio_refresh"


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


def signup_user(
    full_name: str,
    email: str,
    phone: str = None,
    organization: str = None,
    signup_message: str = None,
):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        placeholder_hash = hash_password(secrets.token_urlsafe(32))
        cur.execute(
            CREATE_PENDING_USER,
            (
                full_name,
                email,
                placeholder_hash,
                "inactive",
                phone,
                organization,
                signup_message,
            ),
        )
        new_user = cur.fetchone()
        conn.commit()
        log_activity(new_user["id"], "SIGNUP", "Authentication", f"Pending signup: {email}")
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
        return {"error": "An account with this email already exists", "status": 409}
    except Exception as e:
        conn.rollback()
        logger.error("Signup error: %s", e)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        if conn:
            conn.close()


def login_user(email: str, password: str, device_info: str = None, ip_address: str = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(GET_USER_BY_EMAIL, (email,))
        user = cur.fetchone()

        if not user:
            log_activity(None, "LOGIN_FAILED", "Authentication", f"Failed login for unknown email: {email}")
            return {"error": "Invalid email or password", "status": 401}

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
            return {"error": "User account is disabled", "status": 403}

        if not verify_password(password, user["password_hash"]):
            log_activity(user["id"], "LOGIN_FAILED", "Authentication", f"Invalid password for {email}")
            return {"error": "Invalid email or password", "status": 401}

        if user.get("is_first_login"):
            expiry = user.get("temp_password_expiry")
            if expiry:
                now = (
                    datetime.datetime.now(expiry.tzinfo)
                    if getattr(expiry, "tzinfo", None)
                    else datetime.datetime.utcnow()
                )
                if now > expiry:
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
        role_jwt, scope_type, permissions = _resolve_role_claims(primary_role)

        access_token = generate_access_token(
            user["id"],
            user["email"],
            roles=roles,
            role=role_jwt,
            scope_type=scope_type,
            permissions=permissions,
        )
        refresh_token = generate_refresh_token_value()
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=config.JWT_REFRESH_DAYS)

        cur.execute(
            """
            INSERT INTO auth_enabler.user_sessions
            (user_id, refresh_token, device_info, ip_address, expires_at, created_by, updated_by, revoked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
            """,
            (
                user["id"],
                refresh_token,
                device_info,
                ip_address,
                expires_at,
                user["id"],
                user["id"],
            ),
        )
        conn.commit()

        log_activity(user["id"], "LOGIN", "Authentication", f"User {user['email']} successfully logged in.")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": _user_response(user, roles),
        }
    except Exception as e:
        logger.error("Login error: %s", e)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        if conn:
            conn.close()


def refresh_session(refresh_token: str):
    if not refresh_token:
        return {"error": "Refresh token required", "status": 401}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.id AS session_id, s.user_id, s.expires_at, s.revoked,
                   u.email, u.full_name, u.status, u.registration_status, u.is_first_login
            FROM auth_enabler.user_sessions s
            JOIN auth_enabler.users u ON u.id = s.user_id
            WHERE s.refresh_token = %s
            """,
            (refresh_token,),
        )
        row = cur.fetchone()

        if not row or row.get("revoked"):
            return {"error": "Invalid refresh token", "status": 401}

        expires = row["expires_at"]
        now = (
            datetime.datetime.now(expires.tzinfo)
            if getattr(expires, "tzinfo", None)
            else datetime.datetime.utcnow()
        )
        if expires < now:
            return {"error": "Refresh token expired", "status": 401}

        if row["status"] != "active" or row.get("registration_status") != "APPROVED":
            return {"error": "User account is not active", "status": 403}

        roles = _get_user_roles(cur, row["user_id"])
        primary_role = roles[0]["name"] if roles else None
        role_jwt, scope_type, permissions = _resolve_role_claims(primary_role)

        access_token = generate_access_token(
            row["user_id"],
            row["email"],
            roles=roles,
            role=role_jwt,
            scope_type=scope_type,
            permissions=permissions,
        )

        new_refresh = generate_refresh_token_value()
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=config.JWT_REFRESH_DAYS)

        cur.execute(
            "UPDATE auth_enabler.user_sessions SET revoked = TRUE, updated_at = NOW() WHERE id = %s",
            (row["session_id"],),
        )
        cur.execute(
            """
            INSERT INTO auth_enabler.user_sessions
            (user_id, refresh_token, expires_at, created_by, updated_by, revoked)
            VALUES (%s, %s, %s, %s, %s, FALSE)
            """,
            (row["user_id"], new_refresh, expires_at, row["user_id"], row["user_id"]),
        )
        conn.commit()

        return {"access_token": access_token, "refresh_token": new_refresh}
    except Exception as e:
        logger.error("Refresh error: %s", e)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        if conn:
            conn.close()


def logout_user(refresh_token: str):
    if not refresh_token:
        return {"message": "Logged out"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE auth_enabler.user_sessions
            SET revoked = TRUE, updated_at = NOW()
            WHERE refresh_token = %s AND revoked = FALSE
            RETURNING user_id
            """,
            (refresh_token,),
        )
        row = cur.fetchone()
        conn.commit()
        if row:
            log_activity(row["user_id"], "LOGOUT", "Authentication", "User logged out")
        return {"message": "Logged out"}
    except Exception as e:
        logger.error("Logout error: %s", e)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        if conn:
            conn.close()


def change_temp_password(user_id: int, current_temp_pw: str, new_pw: str):
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
            return {"error": "Password change only allowed during temporary password stage", "status": 400}
        if not verify_password(current_temp_pw, user["password_hash"]):
            log_activity(
                user_id, "CHANGE_PASSWORD_FAILED", "Authentication",
                "Failed first login password change: invalid temporary password",
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
        conn.commit()
        log_activity(
            user_id, "RESET_PASSWORD", "Authentication",
            f"Successfully changed temporary password for {user['email']}",
        )
        return {"message": "Password changed successfully"}
    except Exception as e:
        conn.rollback()
        logger.error("Error resetting temp password: %s", e)
        return {"error": "Internal server error", "status": 500}
    finally:
        if conn:
            conn.close()


def register_user(
    full_name: str,
    email: str,
    password: str,
    phone: str = None,
    department: str = None,
    employee_id: str = None,
):
    """Public registration — creates inactive user pending Super Admin approval."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        hashed_pw = hash_password(password)
        cur.execute(
            CREATE_USER,
            (full_name, email, hashed_pw, "inactive", "PENDING", phone, department, employee_id),
        )
        new_user = cur.fetchone()
        conn.commit()
        log_activity(new_user["id"], "REGISTER", "Authentication", f"New user registered: {email} (PENDING)")
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
        logger.error("Registration error: %s", e)
        return {"error": "An internal server error occurred", "status": 500}
    finally:
        if conn:
            conn.close()
