"""JWT revocation fail-closed behavior."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from auth.helpers.jwt_helper import is_token_revoked


class TestTokenRevocationFailClosed:
    def test_db_error_treats_token_as_revoked(self, app):
        with app.app_context():
            with patch(
                "auth.helpers.jwt_helper.get_db_connection",
                side_effect=RuntimeError("db down"),
            ):
                assert is_token_revoked("test-jti") is True
