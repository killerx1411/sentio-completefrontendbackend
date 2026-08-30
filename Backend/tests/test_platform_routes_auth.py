"""Platform analysis routes on test_db.py must reject unauthenticated requests."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# The combined ``test_db`` app composes the CV blueprints, so importing it pulls
# in OpenCV/DeepFace/MediaPipe/TensorFlow. Those live in requirements-cv.txt and
# are deliberately absent from the auth/B2B production image, so these tests are
# opt-in: run them with SENTIO_RUN_CV_TESTS=1 in an environment that has the CV
# stack installed. See tests/test_service_boundary.py for the separation itself.
pytestmark = pytest.mark.cv



@pytest.fixture
def platform_client():
    os.environ.setdefault("JWT_SECRET_KEY", "a" * 32)
    os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")
    with patch("auth.db_connection.init_auth_db"), patch(
        "auth.db_connection.get_db_connection"
    ) as mock_get:
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.return_value = None
        mock_get.return_value = conn
        import test_db

        test_db.app.config["TESTING"] = True
        test_db.app.config["RATELIMIT_STORAGE_URI"] = "memory://"
        yield test_db.app.test_client()


PLATFORM_ROUTES = [
    ("GET", "/get_report"),
    ("POST", "/run_analysis"),
    ("POST", "/pin_profile"),
    ("POST", "/update_person_name"),
    ("POST", "/update_person_photo"),
    ("POST", "/delete_person"),
    ("GET", "/system_info"),
]


class TestPlatformRoutesAuth:
    @pytest.mark.parametrize("method,path", PLATFORM_ROUTES)
    def test_unauthenticated_returns_401(self, platform_client, method, path):
        if method == "GET":
            resp = platform_client.get(path)
        else:
            resp = platform_client.post(
                path,
                json={"person_id": "p1", "name": "x", "image_b64": "abc"},
            )
        assert resp.status_code == 401
