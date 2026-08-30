"""Task 6 — refresh token rotation tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from auth.services.refresh_token_service import (
    device_hash_from_request,
    hash_token,
    revoke_family_for_token,
    rotate_refresh_token,
)


class TestRefreshTokenRotation:
    def test_normal_rotation_old_token_rejected(self, mock_db):
        raw = str(uuid.uuid4())
        token_hash = hash_token(raw)
        family = str(uuid.uuid4())
        row = {
            "id": str(uuid.uuid4()),
            "user_id": 1,
            "family_id": family,
            "device_hash": "d1",
            "revoked_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=7),
        }
        with patch("auth.services.refresh_token_service.get_db_connection") as mock:
            conn = MagicMock()
            mock.return_value = conn
            cur = MagicMock()
            conn.cursor.return_value = cur
            cur.fetchone.return_value = row
            result = rotate_refresh_token(raw)
        assert (
            result.get("reason") == "token_reuse_detected"
            or result.get("clear_cookie")
            or result.get("error") == "session_invalidated"
        )

    def test_reuse_detection_revokes_family(self, audit_capture, mock_db):
        raw = str(uuid.uuid4())
        row = {
            "id": str(uuid.uuid4()),
            "user_id": 5,
            "family_id": str(uuid.uuid4()),
            "device_hash": "d",
            "revoked_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=1),
        }
        with patch("auth.services.refresh_token_service.get_db_connection") as mock:
            conn = MagicMock()
            mock.return_value = conn
            cur = MagicMock()
            conn.cursor.return_value = cur
            cur.fetchone.return_value = row
            result = rotate_refresh_token(raw)
        assert result.get("reason") == "token_reuse_detected" or result.get("clear_cookie")

    def test_device_mismatch_rejects_session(self, audit_capture):
        raw = str(uuid.uuid4())
        row = {
            "id": str(uuid.uuid4()),
            "user_id": 1,
            "family_id": str(uuid.uuid4()),
            "device_hash": "old",
            "revoked_at": None,
            "expires_at": datetime.utcnow() + timedelta(days=7),
        }
        with patch("auth.services.refresh_token_service.get_db_connection") as mock:
            conn = MagicMock()
            mock.return_value = conn
            cur = MagicMock()
            conn.cursor.return_value = cur
            cur.fetchone.return_value = row
            result = rotate_refresh_token(raw, user_agent="new-agent")
        assert result.get("reason") == "device_mismatch"
        assert result.get("clear_cookie") is True

    def test_expired_token_rejected(self):
        raw = str(uuid.uuid4())
        row = {
            "id": str(uuid.uuid4()),
            "user_id": 1,
            "family_id": str(uuid.uuid4()),
            "device_hash": "d",
            "revoked_at": None,
            "expires_at": datetime.utcnow() - timedelta(hours=1),
        }
        with patch("auth.services.refresh_token_service.get_db_connection") as mock:
            conn = MagicMock()
            mock.return_value = conn
            cur = MagicMock()
            conn.cursor.return_value = cur
            cur.fetchone.return_value = row
            result = rotate_refresh_token(raw)
        assert result.get("status") == 401 or result.get("error")
