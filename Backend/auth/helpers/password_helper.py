import hashlib
import logging
import re
import urllib.request

import bcrypt

from auth.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

_SPECIAL_CHARS = re.compile(r'[!@#$%^&*(),.?":{}|<>]')


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=config.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 10:
        return False, "Password must be at least 10 characters"
    if len(password.encode("utf-8")) > 72:
        # bcrypt silently truncates input beyond 72 bytes, which would make
        # distinct passwords sharing the same 72-byte prefix hash identically.
        return False, "Password must be at most 72 bytes"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    if not _SPECIAL_CHARS.search(password):
        return (
            False,
            'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)',
        )
    return True, ""


def is_password_pwned(password: str) -> bool:
    """Backward-compatible wrapper around HIBPService."""
    from auth.services.hibp_service import HIBPResult, HIBPService

    result = HIBPService.check_password(password)
    return result == HIBPResult.BREACHED
