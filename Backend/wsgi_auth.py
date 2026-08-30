"""WSGI entry point for the stakeholder/authentication service (no CV stack).

    gunicorn -c gunicorn_config.py wsgi_auth:app
    python wsgi_auth.py          # local dev on PORT (default 5001)

Importing this module must never pull in OpenCV, DeepFace, MediaPipe,
face_recognition or TensorFlow. ``tests/test_startup.py`` asserts that.
"""
from __future__ import annotations

import logging
import os

from app_factory import create_auth_app, run_auth_preflight

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = create_auth_app()

if __name__ == "__main__":
    run_auth_preflight(app)
    from auth.config import get_config

    debug_mode = get_config().FLASK_ENV == "development"
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
        debug=debug_mode,
        threaded=True,
    )
