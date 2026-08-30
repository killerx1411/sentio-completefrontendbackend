"""CV/analysis HTTP routes.

Every route here is authenticated and permission-checked with the *existing*
stakeholder auth stack (``auth.middleware``) — this package deliberately does
not define a second JWT, user store or role system.

Mounted at the application root so the public URLs (/run_analysis, /get_report,
/pin_profile, /update_person_name, /update_person_photo, /delete_person,
/system_info and the operator dashboard at /) are byte-for-byte what they were
before the split.
"""
from __future__ import annotations

import base64
import json
import logging

from flask import Blueprint, Flask, g, jsonify, render_template_string, request

from auth.config import get_config
from auth.middleware.auth_middleware import require_auth, require_permission
from auth.middleware.rate_limiter import limit_authenticated
from auth.services.authorization_service import AuthorizationService, _load_user_scope
from cv_analysis.config import (
    ANALYSIS_DIR,
    MAX_IMAGE_BYTES,
    PROFILES_DIR,
    RATELIMIT_ANALYSIS,
)
from cv_analysis.dashboard import HTML_TEMPLATE
from cv_analysis.libraries import library_status
from cv_analysis.pipeline import analyze_all_dates, generate_multi_day_report
from cv_analysis.routes_analysis import _filter_report_for_user, analysis_bp
from cv_analysis.routes_person import person_bp
from cv_analysis.state import person_database, pinned_profiles

logger = logging.getLogger(__name__)
config = get_config()

cv_bp = Blueprint("cv", __name__)
_analysis_limit = limit_authenticated(RATELIMIT_ANALYSIS)


def register_cv_blueprints(flask_app: Flask) -> None:
    """Mount the whole CV surface (root routes + /analysis + /person) on an app."""
    for bp in (cv_bp, analysis_bp, person_bp):
        flask_app.register_blueprint(bp)


@cv_bp.route('/')
@require_auth(redirect_url=f"{config.FRONTEND_URL.rstrip('/')}/")
def index():
    return render_template_string(HTML_TEMPLATE)


