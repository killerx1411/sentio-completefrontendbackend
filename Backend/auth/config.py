import os

from auth.constants.applications import APPLICATIONS
from auth.constants.applications import DEFAULT_APPLICATION as _DEFAULT_APPLICATION
from auth.env_loader import load_env

load_env()

_DEFAULT_ORIGINS = "https://product.sentiomind.in"
_DEV_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def _default_allowed_origins() -> str:
    if os.environ.get("FLASK_ENV", "").lower() == "development":
        return _DEV_ORIGINS
    return _DEFAULT_ORIGINS


def _parse_allowed_origins() -> list:
    raw = os.environ.get("ALLOWED_ORIGINS", _default_allowed_origins())
    return [o.strip() for o in raw.split(",") if o.strip()]


def _parse_service_applications() -> list:
    """Applications whose access tokens THIS deployment will accept.

    The auth service itself serves every registered application by default
    (it is the one authority that mints all of them). A downstream deployment
    that only fronts one product narrows this via SERVICE_APPLICATIONS, e.g.
    ``SERVICE_APPLICATIONS=sentio-mobile``.
    """
    raw = os.environ.get("SERVICE_APPLICATIONS", "")
    if not raw.strip():
        return list(APPLICATIONS)
    return [a.strip().lower() for a in raw.split(",") if a.strip()]


def _parse_authority_applications() -> list:
    """Applications this deployment will MINT and identify tokens for.

    Distinct from ``SERVICE_APPLICATIONS``, which is the *resource server*
    boundary. https://b2bapi.sentiomind.in plays both parts: it is the one
    authentication authority for every product (so it must be able to log a
    Mobile Admin in and answer ``/api/auth/me`` and ``/api/auth/introspect``
    for a ``sentio-mobile`` token), while its B2B business routes accept only
    ``sentio-b2b`` tokens via ``SERVICE_APPLICATIONS=sentio-b2b``.

    Setting ``SERVICE_APPLICATIONS=sentio-b2b`` without this second dial would
    make the authority reject the very Mobile tokens it just minted, so the
    Mobile Admin pages of the B2B console could never resolve their session.

    Defaults to every registered application. Narrow it only on a deployment
    that is a pure resource server and mints nothing.
    """
    raw = os.environ.get("AUTH_AUTHORITY_APPLICATIONS", "")
    if not raw.strip():
        return list(APPLICATIONS)
    return [a.strip().lower() for a in raw.split(",") if a.strip()]


_LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")


def _is_local(value: str) -> bool:
    lowered = (value or "").lower()
    return any(host in lowered for host in _LOCAL_HOSTS)


