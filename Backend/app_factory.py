"""Stakeholder / authentication application factory.

This module is the boundary marker: it builds a fully functional Flask app for
authentication, authorization, users, roles, MFA, sessions, audit and security
middleware, and it imports **nothing** from ``cv_analysis``. Importing it does
not load OpenCV, DeepFace, MediaPipe, face_recognition, MTCNN or TensorFlow,
so the stakeholder service can be installed and run from
``requirements.txt`` alone.

Entry points::

    gunicorn -c gunicorn_config.py wsgi_auth:app   # stakeholder/auth only
    python wsgi_auth.py                            # local dev, auth only
    gunicorn -c gunicorn_config.py test_db:app     # combined auth + CV (legacy)
"""
from __future__ import annotations

import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from auth.env_loader import load_env

load_env()

from auth.config import get_config, validate_config
from auth.db_connection import init_auth_db
from auth.middleware.rate_limiter import init_rate_limiter
from auth.routes.admin_routes import admin_bp
from auth.routes.audit_routes import audit_bp
from auth.routes.auth_routes import auth_bp
from auth.routes.mfa_routes import mfa_bp
from auth.routes.role_routes import role_bp
from auth.routes.security_routes import security_bp
from auth.routes.user_routes import user_bp
from auth.startup_checks import run_startup_checks
from common.http import CORS_ALLOW_HEADERS, apply_proxy_fix, apply_security_headers

logger = logging.getLogger(__name__)

AUTH_BLUEPRINTS = (
    auth_bp,
    role_bp,
    audit_bp,
    user_bp,
    admin_bp,
    mfa_bp,
    security_bp,
)


def register_auth_blueprints(flask_app: Flask) -> None:
    for bp in AUTH_BLUEPRINTS:
        flask_app.register_blueprint(bp)


def create_auth_app(testing: bool = False) -> Flask:
    """Build the stakeholder/auth Flask app. No CV imports, ever."""
    flask_app = Flask(__name__)
    cfg = get_config()
    flask_app.config.from_object(cfg)
    # Never inherit DEBUG from a stray FLASK_DEBUG in the environment: the
    # Werkzeug debugger is remote code execution on a public endpoint.
    flask_app.config["DEBUG"] = False
    flask_app.debug = False

    if testing:
        flask_app.config.update(
            {
                "TESTING": True,
                "SECRET_KEY": cfg.JWT_SECRET_KEY,
                "RATELIMIT_STORAGE_URI": "memory://",
                "RATELIMIT_STRATEGY": "fixed-window",
                "FLASK_ENV": "test",
                "ENV": "test",
            }
        )

    CORS(
        flask_app,
        origins=cfg.ALLOWED_ORIGINS,
        supports_credentials=True,
        allow_headers=CORS_ALLOW_HEADERS,
    )
    init_rate_limiter(flask_app)
    apply_proxy_fix(flask_app)
    register_auth_blueprints(flask_app)

    @flask_app.after_request
    def _security_headers(response):
        return apply_security_headers(response)

    # JSON errors for a JSON API, and — more importantly — never the Werkzeug
    # debugger or a traceback in a response body.
    @flask_app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        return (
            jsonify({"error": exc.name.lower().replace(" ", "_"), "message": exc.description}),
            exc.code or 500,
        )

    if not testing:
        # Not registered under TESTING: swallowing exceptions here would turn a
        # broken test into a green 500 instead of a traceback.
        @flask_app.errorhandler(Exception)
        def _unhandled_error(exc: Exception):
            logger.exception("Unhandled error on %s %s", request.method, request.path)
            return jsonify({"error": "internal_server_error"}), 500

    # Liveness/readiness for Cloud Run and the load balancer. Deliberately does
    # not touch PostgreSQL or Redis: a dependency outage must show up as failing
    # requests and alerts, not as Cloud Run tearing down every healthy instance.
    @flask_app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy", "service": "Sentio Auth API"}), 200

    # Dependency-aware probe for humans and uptime checks; never wire this one
    # to the container health check.
    @flask_app.route("/health/ready", methods=["GET"])
    def readiness_check():
        checks = {}
        ok = True
        try:
            init_auth_db()
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            logger.warning("Readiness: database check failed: %s", exc)
            checks["database"] = "unavailable"
            ok = False

        storage = flask_app.config.get("RATELIMIT_STORAGE_URI", "")
        if storage.startswith(("redis://", "rediss://")):
            try:
                import redis

                redis.from_url(storage).ping()
                checks["rate_limit_store"] = "ok"
            except Exception as exc:  # noqa: BLE001 - reported, not raised
                logger.warning("Readiness: rate-limit store check failed: %s", exc)
                checks["rate_limit_store"] = "unavailable"
                ok = False
        else:
            checks["rate_limit_store"] = storage.split("://")[0] or "unset"

        return jsonify({"status": "ready" if ok else "degraded", "checks": checks}), (
            200 if ok else 503
        )

    if not testing:
        # Under gunicorn nothing calls run_auth_preflight (only `python
        # wsgi_auth.py` did), so the production security assertions have to run
        # here or they never run in the deployment that actually needs them.
        validate_config(cfg)
        run_startup_checks(flask_app)
        try:
            init_auth_db()
        except Exception as auth_err:
            logger.warning(
                "Auth DB init at import failed (will retry on first request): %s",
                auth_err,
            )

    return flask_app


def run_auth_preflight(flask_app: Flask) -> None:
    """Validate security configuration and warm the auth DB pool."""
    cfg = get_config()
    validate_config(cfg)
    run_startup_checks(flask_app)
    init_auth_db()
    logger.info(
        "Sentio stakeholder/auth starting | env=%s | jwt_expiry=%smin | cors_origins=%s",
        cfg.FLASK_ENV,
        cfg.JWT_ACCESS_TOKEN_EXPIRES_MINUTES,
        cfg.ALLOWED_ORIGINS,
    )
