"""Production startup security validation."""

from __future__ import annotations

import logging
import os

from flask import Flask

from auth.config import get_config
from auth.helpers.audit_helper import log_activity

logger = logging.getLogger(__name__)


def run_startup_checks(app: Flask) -> None:
    """Assert critical security settings in production."""
    cfg = get_config()
    env = app.config.get("ENV") or cfg.FLASK_ENV

    if env != "test":
        if cfg.JWT_SECRET_KEY == "change-me-in-production":
            raise RuntimeError(
                "JWT_SECRET_KEY must be changed from the default"
            )
        if not os.getenv("MFA_ENCRYPTION_KEY"):
            raise RuntimeError("MFA_ENCRYPTION_KEY must be set")

    if env != "production":
        return

    if not app.config.get("SESSION_COOKIE_SECURE", True):
        raise RuntimeError("SESSION_COOKIE_SECURE must be True in production")

    if app.config.get("PREFERRED_URL_SCHEME") != "https":
        raise RuntimeError("PREFERRED_URL_SCHEME must be https in production")

    secret = app.config.get("SECRET_KEY") or cfg.JWT_SECRET_KEY
    if not secret or len(secret) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production")

    db_url = (app.config.get("DATABASE_URL") or cfg.DATABASE_URL or "").lower()
    if db_url and not db_url.startswith("postgresql"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL in production")

    if app.config.get("DEBUG"):
        raise RuntimeError("DEBUG must be disabled in production")

    storage = str(app.config.get("RATELIMIT_STORAGE_URI") or "")
    if not storage.startswith(("redis://", "rediss://")):
        raise RuntimeError(
            "RATELIMIT_STORAGE_URI must be redis:// or rediss:// in production"
        )

    # The audit row is a nice-to-have; a cold database must not stop a Cloud Run
    # instance from coming up, and the checks above have already passed.
    try:
        log_activity(
            None,
            "startup_security_checks_passed",
            "Security",
            "Production startup checks passed",
            severity="INFO",
        )
    except Exception as exc:  # noqa: BLE001 - audit is best effort at boot
        logger.warning("Could not write startup audit entry: %s", exc)
    logger.info("Production startup security checks passed")