def validate_config(cfg: "AuthConfig") -> None:
    """Raises RuntimeError if required security settings are missing or weak."""
    if not cfg.FLASK_ENV:
        raise RuntimeError("FLASK_ENV must be explicitly set")

    if cfg.FLASK_ENV != "test":
        if cfg.JWT_SECRET_KEY == "change-me-in-production":
            raise RuntimeError(
                "JWT_SECRET_KEY must be changed from the default"
            )

    if cfg.FLASK_ENV == "production":
        if not cfg.SMTP_PASSWORD:
            raise RuntimeError("SMTP_PASSWORD is required in production")
        if not cfg.STRICT_PASSWORD_BREACH_CHECK:
            raise RuntimeError(
                "STRICT_PASSWORD_BREACH_CHECK must be true in production"
            )
        if not cfg.MFA_ENCRYPTION_KEY:
            raise RuntimeError("MFA_ENCRYPTION_KEY is required in production")

        # Rate limiting must be backed by shared storage. `memory://` is
        # per-process and per-instance: on Cloud Run every revision instance and
        # every gunicorn worker would keep its own counters, so the configured
        # limits would silently not hold. Fail rather than pretend.
        storage = (cfg.RATELIMIT_STORAGE_URI or "").strip()
        if not storage.startswith(("redis://", "rediss://")):
            raise RuntimeError(
                "RATELIMIT_STORAGE_URI must be a redis:// or rediss:// URI in "
                f"production (got {storage.split('://')[0] or 'empty'}://…). "
                "memory:// does not rate-limit across workers or instances."
            )
        if _is_local(storage):
            raise RuntimeError(
                "RATELIMIT_STORAGE_URI points at localhost; production needs an "
                "external Redis/Upstash endpoint"
            )

        # The production database is external to the Cloud Run container; a
        # container-local PostgreSQL would be empty on every cold start.
        if not cfg.DATABASE_URL:
            raise RuntimeError("SENTIO_DB_URL is required in production")
        if not cfg.DATABASE_URL.lower().startswith("postgres"):
            raise RuntimeError("SENTIO_DB_URL must be a PostgreSQL URL")
        if _is_local(cfg.DATABASE_URL):
            raise RuntimeError(
                "SENTIO_DB_URL points at localhost; production must use the "
                "external managed PostgreSQL instance"
            )
        if cfg.DB_SSLMODE not in ("require", "verify-ca", "verify-full"):
            raise RuntimeError(
                "SENTIO_DB_SSLMODE must be require, verify-ca or verify-full in "
                f"production (got {cfg.DB_SSLMODE!r})"
            )

        # CORS: never a wildcard, never a development origin, always https.
        if not cfg.ALLOWED_ORIGINS:
            raise RuntimeError("ALLOWED_ORIGINS must be set in production")
        for origin in cfg.ALLOWED_ORIGINS:
            if origin == "*":
                raise RuntimeError("ALLOWED_ORIGINS must not contain '*' in production")
            if _is_local(origin):
                raise RuntimeError(
                    f"ALLOWED_ORIGINS must not contain a local origin in production: {origin}"
                )
            if not origin.startswith("https://"):
                raise RuntimeError(
                    f"ALLOWED_ORIGINS entries must be https in production: {origin}"
                )
        if not cfg.FRONTEND_URL.startswith("https://") or _is_local(cfg.FRONTEND_URL):
            raise RuntimeError("FRONTEND_URL must be an https non-local URL in production")

    unknown_authority = [
        a for a in cfg.AUTH_AUTHORITY_APPLICATIONS if a not in APPLICATIONS
    ]
    if unknown_authority:
        raise RuntimeError(
            "AUTH_AUTHORITY_APPLICATIONS contains unregistered applications: "
            + ", ".join(unknown_authority)
        )

    if len(cfg.JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters")

    unknown_apps = [a for a in cfg.SERVICE_APPLICATIONS if a not in APPLICATIONS]
    if unknown_apps:
        raise RuntimeError(
            "SERVICE_APPLICATIONS contains unregistered applications: "
            + ", ".join(unknown_apps)
        )
    if not cfg.SERVICE_APPLICATIONS:
        raise RuntimeError("SERVICE_APPLICATIONS must list at least one application")


class AuthConfig:
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
    SECRET_KEY = JWT_SECRET_KEY
    JWT_ACCESS_MINUTES = int(os.environ.get("JWT_ACCESS_MINUTES", 15))
    JWT_REFRESH_DAYS = int(os.environ.get("JWT_REFRESH_DAYS", 7))
    JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", 24))
    FLASK_ENV = os.environ.get("FLASK_ENV", "")
    ENV = FLASK_ENV
    PREFERRED_URL_SCHEME = os.environ.get(
        "PREFERRED_URL_SCHEME",
        "https" if os.environ.get("FLASK_ENV", "").lower() == "production" else "http",
    )

    # Rate limiting (Flask-Limiter)
    RATELIMIT_STORAGE_URI = os.environ.get(
        "RATELIMIT_STORAGE_URI", "redis://localhost:6379/1"
    )
    RATELIMIT_STRATEGY = "fixed-window-elastic-expiry"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = "200/minute"
    RATELIMIT_LOGIN = "10/minute;100/hour"
    RATELIMIT_REFRESH = "30/minute"
    RATELIMIT_LOGOUT = "20/minute"
    RATELIMIT_PASSWORD_RESET = "5/minute;10/hour"
    RATELIMIT_ANALYSIS = "60/minute"
    RATELIMIT_ADMIN = "120/minute"
    RATELIMIT_MFA_VERIFY = "5/minute"
    RATELIMIT_CSP_REPORT = "20/minute"
    RATELIMIT_SIGNUP = "5/minute;20/hour"
    RATELIMIT_REGISTER = "5/minute;20/hour"
    RATELIMIT_FORGOT_PASSWORD_GLOBAL = "30/hour"

    # Session / cookie security (secure cookies require HTTPS — off in development)
    SESSION_COOKIE_SECURE = FLASK_ENV == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = FLASK_ENV == "production"

    # HIBP
    STRICT_PASSWORD_BREACH_CHECK = (
        os.environ.get("STRICT_PASSWORD_BREACH_CHECK", "true").lower() == "true"
    )
    HIBP_TIMEOUT_SECONDS = int(os.environ.get("HIBP_TIMEOUT_SECONDS", 3))
    HIBP_CACHE_TTL_SECONDS = int(os.environ.get("HIBP_CACHE_TTL_SECONDS", 86400))

    # MFA encryption (Fernet derived from dedicated key or JWT secret)
    MFA_ENCRYPTION_KEY = os.environ.get("MFA_ENCRYPTION_KEY", "")

    DATABASE_URL = os.environ.get("SENTIO_DB_URL", "")
    # Mirrors auth/db_connection.py's default so validate_config() checks the
    # value the pool will actually connect with.
    DB_SSLMODE = os.environ.get("SENTIO_DB_SSLMODE", "require")
    FRONTEND_URL = os.environ.get(
        "FRONTEND_URL",
        "https://product.sentiomind.in"
        if FLASK_ENV == "production"
        else "http://localhost:3000",
    )
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    MAX_LOGIN_ATTEMPTS = int(os.environ.get("MAX_LOGIN_ATTEMPTS", 5))
    MAX_IP_LOGIN_ATTEMPTS = int(os.environ.get("MAX_IP_LOGIN_ATTEMPTS", 5))
    LOGIN_LOCKOUT_MINUTES = int(os.environ.get("LOGIN_LOCKOUT_MINUTES", 15))
    BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", 12))
    TEMP_PASSWORD_EXPIRY_HOURS = int(os.environ.get("TEMP_PASSWORD_EXPIRY_HOURS", 12))
    ALLOWED_ORIGINS = _parse_allowed_origins()

    # Multi-application (one authority, many consumers) — see
    # auth/constants/applications.py
    DEFAULT_APPLICATION = _DEFAULT_APPLICATION
    SERVICE_APPLICATIONS = _parse_service_applications()
    AUTH_AUTHORITY_APPLICATIONS = _parse_authority_applications()
    ENABLE_OPEN_REGISTRATION = (
        os.environ.get("ENABLE_OPEN_REGISTRATION", "false").lower() == "true"
    )

    @property
    def JWT_ACCESS_TOKEN_EXPIRES_MINUTES(self) -> int:
        return self.JWT_ACCESS_MINUTES


_config = None
_config_validated = False


def get_config() -> AuthConfig:
    global _config, _config_validated
    if _config is None:
        _config = AuthConfig()
    if not _config_validated:
        validate_config(_config)
        _config_validated = True
    return _config
