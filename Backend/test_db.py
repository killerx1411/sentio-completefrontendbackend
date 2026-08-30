"""Combined deployment entry point: stakeholder/auth service + CV system.

Historical name, kept because ``gunicorn -c gunicorn_config.py test_db:app``,
the nginx config and the existing tests all reference it. It is now a thin
composition layer with no logic of its own:

    app = create_auth_app()      # auth/RBAC/audit/security — zero CV imports
    register_cv_blueprints(app)  # CV routes, mounted on the same process

The two systems it composes are independently runnable:

    gunicorn -c gunicorn_config.py wsgi_auth:app        # stakeholder/auth only
    gunicorn -c gunicorn_config.py cv_analysis.app:app  # CV/analysis only

``create_app(testing=True)`` still returns the slim auth/API app used by the
pytest suite; it does not touch the CV stack.
"""
from __future__ import annotations

import logging
import os

from flask import Flask

from app_factory import create_auth_app, run_auth_preflight

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = create_auth_app()

# CV system mounted onto the same app. This import — and only this import —
# pulls in OpenCV/DeepFace/MediaPipe/MTCNN.
from cv_analysis.routes import register_cv_blueprints  # noqa: E402
from cv_analysis.state import (  # noqa: E402,F401  (re-exported for tests/tools)
    analysis_cache,
    person_database,
    pinned_profiles,
)

register_cv_blueprints(app)


def create_app(testing: bool = False) -> Flask:
    """Auth/API test factory. When ``testing`` is false, returns this module's ``app``."""
    if not testing:
        return app
    return create_auth_app(testing=True)


def pre_flight_check() -> None:
    run_auth_preflight(app)


if __name__ == "__main__":
    from cv_analysis.config import ANALYSIS_DIR, INPUT_VIDEOS_DIR
    from cv_analysis.libraries import library_status

    pre_flight_check()
    logger.info("Sentio Mind — Behavioral Intelligence Platform v2.0 (combined)")
    logger.info("CV libraries | %s", library_status())
    logger.info("Input: %s | Output: %s", INPUT_VIDEOS_DIR, ANALYSIS_DIR)
    from auth.config import get_config

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
        debug=get_config().FLASK_ENV == "development",
        threaded=True,
    )
