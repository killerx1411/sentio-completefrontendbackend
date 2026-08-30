"""The stakeholder/auth service must not depend on the CV stack.

These are the regression tests for the CV/auth separation: if someone
reintroduces an ``import cv2`` (or a ``cv_analysis`` import) anywhere the auth
service reaches, one of these fails.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

CV_MODULES = ("cv2", "deepface", "mediapipe", "face_recognition", "mtcnn", "tensorflow")

_CHILD_ENV_SNIPPET = """
import os, sys
os.environ.setdefault("JWT_SECRET_KEY", "a" * 32)
os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("MFA_ENCRYPTION_KEY", "test-mfa-encryption-key-32chars!!")
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")
os.environ.setdefault("STRICT_PASSWORD_BREACH_CHECK", "false")
"""


def _run_child(body: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD_ENV_SNIPPET + body],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip().splitlines()[-1]


class TestServiceBoundary:
    def test_auth_app_starts_without_cv_libraries(self):
        """create_auth_app() must not import a single CV library."""
        loaded = _run_child(
            """
from app_factory import create_auth_app
app = create_auth_app(testing=True)
top = {m.split(".")[0] for m in sys.modules}
print(sorted(top & set(%r)))
"""
            % (CV_MODULES,)
        )
        assert loaded == "[]"

    def test_auth_app_serves_health_without_cv_stack(self):
        status = _run_child(
            """
from app_factory import create_auth_app
resp = create_auth_app(testing=True).test_client().get("/health")
print(resp.status_code)
"""
        )
        assert status == "200"

    def test_auth_app_registers_no_cv_routes(self):
        from app_factory import create_auth_app

        rules = {str(r.rule) for r in create_auth_app(testing=True).url_map.iter_rules()}
        for cv_rule in (
            "/run_analysis",
            "/get_report",
            "/pin_profile",
            "/update_person_name",
            "/update_person_photo",
            "/delete_person",
            "/system_info",
            "/analysis/report",
            "/person/<person_id>",
        ):
            assert cv_rule not in rules

    @pytest.mark.parametrize("package", ["auth", "common"])
    def test_no_cv_imports_inside_shared_packages(self, package):
        """auth/ and common/ must never import cv_analysis or a CV library."""
        offenders = []
        for path in (BACKEND_DIR / package).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped.startswith(("import ", "from ")):
                    continue
                if "cv_analysis" in stripped or any(
                    stripped.startswith(f"import {m}")
                    or stripped.startswith(f"from {m}")
                    for m in CV_MODULES + ("numpy",)
                ):
                    offenders.append(f"{path.relative_to(BACKEND_DIR)}: {stripped}")
        assert offenders == []
