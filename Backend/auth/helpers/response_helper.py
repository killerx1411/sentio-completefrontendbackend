import datetime
import re

from flask import jsonify

from auth.config import get_config

config = get_config()

_LEAK_PATTERNS = re.compile(
    r"Error|Exception|Traceback|psycopg2|line ",
    re.IGNORECASE,
)


def _sanitize_error_message(message: str) -> str:
    if config.FLASK_ENV != "production":
        return message
    if _LEAK_PATTERNS.search(message or ""):
        return "An internal error occurred"
    return message


def success_response(data=None, message="Success", status_code=200):
    response = {
        "status": "success",
        "message": message,
    }
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code


def error_response(message="An error occurred", status_code=400):
    return jsonify({
        "status": "error",
        "message": _sanitize_error_message(message),
    }), status_code


def sanitize_user_output(user_dict: dict) -> dict:
    if not user_dict:
        return user_dict

    out = dict(user_dict)
    out.pop("password_hash", None)
    out.pop("created_by", None)
    out.pop("updated_by", None)

    expiry = out.pop("temp_password_expiry", None)

    if isinstance(expiry, str):
        try:
            expiry = datetime.datetime.fromisoformat(
                expiry.replace("Z", "+00:00")
            )
        except Exception:
            expiry = None

    if expiry is not None:
        now = datetime.datetime.utcnow()

        if hasattr(expiry, "tzinfo") and expiry.tzinfo:
            now = datetime.datetime.now(datetime.timezone.utc)

        out["is_temp_password_expired"] = now > expiry
    else:
        out["is_temp_password_expired"] = False

    return out
