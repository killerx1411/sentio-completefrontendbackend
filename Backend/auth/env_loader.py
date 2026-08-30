"""Load Backend env: `.env` first, then `.env.local` overrides for local dev.

In production nothing is loaded from disk. Cloud Run injects configuration as
real environment variables (plain vars plus Secret Manager references), and
`.env` / `.env.local` are excluded from the image by .dockerignore — but a
developer-machine `.env.local` silently overriding a production secret is
exactly the failure this guard exists to prevent, so the override file is
skipped outright whenever FLASK_ENV=production.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parents[1]


def load_env() -> None:
    # Read the REAL environment before any file touches it. The committed .env
    # may itself say FLASK_ENV=production, so deciding after loading it would
    # skip .env.local on developer machines and break local dev.
    deployed = os.environ.get("FLASK_ENV", "").strip().lower() == "production"

    # override=False throughout: a real environment variable (Cloud Run, the
    # shell, CI) always beats a file.
    load_dotenv(_BACKEND_DIR / ".env", override=False)
    if deployed:
        return
    load_dotenv(_BACKEND_DIR / ".env.local", override=True)
