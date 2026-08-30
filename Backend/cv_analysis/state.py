"""In-process CV state shared between the pipeline and the CV routes.

These objects are mutated in place (never rebound), so importing them by name
from either module keeps a single shared instance — matching the previous
module-global behaviour in ``test_db.py``.
"""
from __future__ import annotations

import threading

person_database: dict = {}
analysis_cache: dict = {}
pinned_profiles: set = set()

_db_lock = threading.Lock()
