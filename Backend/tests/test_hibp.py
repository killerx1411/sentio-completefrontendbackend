"""Task 8 — HIBP circuit breaker tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from auth.services.hibp_service import HIBPResult, HIBPService, validate_password_not_breached


class TestHIBPCircuitBreaker:
    def setup_method(self):
        HIBPService.clear_cache()

    def test_breach_returns_400(self):
        with patch.object(HIBPService, "check_password", return_value=HIBPResult.BREACHED):
            err = validate_password_not_breached("Password1!@#")
        assert err["status"] == 400

    def test_timeout_unavailable(self):
        with patch.object(
            HIBPService,
            "_query_hibp",
            side_effect=TimeoutError("timeout"),
        ):
            assert HIBPService.check_password("x") == HIBPResult.UNAVAILABLE

    def test_strict_unavailable_503(self):
        with patch.object(HIBPService, "check_password", return_value=HIBPResult.UNAVAILABLE):
            with patch("auth.services.hibp_service.config") as cfg:
                cfg.STRICT_PASSWORD_BREACH_CHECK = True
                err = validate_password_not_breached("Password1!@#")
        assert err["status"] == 503

    def test_non_strict_unavailable_allowed(self):
        import auth.services.hibp_service as hibp_mod

        with patch.object(HIBPService, "check_password", return_value=HIBPResult.UNAVAILABLE):
            with patch("auth.services.hibp_service.log_activity") as mock_log:
                original = hibp_mod.config.STRICT_PASSWORD_BREACH_CHECK
                hibp_mod.config.STRICT_PASSWORD_BREACH_CHECK = False
                try:
                    err = validate_password_not_breached("Password1!@#", user_id=1)
                finally:
                    hibp_mod.config.STRICT_PASSWORD_BREACH_CHECK = original
        assert err is None
        mock_log.assert_called_once()
        assert mock_log.call_args[0][1] == "hibp_check_skipped"

    def test_circuit_opens_and_closes(self):
        HIBPService.clear_cache()
        with patch.object(
            HIBPService,
            "_query_hibp",
            side_effect=ConnectionError("down"),
        ):
            HIBPService.check_password("a")
            assert HIBPService._circuit_open
            HIBPService._circuit_open_until = datetime.utcnow() - timedelta(seconds=1)
            with patch.object(HIBPService, "_query_hibp", return_value=HIBPResult.CLEAN):
                assert HIBPService.check_password("a") == HIBPResult.CLEAN

    def test_cache_avoids_second_http_request(self):
        with patch.object(HIBPService, "_fetch_range", return_value=set()) as fetch:
            HIBPService.check_password("SamePass1!@#")
            HIBPService.check_password("SamePass1!@#")
        assert fetch.call_count == 1
