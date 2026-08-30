"""Task 7 — startup security checks."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app_factory import create_auth_app
from auth.startup_checks import run_startup_checks


def _production_app():
    """An auth app flipped into the production posture the checks assert on."""
    app = create_auth_app(testing=True)
    app.config["ENV"] = "production"
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["PREFERRED_URL_SCHEME"] = "https"
    app.config["SECRET_KEY"] = "x" * 32
    app.config["DATABASE_URL"] = "postgresql://db.internal:5432/sentio"
    app.config["RATELIMIT_STORAGE_URI"] = "rediss://cache.example:6379/1"
    app.config["DEBUG"] = False
    return app



class TestStartupChecks:
    def test_production_secure_false_raises(self):
        app = create_auth_app(testing=True)
        app.config["ENV"] = "production"
        app.config["FLASK_ENV"] = "production"
        app.config["SESSION_COOKIE_SECURE"] = False
        with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE"):
            run_startup_checks(app)

    def test_production_all_checks_pass(self):
        app = _production_app()
        with patch("auth.startup_checks.log_activity"):
            run_startup_checks(app)

    def test_production_rejects_memory_rate_limit_storage(self):
        """memory:// is per-process: it would not rate-limit across Cloud Run
        instances or gunicorn workers, so production must refuse to start."""
        app = _production_app()
        app.config["RATELIMIT_STORAGE_URI"] = "memory://"
        with pytest.raises(RuntimeError, match="RATELIMIT_STORAGE_URI"):
            run_startup_checks(app)

    def test_production_rejects_debug(self):
        app = _production_app()
        app.config["DEBUG"] = True
        with pytest.raises(RuntimeError, match="DEBUG"):
            run_startup_checks(app)

    def test_development_skips_checks(self):
        app = create_auth_app(testing=True)
        app.config["ENV"] = "development"
        app.config["SESSION_COOKIE_SECURE"] = False
        run_startup_checks(app)
