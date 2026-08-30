"""Shared pytest fixtures for auth security tests."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "a" * 32)
os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("MFA_ENCRYPTION_KEY", "test-mfa-encryption-key-32chars!!")
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")
os.environ.setdefault("STRICT_PASSWORD_BREACH_CHECK", "false")


@pytest.fixture
def app():
    # Import the auth factory directly, never test_db: test_db composes the CV
    # blueprints onto the app and its import pulls in OpenCV/DeepFace/MediaPipe.
    # The auth suite must run on requirements.txt alone (see
    # tests/test_service_boundary.py).
    from app_factory import create_auth_app

    application = create_auth_app(testing=True)
    application.config["RATELIMIT_STORAGE_URI"] = "memory://"
    application.config["RATELIMIT_STRATEGY"] = "fixed-window"
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_db():
    """Mock pooled PostgreSQL connections."""
    mock_pool = MagicMock()
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    mock_pool.getconn.return_value = conn
    with patch("auth.db_connection._get_pool", return_value=mock_pool), patch(
        "auth.db_connection._POOL", mock_pool
    ), patch("auth.db_connection.get_db_connection", return_value=conn), patch(
        "auth.db_connection.release_db_connection"
    ):
        yield conn, cur


@pytest.fixture(autouse=True)
def _autouse_mock_db(mock_db):
    return mock_db


@pytest.fixture
def audit_capture():
    entries = []

    def _capture(*args, **kwargs):
        entries.append({"args": args, "kwargs": kwargs})

    with patch("auth.helpers.audit_helper.log_activity", side_effect=_capture):
        yield entries


def pytest_collection_modifyitems(config, items):
    """Skip CV-marked tests unless SENTIO_RUN_CV_TESTS=1.

    The auth/B2B service is installed from requirements.txt alone and its image
    contains no OpenCV/DeepFace/MediaPipe/TensorFlow, so `pytest tests` must be
    green there. Tests that exercise the combined `test_db` app (auth + CV) are
    opt-in and need requirements-cv.txt installed.
    """
    if os.environ.get("SENTIO_RUN_CV_TESTS") == "1":
        return
    skip_cv = pytest.mark.skip(
        reason="CV stack not installed (set SENTIO_RUN_CV_TESTS=1 to run)"
    )
    for item in items:
        if "cv" in item.keywords:
            item.add_marker(skip_cv)
