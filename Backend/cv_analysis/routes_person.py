"""CV person-profile routes with per-resource scope enforcement.

The profiles served here are CV-generated (face clustering output), not
identity records; identity lives in ``auth_enabler.users``.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from auth.middleware.auth_middleware import require_auth, require_permission
from auth.middleware.rate_limiter import limit_authenticated
from auth.services.authorization_service import AuthorizationService, _load_user_scope
from cv_analysis.config import RATELIMIT_ANALYSIS

person_bp = Blueprint("person", __name__, url_prefix="/person")
_person_limit = limit_authenticated(RATELIMIT_ANALYSIS)


def _get_person_from_registry(person_id: str) -> dict | None:
    import json

    from cv_analysis.config import ANALYSIS_DIR

    rf = ANALYSIS_DIR / "multi_day_report.json"
    if rf.exists():
        with open(rf, encoding="utf-8") as f:
            report = json.load(f)
        return (report.get("person_profiles") or {}).get(person_id)
    return None


@person_bp.route("/<person_id>", methods=["GET"])
@_person_limit
@require_auth
@require_permission("reports.read")
def get_person(person_id: str):
    user = _load_user_scope(int(g.user["sub"]))
    person = _get_person_from_registry(person_id)
    if not person:
        return jsonify({"error": "not_found"}), 404
    try:
        AuthorizationService.assert_person_access(user, person)
    except PermissionError:
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"success": True, "person": person})


@person_bp.route("/<person_id>/access-check", methods=["POST"])
@_person_limit
@require_auth
@require_permission("reports.read")
def check_person_access(person_id: str):
    """Explicit scope check endpoint used by tests."""
    user = _load_user_scope(int(g.user["sub"]))
    person = _get_person_from_registry(person_id) or {}
    if not person:
        return jsonify({"error": "not_found"}), 404
    try:
        AuthorizationService.assert_person_access(user, person)
        return jsonify({"allowed": True}), 200
    except PermissionError:
        return jsonify({"error": "forbidden"}), 403
