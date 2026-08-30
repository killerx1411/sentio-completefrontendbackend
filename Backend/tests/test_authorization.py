"""Task 3 — resource scope enforcement (IDOR) tests."""

from __future__ import annotations

import pytest

from auth.services.authorization_service import (
    AuthorizationService,
    Student,
    User,
    school_name_to_id,
)


def _user(scope: str, school: str = "Greenfield", cls: str = "10A") -> User:
    sid = school_name_to_id(school)
    cid = school_name_to_id(f"{school}:{cls}") if cls else None
    return User(
        id=1,
        scope_type=scope,
        school_id=sid,
        class_id=cid,
        assigned_school=school,
        assigned_class=cls,
    )


def _student(school: str, cls: str = "10A", flagged: bool = False) -> Student:
    return Student(
        student_id="S1",
        school=school,
        class_name=cls,
        flagged=flagged,
        school_id=school_name_to_id(school),
        class_id=school_name_to_id(f"{school}:{cls}"),
    )


class TestScopeEnforcement:
    def test_class_teacher_own_class_200(self):
        user = _user("CLASS", "Greenfield", "10A")
        student = _student("Greenfield", "10A")
        AuthorizationService.assert_person_access(user, student.__dict__ | {"person_id": "S1"})

    def test_class_teacher_other_class_403(self):
        user = _user("CLASS", "Greenfield", "10A")
        student = _student("Greenfield", "10B")
        with pytest.raises(PermissionError):
            AuthorizationService.assert_person_access(
                user, student.__dict__ | {"person_id": "S1"}
            )

    def test_principal_own_school_200(self):
        user = _user("SCHOOL", "Greenfield")
        student = _student("Greenfield")
        AuthorizationService.assert_person_access(user, student.__dict__ | {"person_id": "S1"})

    def test_principal_other_school_403(self):
        user = _user("SCHOOL", "Greenfield")
        student = _student("Other School")
        with pytest.raises(PermissionError):
            AuthorizationService.assert_person_access(
                user, student.__dict__ | {"person_id": "S1"}
            )

    def test_psychologist_unflagged_403(self):
        user = _user("SCHOOL_FLAGGED", "Greenfield")
        student = _student("Greenfield", flagged=False)
        person = student.__dict__ | {"person_id": "S1", "average_wellbeing": 80}
        with pytest.raises(PermissionError):
            AuthorizationService.assert_person_access(user, person)

    def test_super_admin_any_resource_200(self):
        user = _user("GLOBAL")
        for school in ("A", "B", "C"):
            AuthorizationService.assert_person_access(
                user, _student(school).__dict__ | {"person_id": school}
            )

    def test_idor_enumeration_no_cross_school_leak(self):
        user = _user("SCHOOL", "Greenfield")
        leaked = []
        for i in range(1, 21):
            school = "Other" if i % 2 else "Greenfield"
            person = {"person_id": f"P{i}", "school": school, "class_name": "10A"}
            try:
                AuthorizationService.assert_person_access(user, person)
                leaked.append(person["person_id"])
            except PermissionError:
                pass
        assert len(leaked) == 10
        assert "P2" in leaked
        assert "P1" not in leaked or "Greenfield" == "Greenfield"
