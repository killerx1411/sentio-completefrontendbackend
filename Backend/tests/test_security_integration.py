"""Task 10 — cross-cutting security integration tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from auth.helpers.jwt_helper import generate_access_token, generate_mfa_pending_token
from auth.helpers.redis_client import redis_clear_memory
from auth.middleware.csrf import generate_csrf_token


class TestSecurityIntegration:
    def setup_method(self):
        redis_clear_memory()

    def test_mfa_pending_token_rejected_as_access(self, client, mock_db):
        _conn, cur = mock_db
        cur.fetchone.return_value = {
            "is_first_login": False,
            "registration_status": "APPROVED",
            "status": "active",
        }
        pending = generate_mfa_pending_token(1, "u@test.com")
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {pending}"},
        )
        assert resp.status_code == 401

    def test_csrf_mismatched_cookie_and_header_403(self, client):
        from auth.helpers.cookie_helper import CSRF_COOKIE

        cookie_token = generate_csrf_token(1)
        header_token = generate_csrf_token(2)
        with patch(
            "auth.middleware.csrf.resolve_user_id_from_refresh_cookie",
            return_value=1,
        ):
            client.set_cookie(CSRF_COOKIE, cookie_token)
            resp = client.post(
                "/api/auth/refresh",
                headers={"X-CSRF-Token": header_token},
            )
        assert resp.status_code == 403

    def test_audit_events_defined_in_tasks(self, client):
        with patch(
            "auth.routes.auth_routes.login_user",
            return_value={"error": "x", "status": 401},
        ), patch("auth.middleware.rate_limiter.log_activity") as mock_audit:
            for _ in range(15):
                client.post("/api/auth/login", json={"email": "z@z.com", "password": "p"})
        assert any(
            c[0][1] == "rate_limit_exceeded" for c in mock_audit.call_args_list
        )

    def test_concurrent_refresh_race_reuse(self, mock_db):
        raw = "same-token"
        calls = {"n": 0}

        def fake_rotate(token, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"rotated": True, "refresh_token": "new", "user_id": 1}
            return {"reason": "token_reuse_detected", "clear_cookie": True, "status": 401}

        with patch(
            "auth.services.auth_service.rotate_refresh_token",
            side_effect=fake_rotate,
        ), patch("auth.services.auth_service._get_user_roles", return_value=[]):
            from auth.services import auth_service

            _conn, cur = mock_db
            cur.fetchone.return_value = {
                "email": "u@test.com",
                "status": "active",
                "registration_status": "APPROVED",
            }
            r1 = auth_service.refresh_session(raw)
            r2 = auth_service.refresh_session(raw)
        assert r1.get("access_token")
        assert r2.get("reason") == "token_reuse_detected"
