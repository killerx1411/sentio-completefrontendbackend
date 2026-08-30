"""Production configuration guardrails for https://b2bapi.sentiomind.in.

These assert the things that, if wrong, produce a service that looks healthy
and is not: rate limiting that does not limit, a database that vanishes on cold
start, CORS that lets any origin carry credentials, DEBUG left on.

Every case runs `validate_config` against a fresh `AuthConfig` built in a child
environment, because AuthConfig reads os.environ at class-definition time.
"""

from __future__ import annotations

import importlib

import pytest

BASE_PRODUCTION_ENV = {
    "FLASK_ENV": "production",
    "JWT_SECRET_KEY": "p" * 48,
    "MFA_ENCRYPTION_KEY": "a1" * 32,
    "SENTIO_DB_URL": "postgresql://sentio:pw@db.prod.internal:5432/sentio_b2b",
    "SENTIO_DB_SSLMODE": "require",
    "RATELIMIT_STORAGE_URI": "rediss://default:tok@cache.upstash.io:6379",
    "REDIS_URL": "rediss://default:tok@cache.upstash.io:6379/2",
    "FRONTEND_URL": "https://product.sentiomind.in",
    "ALLOWED_ORIGINS": "https://product.sentiomind.in",
    "SMTP_PASSWORD": "smtp-password",
    "STRICT_PASSWORD_BREACH_CHECK": "true",
    "SERVICE_APPLICATIONS": "sentio-b2b",
}


def _validate(monkeypatch, **overrides):
    """Rebuild AuthConfig under the given environment and validate it."""
    env = {**BASE_PRODUCTION_ENV, **overrides}
    for key in set(env) | {"AUTH_AUTHORITY_APPLICATIONS"}:
        # Set an empty string rather than deleting: auth.config calls load_env()
        # at import, so a deleted key would be refilled from the developer's
        # on-disk .env on reload and the "missing value" case would never occur.
        monkeypatch.setenv(key, env.get(key) or "")

    import auth.config as auth_config

    importlib.reload(auth_config)
    cfg = auth_config.AuthConfig()
    auth_config.validate_config(cfg)
    return cfg


@pytest.fixture(autouse=True)
def _restore_config_module():
    """Leave auth.config as the rest of the suite expects to find it."""
    yield
    import auth.config as auth_config

    importlib.reload(auth_config)


class TestProductionStartup:
    def test_valid_production_config_passes(self, monkeypatch):
        cfg = _validate(monkeypatch)
        assert cfg.FLASK_ENV == "production"
        assert cfg.SESSION_COOKIE_SECURE is True
        assert cfg.PREFERRED_URL_SCHEME == "https"
        assert cfg.ALLOWED_ORIGINS == ["https://product.sentiomind.in"]
        assert cfg.SERVICE_APPLICATIONS == ["sentio-b2b"]

    def test_authority_still_serves_both_applications(self, monkeypatch):
        """SERVICE_APPLICATIONS=sentio-b2b must not narrow the authority."""
        cfg = _validate(monkeypatch)
        assert set(cfg.AUTH_AUTHORITY_APPLICATIONS) == {"sentio-b2b", "sentio-mobile"}


class TestProductionRejects:
    def test_memory_rate_limit_storage(self, monkeypatch):
        with pytest.raises(RuntimeError, match="RATELIMIT_STORAGE_URI"):
            _validate(monkeypatch, RATELIMIT_STORAGE_URI="memory://")

    def test_localhost_rate_limit_storage(self, monkeypatch):
        with pytest.raises(RuntimeError, match="localhost"):
            _validate(monkeypatch, RATELIMIT_STORAGE_URI="redis://localhost:6379/1")

    def test_localhost_database(self, monkeypatch):
        """The production database is external to the Cloud Run container."""
        with pytest.raises(RuntimeError, match="localhost"):
            _validate(
                monkeypatch,
                SENTIO_DB_URL="postgresql://sentio:pw@localhost:5432/sentio_b2b",
            )

    def test_missing_database_url(self, monkeypatch):
        with pytest.raises(RuntimeError, match="SENTIO_DB_URL"):
            _validate(monkeypatch, SENTIO_DB_URL=None)

    def test_unencrypted_database_connection(self, monkeypatch):
        with pytest.raises(RuntimeError, match="SENTIO_DB_SSLMODE"):
            _validate(monkeypatch, SENTIO_DB_SSLMODE="disable")

    def test_wildcard_cors_origin(self, monkeypatch):
        with pytest.raises(RuntimeError, match=r"\*"):
            _validate(monkeypatch, ALLOWED_ORIGINS="*")

    def test_localhost_cors_origin(self, monkeypatch):
        with pytest.raises(RuntimeError, match="local origin"):
            _validate(
                monkeypatch,
                ALLOWED_ORIGINS="https://product.sentiomind.in,http://localhost:3000",
            )

    def test_plaintext_cors_origin(self, monkeypatch):
        with pytest.raises(RuntimeError, match="https"):
            _validate(monkeypatch, ALLOWED_ORIGINS="http://product.sentiomind.in")

    def test_missing_mfa_key(self, monkeypatch):
        with pytest.raises(RuntimeError, match="MFA_ENCRYPTION_KEY"):
            _validate(monkeypatch, MFA_ENCRYPTION_KEY=None)

    def test_missing_smtp_password(self, monkeypatch):
        with pytest.raises(RuntimeError, match="SMTP_PASSWORD"):
            _validate(monkeypatch, SMTP_PASSWORD=None)

    def test_breach_check_disabled(self, monkeypatch):
        with pytest.raises(RuntimeError, match="STRICT_PASSWORD_BREACH_CHECK"):
            _validate(monkeypatch, STRICT_PASSWORD_BREACH_CHECK="false")

    def test_short_jwt_secret(self, monkeypatch):
        with pytest.raises(RuntimeError, match="32 characters"):
            _validate(monkeypatch, JWT_SECRET_KEY="too-short")

    def test_unregistered_service_application(self, monkeypatch):
        with pytest.raises(RuntimeError, match="unregistered"):
            _validate(monkeypatch, SERVICE_APPLICATIONS="sentio-nope")


class TestGunicornBinding:
    def test_binds_all_interfaces_on_cloud_run_port(self, monkeypatch):
        """Cloud Run injects $PORT and requires 0.0.0.0; 127.0.0.1 fails startup."""
        monkeypatch.setenv("PORT", "8080")
        monkeypatch.delenv("GUNICORN_BIND", raising=False)
        monkeypatch.delenv("GUNICORN_BIND_HOST", raising=False)

        import gunicorn_config

        importlib.reload(gunicorn_config)
        assert gunicorn_config.bind == "0.0.0.0:8080"
        # Must drain inside Cloud Run's ~10s SIGTERM grace period.
        assert gunicorn_config.graceful_timeout <= 10

    def test_bind_host_is_overridable_for_nginx_deployments(self, monkeypatch):
        monkeypatch.setenv("PORT", "5000")
        monkeypatch.setenv("GUNICORN_BIND_HOST", "127.0.0.1")
        monkeypatch.delenv("GUNICORN_BIND", raising=False)

        import gunicorn_config

        importlib.reload(gunicorn_config)
        assert gunicorn_config.bind == "127.0.0.1:5000"
