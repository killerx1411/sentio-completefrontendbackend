"""Resource scope enforcement for IDOR prevention."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import wraps
from typing import Any

from flask import g, jsonify

from auth.constants.roles import ROLE_CONFIG
from auth.db_connection import get_db_connection, release_db_connection


@dataclass
class Student:
    """Minimal student/person resource for scope checks."""

    student_id: str
    school: str
    class_name: str | None = None
    flagged: bool = False
    school_id: int | None = None
    class_id: int | None = None


@dataclass
class User:
    """User context for authorization (from JWT + DB)."""

    id: int
    scope_type: str
    school_id: int | None = None
    class_id: int | None = None
    assigned_school: str | None = None
    assigned_class: str | None = None


def school_name_to_id(school: str | None) -> int | None:
    if not school:
        return None
    digest = hashlib.sha256(school.strip().lower().encode()).hexdigest()
    return int(digest[:8], 16)


def _load_user_scope(user_id: int) -> User:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT u.id, u.assigned_school, u.assigned_class, u.school_id, u.class_id,
                   ARRAY_AGG(r.name) AS roles
            FROM auth_enabler.users u
            LEFT JOIN auth_enabler.user_roles ur ON u.id = ur.user_id
            LEFT JOIN auth_enabler.roles r ON ur.role_id = r.id
            WHERE u.id = %s
            GROUP BY u.id
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            raise PermissionError("User not found")
        roles = row.get("roles") or []
        primary = roles[0] if roles else None
        scope = ROLE_CONFIG.get(primary, {}).get("scope", "GLOBAL") if primary else "GLOBAL"
        school_id = row.get("school_id") or school_name_to_id(row.get("assigned_school"))
        class_id = row.get("class_id") or (
            school_name_to_id(f"{row.get('assigned_school')}:{row.get('assigned_class')}")
            if row.get("assigned_class")
            else None
        )
        return User(
            id=int(row["id"]),
            scope_type=scope,
            school_id=school_id,
            class_id=class_id,
            assigned_school=row.get("assigned_school"),
            assigned_class=row.get("assigned_class"),
        )
    finally:
        release_db_connection(conn)


def user_from_jwt() -> User:
    payload = g.user
    user_id = int(payload["sub"])
    scope = payload.get("scope_type") or "GLOBAL"
    return User(
        id=user_id,
        scope_type=scope,
        school_id=payload.get("school_id"),
        class_id=payload.get("class_id"),
        assigned_school=payload.get("assigned_school"),
        assigned_class=payload.get("assigned_class"),
    )


def _forbidden():
    raise PermissionError("Forbidden: scope violation")


class AuthorizationService:
    @staticmethod
    def assert_school_scope(user: User, resource_school_id: int) -> None:
        if user.scope_type in ("GLOBAL", "MONITORING"):
            return
        if user.school_id is None:
            _forbidden()
        if user.school_id != resource_school_id:
            _forbidden()

    @staticmethod
    def assert_class_scope(user: User, resource_class_id: int) -> None:
        if user.scope_type in ("GLOBAL", "SCHOOL", "SCHOOL_FLAGGED", "ANALYTICS", "MONITORING"):
            return
        if user.scope_type == "CLASS":
            if user.class_id is None or user.class_id != resource_class_id:
                _forbidden()
            return
        _forbidden()

    @staticmethod
    def assert_flagged_only(user: User, student: Student) -> None:
        if user.scope_type != "SCHOOL_FLAGGED":
            return
        if not student.flagged:
            _forbidden()

    @staticmethod
    def get_school_filter(user: User) -> int | None:
        if user.scope_type in ("GLOBAL", "MONITORING"):
            return None
        return user.school_id

    @staticmethod
    def get_class_filter(user: User) -> int | None:
        if user.scope_type == "CLASS":
            return user.class_id
        return None

    @staticmethod
    def assert_person_access(user: User, person: dict[str, Any]) -> None:
        student = Student(
            student_id=person.get("person_id") or person.get("student_id", ""),
            school=person.get("school", ""),
            class_name=person.get("class_name"),
            flagged=bool(person.get("flagged", person.get("average_wellbeing", 100) < 40)),
            school_id=school_name_to_id(person.get("school")),
            class_id=school_name_to_id(
                f"{person.get('school')}:{person.get('class_name')}"
            )
            if person.get("class_name")
            else None,
        )
        if student.school_id is not None:
            AuthorizationService.assert_school_scope(user, student.school_id)
        if user.scope_type == "CLASS" and student.class_id is not None:
            AuthorizationService.assert_class_scope(user, student.class_id)
        AuthorizationService.assert_flagged_only(user, student)


def scope_required(scope: str):
    """Decorator requiring JWT user scope_type to match."""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                user = user_from_jwt()
                if user.scope_type != scope and scope not in ("GLOBAL",):
                    if scope == "SCHOOL" and user.scope_type not in (
                        "SCHOOL",
                        "SCHOOL_FLAGGED",
                        "CLASS",
                        "ANALYTICS",
                    ):
                        return jsonify({"error": "forbidden", "message": "Insufficient scope"}), 403
                    elif scope not in (user.scope_type,):
                        if user.scope_type not in ("GLOBAL", "MONITORING"):
                            return jsonify({"error": "forbidden", "message": "Insufficient scope"}), 403
            except PermissionError:
                return jsonify({"error": "forbidden"}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


def require_person_scope(person_loader):
    """Decorator: load person dict, enforce scope, pass to view."""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                user = _load_user_scope(int(g.user["sub"]))
                person = person_loader(**kwargs)
                if person:
                    AuthorizationService.assert_person_access(user, person)
            except PermissionError:
                return jsonify({"error": "forbidden", "message": "Access denied"}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator
