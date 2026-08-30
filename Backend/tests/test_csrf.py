"""Task 2 — CSRF protection tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from auth.helpers.cookie_helper import CSRF_COOKIE
from auth.middleware.csrf import generate_csrf_token, validate_csrf_token


def _csrf_headers(token: str) -> dict:
    return {"X-CSRF-Token": token}


class TestCSRF:
    def test_stateless_csrf_validate(self):
        token = generate_csrf_token(42)
        assert validate_csrf_token(42, token) is True
        assert validate_csrf_token(43, token) is False

    def test_refresh_without_header_403(self, client):
        token = generate_csrf_token(1)
        with patch(
            "auth.routes.auth_routes.refresh_session",
            return_value={"access_token": "atk", "refresh_token": "rtk", "user_id": 1},
        ), patch(
            "auth.middleware.csrf.resolve_user_id_from_refresh_cookie",
            return_value=1,
        ), patch("auth.routes.auth_routes.set_refresh_cookie", side_effect=lambda r, *a: r):
            client.set_cookie(CSRF_COOKIE, token)
            resp = client.post("/api/auth/refresh")
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "csrf_validation_failed"

    def test_refresh_wrong_token_403(self, client):
        token = generate_csrf_token(1)
        with patch(
            "auth.routes.auth_routes.refresh_session",
            return_value={"access_token": "atk", "refresh_token": "rtk", "user_id": 1},
        ), patch(
            "auth.middleware.csrf.resolve_user_id_from_refresh_cookie",
            return_value=1,
        ), patch("auth.routes.auth_routes.set_refresh_cookie", side_effect=lambda r, *a: r):
            client.set_cookie(CSRF_COOKIE, token)
            resp = client.post(
                "/api/auth/refresh",
                headers=_csrf_headers("bad"),
            )
        assert resp.status_code == 403

    def test_refresh_correct_token_200(self, client):
        from auth.constants.cookies import REFRESH_COOKIE

        token = generate_csrf_token(1)
        with patch(
            "auth.routes.auth_routes.refresh_session",
            return_value={
                "access_token": "atk",
                "refresh_token": "rtk",
                "user_id": 1,
                "remember": True,
            },
        ), patch(
            "auth.middleware.csrf.resolve_user_id_from_refresh_cookie",
            return_value=1,
        ), patch("auth.routes.auth_routes.set_refresh_cookie", side_effect=lambda r, *a: r):
            client.set_cookie(REFRESH_COOKIE, "valid-refresh-token")
            client.set_cookie(CSRF_COOKIE, token)
            resp = client.post(
                "/api/auth/refresh",
                headers=_csrf_headers(token),
                json={},
            )
        assert resp.status_code == 200, resp.get_data(as_text=True)

    def test_logout_clears_csrf_cookie(self, client):
        token = generate_csrf_token(1)
        with patch(
            "auth.routes.auth_routes.logout_user",
            return_value={"message": "Logged out"},
        ), patch(
            "auth.middleware.csrf.resolve_user_id_from_refresh_cookie",
            return_value=1,
        ), patch("auth.routes.auth_routes.clear_refresh_cookie", side_effect=lambda r: r):
            client.set_cookie(CSRF_COOKIE, token)
            resp = client.post(
                "/api/auth/logout",
                headers={**_csrf_headers(token), "Content-Type": "application/json"},
                json={},
            )
        assert resp.status_code == 200
        set_cookie = resp.headers.get("Set-Cookie", "")
        assert CSRF_COOKIE in set_cookie
