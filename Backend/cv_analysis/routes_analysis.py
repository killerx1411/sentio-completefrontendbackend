"""Scope-aware access to CV-generated reports.

Stakeholder-facing, but CV-owned: every byte it serves is produced by the CV
pipeline and read from ``analysis_results/``. It applies the auth package's
RBAC + row-level scope rather than defining any authorization of its own.
"""

from __future__ import annotations

import json

from flask import Blueprint, g, jsonify

from auth.middleware.auth_middleware import require_auth, require_permission
from auth.middleware.rate_limiter import limit_authenticated
from auth.services.authorization_service import (
    AuthorizationService,
    User,
    _load_user_scope,
    school_name_to_id,
)
from cv_analysis.config import ANALYSIS_DIR, RATELIMIT_ANALYSIS

analysis_bp = Blueprint("analysis", __name__, url_prefix="/analysis")
_analysis_limit = limit_authenticated(RATELIMIT_ANALYSIS)


def _filter_report_for_user(report: dict, user: User) -> dict:
    """Apply school/class scope filters in SQL-style WHERE semantics on report dict."""
    profiles = report.get("person_profiles") or {}
    school_filter = AuthorizationService.get_school_filter(user)
    class_filter = AuthorizationService.get_class_filter(user)

    filtered = {}
    for pid, person in profiles.items():
        school_id = school_name_to_id(person.get("school"))
        if school_filter is not None and school_id != school_filter:
            continue
        if class_filter is not None:
            class_id = school_name_to_id(
                f"{person.get('school')}:{person.get('class_name')}"
            )
            if class_id != class_filter:
                continue
        if user.scope_type == "SCHOOL_FLAGGED":
            flagged = person.get("flagged", person.get("average_wellbeing", 100) < 40)
            if not flagged:
                continue
        try:
            AuthorizationService.assert_person_access(user, person)
        except PermissionError:
            continue
        filtered[pid] = person

    out = dict(report)
    out["person_profiles"] = filtered
    if "overall_stats" in out:
        out["overall_stats"] = {
            **out.get("overall_stats", {}),
            "total_unique_persons": len(filtered),
        }
    return out


@analysis_bp.route("/report", methods=["GET"])
@_analysis_limit
@require_auth
@require_permission("reports.read")
def get_scoped_report():
    user = _load_user_scope(int(g.user["sub"]))
    rf = ANALYSIS_DIR / "multi_day_report.json"
    if not rf.exists():
        return jsonify({"success": False, "message": "No report"}), 404
    with open(rf, encoding="utf-8") as f:
        report = json.load(f)
    scoped = _filter_report_for_user(report, user)
    return jsonify({"success": True, "report": scoped})


@analysis_bp.route("/run", methods=["POST"])
@_analysis_limit
@require_auth
@require_permission("observations.write")
def run_analysis_stub():
    return jsonify({"success": False, "message": "Use POST /run_analysis"}), 501
