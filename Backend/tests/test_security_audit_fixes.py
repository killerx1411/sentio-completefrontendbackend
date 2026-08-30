"""Security audit regression tests."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# The combined ``test_db`` app composes the CV blueprints, so importing it pulls
# in OpenCV/DeepFace/MediaPipe/TensorFlow. Those live in requirements-cv.txt and
# are deliberately absent from the auth/B2B production image, so these tests are
# opt-in: run them with SENTIO_RUN_CV_TESTS=1 in an environment that has the CV
# stack installed. See tests/test_service_boundary.py for the separation itself.
pytestmark = pytest.mark.cv


from auth.helpers.jwt_helper import generate_access_token
from auth.helpers.rate_limit_helper import is_password_reset_rate_limited
from auth.services.authorization_service import school_name_to_id


@pytest.fixture
def platform_client(mock_db):
    os.environ.setdefault("JWT_SECRET_KEY", "a" * 32)
    os.environ.setdefault("FLASK_ENV", "test")
    os.environ.setdefault("MFA_ENCRYPTION_KEY", "test-mfa-encryption-key-32chars!!")
    os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")
    with patch("auth.db_connection.init_auth_db"):
        import test_db

        test_db.app.config["TESTING"] = True
        test_db.app.config["SECRET_KEY"] = "a" * 32
        test_db.app.config["RATELIMIT_STORAGE_URI"] = "memory://"
        test_db.app.config["FLASK_ENV"] = "test"
        yield test_db.app.test_client(), test_db


def _auth_headers(user_id, role, scope_type, permissions, school=None, cls=None):
    token = generate_access_token(
        user_id,
        f"user{user_id}@test.com",
        role=role,
        scope_type=scope_type,
        permissions=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


def _active_user_row():
    return {
        "is_first_login": False,
        "registration_status": "APPROVED",
        "status": "active",
    }


def _permission_ok():
    return {"ok": 1}


def _scope_row(user_id, school, cls=None, role="Principal"):
    return {
        "id": user_id,
        "assigned_school": school,
        "assigned_class": cls,
        "school_id": school_name_to_id(school),
        "class_id": school_name_to_id(f"{school}:{cls}") if cls else None,
        "roles": [role],
    }


class TestSecurityAuditFixes:
    def test_update_person_photo_authorization(self, platform_client, mock_db):
        client, test_db_mod = platform_client
        _conn, cur = mock_db
        test_db_mod.person_database.clear()
        test_db_mod.person_database["p-school-b"] = {
            "person_id": "p-school-b",
            "school": "Other School",
            "class_name": "10A",
            "name": "Student B",
        }

        teacher_token = _auth_headers(
            10,
            "Class Teacher",
            "CLASS",
            ["observations.write"],
            school="Greenfield",
            cls="10A",
        )
        with patch("auth.middleware.auth_middleware.is_token_revoked", return_value=False):
            cur.fetchone.side_effect = [
                _active_user_row(),
                None,
            ]
            resp = client.post(
                "/update_person_photo",
                json={"person_id": "p-school-b", "image_b64": "aGVsbG8="},
                headers=teacher_token,
            )
        assert resp.status_code == 403

        scoped_token = _auth_headers(
            11,
            "Principal",
            "SCHOOL",
            ["observations.write"],
            school="Greenfield",
        )
        with patch("auth.middleware.auth_middleware.is_token_revoked", return_value=False):
            cur.fetchone.side_effect = [
                _active_user_row(),
                _permission_ok(),
                _scope_row(11, "Greenfield", role="Principal"),
            ]
            resp2 = client.post(
                "/update_person_photo",
                json={"person_id": "p-school-b", "image_b64": "aGVsbG8="},
                headers=scoped_token,
            )
        assert resp2.status_code == 403

    def test_login_lockout_per_ip(self):
        from auth.helpers import rate_limit_helper as rl

        rl._memory_attempts.clear()
        rl._memory_ip_attempts.clear()
        with patch.object(rl, "_count_attempts_db", side_effect=RuntimeError("db down")), patch.object(
            rl, "_count_ip_attempts_db", side_effect=RuntimeError("db down")
        ), patch.object(rl, "get_db_connection", side_effect=RuntimeError("db down")):
            for i in range(5):
                rl.record_failed_attempt(f"user{i}@example.com", "10.0.0.5")
            assert rl.is_locked_out("new@example.com", "10.0.0.5") is True

    def test_password_reset_rate_limit_fail_closed(self):
        with patch(
            "auth.helpers.rate_limit_helper.get_db_connection",
            side_effect=RuntimeError("db error"),
        ):
            assert is_password_reset_rate_limited("user@example.com") is True

    def test_pin_profile_unknown_person(self, platform_client, mock_db):
        client, test_db_mod = platform_client
        _conn, cur = mock_db
        test_db_mod.person_database.clear()
        token = _auth_headers(1, "Super Admin", "GLOBAL", ["reports.write"])
        with patch("auth.middleware.auth_middleware.is_token_revoked", return_value=False):
            cur.fetchone.side_effect = [
                _active_user_row(),
                _permission_ok(),
            ]
            resp = client.post(
                "/pin_profile",
                json={"person_id": "missing-person"},
                headers=token,
            )
        assert resp.status_code == 404

    def test_role_assign_does_not_stack(self, mock_db):
        from auth.services.role_service import assign_role_to_user

        _conn, cur = mock_db
        cur.fetchone.return_value = {"name": "Principal"}
        assign_role_to_user(7, 1, admin_id=1)
        assign_role_to_user(7, 2, admin_id=1)
        sql_calls = [str(c.args[0]) for c in cur.execute.call_args_list if c.args]
        assert sum("DELETE FROM auth_enabler.user_roles" in s for s in sql_calls) == 2
        insert_calls = [c for c in cur.execute.call_args_list if c.args and "INSERT INTO auth_enabler.user_roles" in str(c.args[0])]
        assert insert_calls[-1][0][1][1] == 2

    def test_remember_me_honored_on_refresh(self, client):
        from auth.constants.cookies import REFRESH_COOKIE
        from auth.helpers.cookie_helper import CSRF_COOKIE
        from auth.middleware.csrf import generate_csrf_token

        csrf = generate_csrf_token(42)
        with patch(
            "auth.routes.auth_routes.refresh_session",
            return_value={
                "access_token": "atk",
                "refresh_token": "rtk",
                "user_id": 42,
                "remember": False,
            },
        ), patch(
            "auth.middleware.csrf.resolve_user_id_from_refresh_cookie",
            return_value=42,
        ), patch(
            "auth.routes.auth_routes.set_refresh_cookie",
            side_effect=lambda resp, token, remember: resp,
        ) as mock_set_cookie:
            client.set_cookie(REFRESH_COOKIE, "refresh-token")
            client.set_cookie(CSRF_COOKIE, csrf)
            resp = client.post(
                "/api/auth/refresh",
                headers={"X-CSRF-Token": csrf},
                json={},
            )
        assert resp.status_code == 200
        mock_set_cookie.assert_called_once()
        assert mock_set_cookie.call_args[0][2] is False

    def test_delete_person_scope_idor(self, platform_client, mock_db):
        client, test_db_mod = platform_client
        _conn, cur = mock_db
        test_db_mod.person_database.clear()
        test_db_mod.person_database["p-other"] = {
            "person_id": "p-other",
            "school": "Other School",
            "class_name": "10A",
            "name": "Other",
        }
        token = _auth_headers(
            5,
            "Super Admin",
            "GLOBAL",
            ["users.delete"],
            school="Greenfield",
        )
        with patch("auth.middleware.auth_middleware.is_token_revoked", return_value=False):
            cur.fetchone.side_effect = [
                _active_user_row(),
                _permission_ok(),
                _scope_row(5, "Greenfield", role="Principal"),
            ]
            resp = client.post(
                "/delete_person",
                json={"person_id": "p-other"},
                headers=token,
            )
        assert resp.status_code == 403

    def test_reset_password_revokes_refresh_tokens(self, mock_db):
        from auth.services.auth_service import reset_password

        _conn, cur = mock_db
        cur.fetchone.return_value = {
            "id": 1,
            "user_id": 99,
            "expires_at": __import__("datetime").datetime.utcnow()
            + __import__("datetime").timedelta(minutes=10),
            "used_at": None,
            "email": "u@test.com",
        }
        with patch(
            "auth.services.auth_service.validate_password_not_breached",
            return_value=None,
        ), patch(
            "auth.services.auth_service.hash_password",
            return_value="hashed",
        ), patch(
            "auth.services.auth_service.revoke_all_refresh_tokens_for_user"
        ) as mock_revoke:
            result = reset_password("valid-token-value-here-1234567890", "NewPass1!word")
        assert "message" in result
        mock_revoke.assert_called_once_with(99, cur=cur)

    def test_signup_duplicate_email_generic_response(self, mock_db):
        from auth.services.auth_service import signup_user
        from psycopg2.errors import UniqueViolation

        _conn, cur = mock_db
        cur.execute.side_effect = UniqueViolation()
        result = signup_user(
            full_name="Test User",
            email="exists@example.com",
            terms_accepted=True,
        )
        assert "error" not in result
        assert "message" in result

    def test_unauthenticated_get_root(self, platform_client):
        client, _ = platform_client
        resp = client.get("/")
        assert resp.status_code in (302, 401)

    def test_nginx_api_security_headers(self):
        conf = Path(__file__).resolve().parents[1].joinpath("nginx", "nginx.conf").read_text()
        assert "location /person/" in conf
        api_block = conf.split("location /api/ {", 1)[1].split("}", 1)[0]
        for header in (
            "Strict-Transport-Security",
            "X-Frame-Options",
            "X-Content-Type-Options",
        ):
            assert header in api_block

    def test_update_person_name_scope_idor(self, platform_client, mock_db):
        client, test_db_mod = platform_client
        _conn, cur = mock_db
        test_db_mod.person_database.clear()
        test_db_mod.person_database["p-other"] = {
            "person_id": "p-other",
            "school": "Other School",
            "class_name": "10A",
            "name": "Other",
        }
        token = _auth_headers(
            5,
            "Principal",
            "SCHOOL",
            ["users.write"],
            school="Greenfield",
        )
        with patch("auth.middleware.auth_middleware.is_token_revoked", return_value=False):
            cur.fetchone.side_effect = [
                _active_user_row(),
                _permission_ok(),
                _scope_row(5, "Greenfield", role="Principal"),
            ]
            resp = client.post(
                "/update_person_name",
                json={"person_id": "p-other", "name": "Hacked"},
                headers=token,
            )
        assert resp.status_code == 403
