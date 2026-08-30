"""Additional security regression tests from audit."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from auth.helpers.jwt_helper import generate_access_token


class TestRefreshBodyTokenRejected:
    def test_refresh_json_body_without_cookie_returns_401(self, client):
        resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "stolen-token"},
        )
        assert resp.status_code in (401, 403)


class TestDashboardStatsPermission:
    def test_teacher_role_gets_403(self, client, mock_db):
        _conn, cur = mock_db
        cur.fetchone.side_effect = [
            None,
            {
                "is_first_login": False,
                "registration_status": "APPROVED",
                "status": "active",
            },
            None,
        ]
        token = generate_access_token(
            99,
            "teacher@test.com",
            role="Class Teacher",
            scope_type="CLASS",
            permissions=["reports.read"],
        )
        resp = client.get(
            "/api/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestSignupRateLimit:
    def test_signup_burst_returns_429(self, client):
        with patch(
            "auth.routes.auth_routes.signup_user",
            return_value={"message": "ok", "user": {"id": 1}},
        ):
            last = None
            for i in range(25):
                last = client.post(
                    "/api/auth/signup",
                    json={
                        "email": f"user{i}@test.com",
                        "full_name": "Test User",
                        "terms_accepted": True,
                    },
                )
        assert last.status_code == 429
