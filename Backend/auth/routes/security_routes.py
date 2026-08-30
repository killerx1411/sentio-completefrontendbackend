"""Security reporting endpoints (CSP violations)."""

from __future__ import annotations

import json
import logging

from flask import Blueprint, request

from auth.config import get_config
from auth.helpers.audit_helper import log_activity
from auth.helpers.request_helper import get_client_ip
from auth.middleware.rate_limiter import limit_ip

logger = logging.getLogger(__name__)
security_bp = Blueprint("security", __name__, url_prefix="/api")
config = get_config()


@security_bp.route("/csp-report", methods=["POST"])
@limit_ip(config.RATELIMIT_CSP_REPORT)
def csp_report():
    """Accept browser CSP violation reports."""
    body = request.get_data(as_text=True) or "{}"
    try:
        if request.content_type and "application/csp-report" in request.content_type:
            payload = json.loads(body) if body else {}
        else:
            payload = request.get_json(silent=True) or json.loads(body) if body else {}
    except json.JSONDecodeError:
        payload = {"raw": body[:2000]}

    log_activity(
        None,
        "csp_violation",
        "Security",
        json.dumps(payload)[:4000],
        ip_address=get_client_ip(),
        severity="WARNING",
    )
    return "", 204
