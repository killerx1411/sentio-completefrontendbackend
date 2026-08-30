"""TOTP MFA setup, verification, and recovery codes."""

from __future__ import annotations

import base64
import io
import logging
import re
import secrets
from typing import Any

import bcrypt
import pyotp
import qrcode
from cryptography.fernet import Fernet

from auth.config import get_config
from auth.db_connection import get_db_connection, release_db_connection
from auth.helpers.audit_helper import log_activity

logger = logging.getLogger(__name__)
config = get_config()

_RECOVERY_FORMAT = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")


def _fernet() -> Fernet:
    if not config.MFA_ENCRYPTION_KEY:
        raise RuntimeError("MFA_ENCRYPTION_KEY must be set")
    digest = __import__("hashlib").sha256(config.MFA_ENCRYPTION_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def generate_secret() -> str:
    """Return base32 TOTP secret (plaintext before encryption)."""
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()


def get_provisioning_uri(user_email: str, secret: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user_email, issuer_name="Sentio Mind")


def qr_code_base64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def verify_totp(encrypted_secret: str, code: str) -> bool:
    try:
        secret = decrypt_secret(encrypted_secret)
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    except Exception:
        return False


def generate_recovery_codes(n: int = 8) -> list[str]:
    codes = []
    for _ in range(n):
        part = secrets.token_hex(6).upper()[:12]
        codes.append(f"{part[:4]}-{part[4:8]}-{part[8:12]}")
    return codes


def _hash_recovery(code: str) -> str:
    return bcrypt.hashpw(code.encode(), bcrypt.gensalt(rounds=12)).decode()


def store_pending_mfa_secret(user_id: int, plain_secret: str) -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE auth_enabler.users
            SET mfa_secret = %s, mfa_enabled = FALSE
            WHERE id = %s
            """,
            (encrypt_secret(plain_secret), user_id),
        )
        conn.commit()
    finally:
        release_db_connection(conn)


def confirm_mfa(user_id: int, totp_code: str) -> dict[str, Any]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT email, mfa_secret FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row or not row.get("mfa_secret"):
            return {"error": "MFA not initialized", "status": 400}
        if not verify_totp(row["mfa_secret"], totp_code):
            return {"error": "Invalid TOTP code", "status": 400}
        plain_codes = generate_recovery_codes()
        hashed = [_hash_recovery(c) for c in plain_codes]
        cur.execute(
            """
            UPDATE auth_enabler.users
            SET mfa_enabled = TRUE, mfa_recovery_codes = %s
            WHERE id = %s
            """,
            (hashed, user_id),
        )
        conn.commit()
        log_activity(user_id, "mfa_enabled", "Security", "MFA enabled", severity="INFO")
        return {"recovery_codes": plain_codes}
    except Exception as exc:
        conn.rollback()
        logger.error("MFA confirm error: %s", exc)
        return {"error": "Internal error", "status": 500}
    finally:
        release_db_connection(conn)


def verify_recovery_code(user_id: int, code: str) -> bool:
    normalized = code.strip().upper()
    if not _RECOVERY_FORMAT.match(normalized):
        return False
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT mfa_recovery_codes FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        hashes = row.get("mfa_recovery_codes") if row else None
        if not hashes:
            return False
        for idx, stored in enumerate(hashes):
            if stored and bcrypt.checkpw(normalized.encode(), stored.encode()):
                updated = list(hashes)
                updated[idx] = None
                cur.execute(
                    "UPDATE auth_enabler.users SET mfa_recovery_codes = %s WHERE id = %s",
                    (updated, user_id),
                )
                conn.commit()
                log_activity(
                    user_id,
                    "recovery_code_used",
                    "Security",
                    "Recovery code consumed",
                    severity="WARNING",
                )
                return True
        return False
    finally:
        release_db_connection(conn)


def disable_mfa(user_id: int, password: str, totp_code: str) -> dict[str, Any]:
    from auth.helpers.password_helper import verify_password

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT password_hash, mfa_secret, mfa_enabled FROM auth_enabler.users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row or not row.get("mfa_enabled"):
            return {"error": "MFA not enabled", "status": 400}
        if not verify_password(password, row["password_hash"]):
            return {"error": "Invalid password", "status": 401}
        if not verify_totp(row["mfa_secret"], totp_code):
            return {"error": "Invalid TOTP code", "status": 401}
        cur.execute(
            """
            UPDATE auth_enabler.users
            SET mfa_enabled = FALSE, mfa_secret = NULL, mfa_recovery_codes = NULL
            WHERE id = %s
            """,
            (user_id,),
        )
        conn.commit()
        log_activity(user_id, "mfa_disabled", "Security", "MFA disabled", severity="WARNING")
        return {"message": "MFA disabled"}
    except Exception as exc:
        conn.rollback()
        logger.error("MFA disable error: %s", exc)
        return {"error": "Internal error", "status": 500}
    finally:
        release_db_connection(conn)
