"""CV-specific configuration.

Separate from ``auth.config`` on purpose: the stakeholder/auth service must be
able to boot without any of these settings, and the CV system must not need
JWT/SMTP/MFA settings to run its pipeline offline.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _dir(env_name: str, default_name: str) -> Path:
    raw = os.environ.get(env_name)
    return Path(raw) if raw else PROJECT_ROOT / default_name


# ─── FILESYSTEM ───────────────────────────────────────────────────────────────
INPUT_VIDEOS_DIR = _dir("CV_INPUT_VIDEOS_DIR", "input_videos")
PROFILES_DIR = _dir("CV_PROFILES_DIR", "profiles")
SNAPSHOTS_DIR = _dir("CV_SNAPSHOTS_DIR", "snapshots")
ANALYSIS_DIR = _dir("CV_ANALYSIS_DIR", "analysis_results")

for _d in (INPUT_VIDEOS_DIR, PROFILES_DIR, SNAPSHOTS_DIR, ANALYSIS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

PERSON_DATABASE_FILE = PROFILES_DIR / "person_database.json"
MULTI_DAY_REPORT_FILE = ANALYSIS_DIR / "multi_day_report.json"

# ─── PIPELINE THRESHOLDS ──────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = float(os.environ.get("CV_SIMILARITY_THRESHOLD", "0.48"))
FRAME_DIFFERENCE_THRESHOLD = float(
    os.environ.get("CV_FRAME_DIFFERENCE_THRESHOLD", "0.15")
)

# ─── ROUTE LIMITS ─────────────────────────────────────────────────────────────
# Same default as the previous AuthConfig.RATELIMIT_ANALYSIS so behaviour is
# unchanged; it now lives with the routes it actually limits.
RATELIMIT_ANALYSIS = os.environ.get("CV_RATELIMIT_ANALYSIS", "60/minute")
MAX_IMAGE_BYTES = int(os.environ.get("CV_MAX_IMAGE_BYTES", str(2 * 1024 * 1024)))

# ─── DATABASE ─────────────────────────────────────────────────────────────────
# CV analysis rows (persons/videos/frames/analysis/traits) currently live in the
# same PostgreSQL instance as the auth schema and reuse the auth connection
# pool (see cv_analysis/db.py). Set CV_DATABASE_URL when the CV service is
# extracted so it can own its own pool without touching auth.
CV_DATABASE_URL = os.environ.get("CV_DATABASE_URL", "")