@cv_bp.route('/run_analysis', methods=['POST'])
@_analysis_limit
@require_auth
@require_permission('observations.write')
def run_analysis_endpoint():
    try:
        analyze_all_dates()
        report = generate_multi_day_report()
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        logger.error("Route /run_analysis error: %s", e, exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred'}), 500


@cv_bp.route('/get_report', methods=['GET'])
@_analysis_limit
@require_auth
@require_permission('reports.read')
def get_report():
    try:
        rf = ANALYSIS_DIR / "multi_day_report.json"
        if rf.exists():
            with open(rf) as f:
                report = json.load(f)
            user = _load_user_scope(int(g.user['sub']))
            report = _filter_report_for_user(report, user)
            pinned_profiles.clear()
            pinned_profiles.update(report.get('pinned_profiles', []))
            return jsonify({'success': True, 'report': report})
        return jsonify({'success': False, 'message': 'No report'})
    except Exception as e:
        logger.error("Route /get_report error: %s", e, exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred'}), 500


@cv_bp.route('/pin_profile', methods=['POST'])
@_analysis_limit
@require_auth
@require_permission('reports.write')
def pin_profile():
    try:
        data = request.get_json()
        person_id = data.get('person_id')
        action = data.get('action', 'pin')
        if not person_id:
            return jsonify({'success': False, 'message': 'Missing person_id'})
        person = person_database.get(person_id)
        if not person:
            return jsonify({'success': False, 'message': 'Person not found'}), 404
        user = _load_user_scope(int(g.user['sub']))
        try:
            AuthorizationService.assert_person_access(user, person)
        except PermissionError:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        if action == 'pin':
            pinned_profiles.add(person_id)
        else:
            pinned_profiles.discard(person_id)

        rf = ANALYSIS_DIR / "multi_day_report.json"
        if rf.exists():
            with open(rf) as f:
                report = json.load(f)
            report['pinned_profiles'] = list(pinned_profiles)
            with open(rf, 'w') as f:
                json.dump(report, f, indent=2)

        return jsonify({'success': True, 'pinned': list(pinned_profiles)})
    except Exception as e:
        logger.error("Route /pin_profile error: %s", e, exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred'}), 500


@cv_bp.route('/update_person_name', methods=['POST'])
@require_auth
@require_permission('users.write')
def update_person_name():
    try:
        data = request.get_json()
        pid = data.get('person_id')
        name = data.get('name')
        if not isinstance(name, str):
            return jsonify({'success': False, 'message': 'name must be a string'}), 400
        name = name.strip()
        if not (1 <= len(name) <= 80):
            return jsonify({'success': False, 'message': 'name must be 1-80 characters'}), 400
        if any(ord(ch) < 0x20 for ch in name):
            return jsonify({'success': False, 'message': 'name contains invalid characters'}), 400
        if pid not in person_database:
            return jsonify({'success': False, 'message': 'Person not found'}), 404
        user = _load_user_scope(int(g.user['sub']))
        person = person_database[pid]
        try:
            AuthorizationService.assert_person_access(user, person)
        except PermissionError:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        person_database[pid]['name'] = name

        for fpath in [PROFILES_DIR / "person_database.json", ANALYSIS_DIR / "multi_day_report.json"]:
            if fpath.exists():
                with open(fpath) as f:
                    db = json.load(f)
                target = db if fpath.name.endswith('person_database.json') else db.get('person_profiles', {})
                if pid in target:
                    target[pid]['name'] = name
                with open(fpath, 'w') as f:
                    json.dump(db, f, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        logger.error("Route /update_person_name error: %s", e, exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred'}), 500


@cv_bp.route('/update_person_photo', methods=['POST'])
@require_auth
@require_permission('observations.write')
def update_person_photo():
    try:
        data = request.get_json()
        pid = data.get('person_id')
        b64_string = data.get('image_b64')
        if not pid or not b64_string:
            return jsonify({'success': False, 'message': 'Missing fields'}), 400
        if pid not in person_database:
            return jsonify({'success': False, 'message': 'Person not found'}), 404
        user = _load_user_scope(int(g.user['sub']))
        person = person_database[pid]
        try:
            AuthorizationService.assert_person_access(user, person)
        except PermissionError:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        raw = base64.b64decode(b64_string)
        if len(raw) > MAX_IMAGE_BYTES:
            return jsonify({'success': False, 'message': 'Image too large (max 2MB)'}), 413
        if not (raw[:3] == b'\xff\xd8\xff' or raw[:8] == b'\x89PNG\r\n\x1a\n'):
            return jsonify({'success': False, 'message': 'Only JPEG and PNG allowed'}), 415

        b64 = b64_string
        person_database[pid]['profile_image'] = b64
        person_database[pid]['best_quality'] = 9999

        for fpath in [PROFILES_DIR / "person_database.json", ANALYSIS_DIR / "multi_day_report.json"]:
            if fpath.exists():
                with open(fpath) as f:
                    db = json.load(f)
                target = db if fpath.name.endswith('person_database.json') else db.get('person_profiles', {})
                if pid in target:
                    target[pid]['profile_image'] = b64
                with open(fpath, 'w') as f:
                    json.dump(db, f, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        logger.error("Route /update_person_photo error: %s", e, exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred'}), 500


@cv_bp.route('/delete_person', methods=['POST'])
@require_auth
@require_permission('users.delete')
def delete_person():
    try:
        data = request.get_json()
        pid = data.get('person_id')
        if not pid:
            return jsonify({'success': False, 'message': 'Missing person_id'})

        if pid not in person_database:
            return jsonify({'success': False, 'message': 'Person not found'}), 404

        user = _load_user_scope(int(g.user['sub']))
        person = person_database[pid]
        try:
            AuthorizationService.assert_person_access(user, person)
        except PermissionError:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        person_database.pop(pid, None)
        pinned_profiles.discard(pid)

        for fpath in [PROFILES_DIR / "person_database.json", ANALYSIS_DIR / "multi_day_report.json"]:
            if fpath.exists():
                with open(fpath) as f:
                    db = json.load(f)
                if fpath.name.endswith('person_database.json'):
                    db.pop(pid, None)
                else:
                    db.get('person_profiles', {}).pop(pid, None)
                    db['pinned_profiles'] = list(pinned_profiles)
                    db['overall_stats']['total_unique_persons'] = len(db.get('person_profiles', {}))
                with open(fpath, 'w') as f:
                    json.dump(db, f, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        logger.error("Route /delete_person error: %s", e, exc_info=True)
        return jsonify({'success': False, 'message': 'An internal error occurred'}), 500


@cv_bp.route('/system_info', methods=['GET'])
@require_auth
@require_permission('audit.read')
def system_info():
    return jsonify(library_status())
