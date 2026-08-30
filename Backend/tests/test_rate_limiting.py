"""Task 1 — global rate limiting tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestRateLimiting:
    def test_login_burst_returns_429_with_retry_after(self, client, audit_capture):
        with patch(
            "auth.routes.auth_routes.login_user",
            return_value={"error": "Invalid email or password", "status": 401},
        ), patch("auth.middleware.rate_limiter.log_activity") as mock_audit:
            last = None
            for _ in range(15):
                last = client.post(
                    "/api/auth/login",
                    json={"email": "burst@b.com", "password": "x"},
                )
            resp = last
        assert resp.status_code == 429
        data = resp.get_json()
        assert data["error"] == "rate_limit_exceeded"
        assert "retry_after" in data
        assert resp.headers.get("Retry-After")
        assert mock_audit.called
        assert any(
            call[0][1] == "rate_limit_exceeded"
            for call in mock_audit.call_args_list
        )

    def test_authenticated_vs_ip_key_separation(self, app):
        from auth.middleware.rate_limiter import _authenticated_key

        with app.test_request_context("/", environ_base={"REMOTE_ADDR": "1.2.3.4"}):
            ip_key = _authenticated_key()
        assert ip_key == "1.2.3.4"

        with app.test_request_context(
            "/",
            headers={"Authorization": "Bearer valid"},
            environ_base={"REMOTE_ADDR": "9.9.9.9"},
        ):
            with patch(
                "auth.helpers.jwt_helper.decode_token",
                return_value={"sub": 42, "type": "access"},
            ):
                user_key = _authenticated_key()
        assert user_key == "user:42"
