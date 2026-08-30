"""Standalone CV / analysis service.

Lets the CV system run as its own process today, ahead of any real extraction:

    gunicorn -c gunicorn_config.py cv_analysis.app:app
    python -m cv_analysis.app

It authenticates and authorizes with the *existing* stakeholder auth stack
(``auth.middleware``) reading the same JWTs and the same PostgreSQL permission
tables — deliberately no second JWT implementation, user store or role system.
That is the CV -> Auth dependency documented in ``cv_analysis/README.md``.
"""
from __future__ import annotations

import logging
import os

from flask import Flask
from flask_cors import CORS

from auth.env_loader import load_env

load_env()

from auth.config import get_config
from auth.middleware.rate_limiter import init_rate_limiter
from common.http import CORS_ALLOW_HEADERS, apply_proxy_fix, apply_security_headers
from cv_analysis.routes import register_cv_blueprints

logger = logging.getLogger(__name__)


def create_cv_app(testing: bool = False) -> Flask:
    flask_app = Flask(__name__)
    cfg = get_config()
    flask_app.config.from_object(cfg)
    if testing:
        flask_app.config.update(
            {"TESTING": True, "RATELIMIT_STORAGE_URI": "memory://", "ENV": "test"}
        )

    CORS(
        flask_app,
        origins=cfg.ALLOWED_ORIGINS,
        supports_credentials=True,
        allow_headers=CORS_ALLOW_HEADERS,
    )
    init_rate_limiter(flask_app)
    apply_proxy_fix(flask_app)
    register_cv_blueprints(flask_app)

    @flask_app.after_request
    def _security_headers(response):
        return apply_security_headers(response)

    return flask_app


app = create_cv_app()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    from cv_analysis.config import ANALYSIS_DIR, INPUT_VIDEOS_DIR
    from cv_analysis.libraries import library_status

    logger.info("Sentio CV / analysis service | libraries=%s", library_status())
    logger.info("Input: %s | Output: %s", INPUT_VIDEOS_DIR, ANALYSIS_DIR)
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("CV_PORT", 5002)),
        debug=get_config().FLASK_ENV == "development",
        threaded=True,
    )
