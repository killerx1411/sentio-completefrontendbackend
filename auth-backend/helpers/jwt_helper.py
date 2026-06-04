import jwt
import datetime
import uuid
from config import get_config

config = get_config()


def generate_access_token(
    user_id: int,
    email: str,
    roles: list = None,
    role: str = None,
    scope_type: str = None,
    permissions: list = None,
) -> str:
    role_names = [r["name"] if isinstance(r, dict) else r for r in (roles or [])]
    payload = {
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(minutes=config.JWT_ACCESS_MINUTES),
        "iat": datetime.datetime.utcnow(),
        "sub": user_id,
        "email": email,
        "roles": role_names,
        "type": "access",
    }
    if role:
        payload["role"] = role
    if scope_type:
        payload["scope_type"] = scope_type
    if permissions:
        payload["permissions"] = permissions
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm="HS256")


def generate_refresh_token_value() -> str:
    return str(uuid.uuid4())


def decode_token(auth_token: str):
    try:
        return jwt.decode(auth_token, config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return "Signature expired. Please log in again."
    except jwt.InvalidTokenError:
        return "Invalid token. Please log in again."


def generate_token(user_id: int, email: str, role: str = None, scope_type: str = None, permissions: list = None) -> str:
    """Backward-compatible alias used by legacy callers."""
    return generate_access_token(
        user_id, email, role=role, scope_type=scope_type, permissions=permissions
    )
