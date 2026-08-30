import re
import uuid

from email_validator import validate_email as _validate_email, EmailNotValidError

_JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def sanitize_email(email: str) -> str:
    if not email or not isinstance(email, str):
        raise ValueError("Email is required")
    cleaned = email.strip().lower()
    try:
        result = _validate_email(cleaned, check_deliverability=False)
        return result.normalized
    except EmailNotValidError as exc:
        raise ValueError("Invalid email address") from exc


def sanitize_string(value: str, max_length: int, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if "\x00" in value:
        raise ValueError(f"{field_name} contains invalid characters")
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return cleaned


def validate_uuid(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def validate_pagination(
    page: int, per_page: int, max_per_page: int = 100
) -> tuple[int, int]:
    page = max(1, int(page) if page is not None else 1)
    per_page = int(per_page) if per_page is not None else 20
    per_page = max(1, min(per_page, max_per_page))
    return page, per_page


def mask_sensitive(text: str) -> str:
    if not text:
        return text
    return _JWT_PATTERN.sub("[JWT_REDACTED]", str(text))
