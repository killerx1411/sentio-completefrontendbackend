"""Seed a Principal user that can log in to the B2B app immediately.

Usage:
    python -m auth.db.seed_principal [--email EMAIL] [--name NAME] [--password PW]

Omitting --password generates a strong random one and prints it once. The user
is created already approved (status=active, registration_status=APPROVED,
is_first_login=FALSE) so no first-login password change is required.
"""
import argparse
import secrets
import string
import sys

from auth.db_connection import db_cursor
from auth.helpers.password_helper import hash_password, validate_password_strength

ROLE_NAME = "Principal"

_UPPER = string.ascii_uppercase
_LOWER = string.ascii_lowercase
_DIGITS = string.digits
_SPECIAL = "!@#$%^&*?"


def generate_password(length: int = 16) -> str:
    """Random password that satisfies validate_password_strength()."""
    alphabet = _UPPER + _LOWER + _DIGITS + _SPECIAL
    while True:
        chars = [
            secrets.choice(_UPPER),
            secrets.choice(_LOWER),
            secrets.choice(_DIGITS),
            secrets.choice(_SPECIAL),
        ]
        chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
        secrets.SystemRandom().shuffle(chars)
        candidate = "".join(chars)
        ok, _ = validate_password_strength(candidate)
        if ok:
            return candidate


def seed_principal(email: str, full_name: str, password: str, organization: str) -> None:
    password_hash = hash_password(password)
    with db_cursor() as cur:
        cur.execute(
            "SELECT id FROM auth_enabler.roles WHERE name = %s", (ROLE_NAME,)
        )
        role = cur.fetchone()
        if not role:
            raise SystemExit(
                f"Role {ROLE_NAME!r} missing. Run auth/db/seed.sql first."
            )
        role_id = role["id"]

        cur.execute(
            """
            INSERT INTO auth_enabler.users (
                full_name, email, password_hash, status, registration_status,
                is_first_login, organization, requested_role, approved_at
            )
            VALUES (%s, %s, %s, 'active', 'APPROVED', FALSE, %s, %s, NOW())
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                full_name = EXCLUDED.full_name,
                status = 'active',
                registration_status = 'APPROVED',
                is_first_login = FALSE,
                approved_at = NOW()
            RETURNING id;
            """,
            (full_name, email, password_hash, organization, ROLE_NAME),
        )
        user_id = cur.fetchone()["id"]

        cur.execute(
            """
            INSERT INTO auth_enabler.user_roles (user_id, role_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, role_id) DO NOTHING;
            """,
            (user_id, role_id),
        )
    print(f"Seeded {ROLE_NAME} user id={user_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a Principal user.")
    parser.add_argument("--email", default="principal@sentiomind.in")
    parser.add_argument("--name", default="Test Principal")
    parser.add_argument("--password", default=None)
    parser.add_argument("--organization", default="Sentio Demo School")
    args = parser.parse_args()

    password = args.password or generate_password()
    ok, reason = validate_password_strength(password)
    if not ok:
        print(f"Password rejected: {reason}", file=sys.stderr)
        return 1

    seed_principal(args.email, args.name, password, args.organization)
    print("-" * 52)
    print(f"  email:    {args.email}")
    print(f"  password: {password}")
    print("-" * 52)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
