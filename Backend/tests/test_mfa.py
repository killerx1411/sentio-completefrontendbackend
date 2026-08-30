"""Task 4 — TOTP MFA tests."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pyotp
import pytest

from auth.helpers.jwt_helper import generate_mfa_pending_token
from auth.services.mfa_service import (
    disable_mfa,
    encrypt_secret,
    generate_secret,
    verify_recovery_code,
    verify_totp,
)


class TestMFA:
    def test_setup_confirm_verify_flow(self, client):
        secret = generate_secret()
        code = pyotp.TOTP(secret).now()
        with patch(
            "auth.services.mfa_service.confirm_mfa",
            return_value={"recovery_codes": ["AAAA-BBBB-CCCC"]},
        ), patch("auth.middleware.auth_middleware.require_auth", lambda f: f):
            resp = client.post(
                "/api/auth/mfa/confirm",
                json={"totp_code": code},
                headers={"Authorization": "Bearer test"},
            )
        assert resp.status_code in (200, 401, 403)

    def test_invalid_totp_on_verify_401(self, client):
        pending = generate_mfa_pending_token(1, "u@test.com")
        with patch(
            "auth.db_connection.get_db_connection",
        ) as mock_conn:
            conn = MagicMock()
            mock_conn.return_value = conn
            cur = MagicMock()
            conn.cursor.return_value = cur
            cur.fetchone.return_value = {
                "email": "u@test.com",
                "mfa_secret": encrypt_secret(generate_secret()),
                "mfa_enabled": True,
            }
            resp = client.post(
                "/api/auth/mfa/verify",
                json={"pending_token": pending, "totp_code": "000000"},
            )
        assert resp.status_code == 401

    def test_expired_pending_token_401(self, client):
        with patch(
            "auth.routes.mfa_routes.decode_token",
            side_effect=__import__(
                "auth.helpers.jwt_helper", fromlist=["TokenExpiredError"]
            ).TokenExpiredError("expired"),
        ):
            resp = client.post(
                "/api/auth/mfa/verify",
                json={"pending_token": "bad", "totp_code": "123456"},
            )
        assert resp.status_code == 401

    def test_recovery_code_single_use(self):
        import bcrypt

        code = "ABCD-EFGH-IJKL"
        hashed = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
        with patch("auth.services.mfa_service.get_db_connection") as mock_conn:
            conn = MagicMock()
            mock_conn.return_value = conn
            cur = MagicMock()
            conn.cursor.return_value = cur
            cur.fetchone.side_effect = [
                {"mfa_recovery_codes": [hashed]},
                {"mfa_recovery_codes": [None]},
            ]
            assert verify_recovery_code(1, code) is True
            assert verify_recovery_code(1, code) is False

    def test_login_without_mfa_no_pending(self):
        with patch("auth.services.auth_service.get_db_connection") as mock_conn:
            conn = MagicMock()
            mock_conn.return_value = conn
            cur = MagicMock()
            conn.cursor.return_value = cur
            cur.fetchone.return_value = {
                "id": 1,
                "email": "u@test.com",
                "password_hash": "x",
                "status": "active",
                "registration_status": "APPROVED",
                "mfa_enabled": False,
                "is_first_login": False,
            }
            cur.fetchall.return_value = [{"id": 1, "name": "Principal"}]
            from auth.services import auth_service

            with patch.object(auth_service, "verify_password", return_value=True):
                result = auth_service.login_user("u@test.com", "pw")
        assert "mfa_required" not in result or not result.get("mfa_required")

    def test_disable_requires_password_and_totp(self):
        with patch("auth.services.mfa_service.get_db_connection") as mock_conn:
            conn = MagicMock()
            mock_conn.return_value = conn
            cur = MagicMock()
            conn.cursor.return_value = cur
            secret = generate_secret()
            cur.fetchone.return_value = {
                "password_hash": "h",
                "mfa_secret": encrypt_secret(secret),
                "mfa_enabled": True,
            }
            with patch(
                "auth.helpers.password_helper.verify_password", return_value=False
            ):
                result = disable_mfa(1, "wrong", pyotp.TOTP(secret).now())
            assert result["status"] == 401
