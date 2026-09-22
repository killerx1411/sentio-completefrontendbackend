"""Create the first Sentio Mobile Admin operator.

`seed.sql` deliberately seeds no admin user (SEC-003: never commit a known
password hash). This is the secure-channel alternative it points at -- the
password is generated here, printed once, and never written to a file or to
version control.

Idempotent on the email: re-running promotes the existing account and, unless
--reset-password is passed, leaves its password alone.

    python -m auth.db.bootstrap_mobile_admin --email you@sentiomind.in
    python -m auth.db.bootstrap_mobile_admin --email you@sentiomind.in --role mobile_secondary_admin

Assigning these roles is privileged (PRIVILEGED_ROLES), so there is no API path
to the *first* one -- somebody has to hold it before they can grant it. That is
what this script is for, and why it runs against the database directly.
"""

import argparse
import os
import secrets
import string
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import bcrypt

from auth.constants.roles import MOBILE_ADMIN_ROLES
from auth.db_connection import get_db_connection

ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*-_"


def _id(row):
    """get_db_connection() hands back dict rows; tolerate tuples too."""
    return row["id"] if isinstance(row, dict) else row[0]


def generate_password(length: int = 20) -> str:
    """A password the operator changes at first sign-in, not one they keep."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def run(email: str, full_name: str, role: str, reset_password: bool) -> None:
    if role not in MOBILE_ADMIN_ROLES:
        print(
            f"Refusing: '{role}' is not a Mobile Admin role. "
            f"Choose one of {', '.join(sorted(MOBILE_ADMIN_ROLES))}.",
            file=sys.stderr,
        )
        sys.exit(1)

    conn = get_db_connection()
    password = None
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM auth_enabler.roles WHERE name = %s;", (role,)
        )
        row = cur.fetchone()
        if row is None:
            print(
                f"Refusing: role '{role}' is not in the database. "
                "Run auth/db/seed.sql and python -m auth.db.migrate_mobile_admin first.",
                file=sys.stderr,
            )
            sys.exit(1)
        role_id = _id(row)

        cur.execute("SELECT id FROM auth_enabler.users WHERE email = %s;", (email,))
        existing = cur.fetchone()

        rounds = int(os.environ.get("BCRYPT_ROUNDS", "12"))
        if existing is None or reset_password:
            password = generate_password()
            password_hash = bcrypt.hashpw(
                password.encode(), bcrypt.gensalt(rounds)
            ).decode()

        if existing is None:
            cur.execute(
                """
                INSERT INTO auth_enabler.users
                    (full_name, email, password_hash, status, registration_status,
                     is_first_login, mfa_enabled, terms_accepted_at, approved_at)
                VALUES (%s, %s, %s, 'active', 'APPROVED', false, false, NOW(), NOW())
                RETURNING id;
                """,
                (full_name, email, password_hash),
            )
            user_id = _id(cur.fetchone())
            action = "created"
        else:
            user_id = _id(existing)
            # An account that exists but was never approved cannot sign in, so
            # promoting it has to clear those gates too.
            cur.execute(
                """
                UPDATE auth_enabler.users
                   SET status = 'active',
                       registration_status = 'APPROVED',
                       is_first_login = false,
                       approved_at = COALESCE(approved_at, NOW()),
                       terms_accepted_at = COALESCE(terms_accepted_at, NOW()),
                       password_hash = COALESCE(%s, password_hash)
                 WHERE id = %s;
                """,
                (password_hash if password else None, user_id),
            )
            action = "updated"

        cur.execute(
            """
            INSERT INTO auth_enabler.user_roles (user_id, role_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (user_id, role_id),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"Mobile Admin {action}: {email} (id={user_id}) with role '{role}'.")
    if password:
        print()
        print("  Password (shown once, not stored anywhere else):")
        print(f"      {password}")
        print()
        print("  Sign in at the console with application 'sentio-mobile'.")
    else:
        print("Password left unchanged. Pass --reset-password to issue a new one.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Mobile Administrator")
    parser.add_argument("--role", default="mobile_super_admin")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Issue a new password for an account that already exists.",
    )
    args = parser.parse_args()
    run(args.email, args.name, args.role, args.reset_password)


if __name__ == "__main__":
    main()
