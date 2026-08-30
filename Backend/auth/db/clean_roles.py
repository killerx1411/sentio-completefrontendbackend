import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.constants.roles import ROLE_CONFIG
from auth.db.migrate_mobile_admin import PERMISSION_META, ROLE_DESCRIPTIONS
from auth.db_connection import get_db_connection


def clean_and_reorder_roles():
    print("Connecting to database for soft seeding roles & permissions...")
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        print("Upserting standardized roles (B2B + Sentio Mobile Admin)...")
        roles_data = [
            ("Super Admin", "Super administrator with system-wide controls."),
            ("Secondary Admin", "Secondary administrator for user operations."),
            ("Normal Admin", "Operational/support administrative role with read-only view."),
            ("Principal", "School principal with read-only access."),
            ("Psychologist", "School psychologist with read-only access."),
            ("Class Teacher", "Classroom teacher with student management access."),
            ("Behaviour Scientist", "Analytical role."),
        ] + [(name, desc) for name, desc in ROLE_DESCRIPTIONS.items()]

        role_ids = {}
        for r_name, r_desc in roles_data:
            cur.execute(
                """
                INSERT INTO auth_enabler.roles (name, description)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                RETURNING id;
                """,
                (r_name, r_desc),
            )
            role_ids[r_name] = cur.fetchone()["id"]

        print("Migrating user roles mapping...")
        if "Secondary Admin" in role_ids:
            cur.execute(
                """
                UPDATE auth_enabler.user_roles
                SET role_id = %s
                WHERE role_id IN (SELECT id FROM auth_enabler.roles WHERE name IN ('Admin', 'Secondary Admin'));
                """,
                (role_ids["Secondary Admin"],),
            )

        if "Class Teacher" in role_ids:
            cur.execute(
                """
                UPDATE auth_enabler.user_roles
                SET role_id = %s
                WHERE role_id IN (SELECT id FROM auth_enabler.roles WHERE name = 'Teacher');
                """,
                (role_ids["Class Teacher"],),
            )

        cur.execute(
            """
            DELETE FROM auth_enabler.user_roles
            WHERE role_id IN (SELECT id FROM auth_enabler.roles WHERE name = 'Sentio Mind');
            """
        )

        print("Removing deprecated roles...")
        cur.execute(
            "DELETE FROM auth_enabler.roles WHERE name IN ('Teacher', 'Sentio Mind', 'Admin');"
        )

        print("Upserting standardized permissions...")
        permissions_data = [
            ("users.read", "Users", "READ", "View list of users and detail profiles"),
            ("users.write", "Users", "CREATE", "Create and edit user profiles"),
            ("users.delete", "Users", "DELETE", "Permanently delete user profiles"),
            ("users.approve", "Users", "APPROVE", "Approve or reject pending user registrations"),
            ("roles.assign", "Roles", "ASSIGN", "Assign roles to user profiles"),
            ("permissions.manage", "Permissions", "ALL", "Manage permissions and RBAC policies"),
            ("reports.read", "Reports", "READ", "View platform reports and analytics"),
            ("reports.write", "Reports", "WRITE", "Create and edit reports and analytics exports"),
            ("observations.write", "Observations", "WRITE", "Write student observations"),
            ("audit.read", "Audit Logs", "READ", "View platform compliance and security logs"),
        ] + [
            # Sentio Mobile Admin namespace — must be listed here too, or the
            # "remove deprecated permissions" delete below would wipe it.
            (name, module, action, description)
            for name, (module, action, description) in PERMISSION_META.items()
        ]

        perm_ids = {}
        for p_name, p_mod, p_act, p_desc in permissions_data:
            cur.execute(
                """
                INSERT INTO auth_enabler.permissions (name, module, action, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    module = EXCLUDED.module,
                    action = EXCLUDED.action
                RETURNING id;
                """,
                (p_name, p_mod, p_act, p_desc),
            )
            perm_ids[p_name] = cur.fetchone()["id"]

        print("Removing deprecated permissions...")
        valid_perms = list(perm_ids.keys())
        cur.execute(
            "DELETE FROM auth_enabler.permissions WHERE name NOT IN %s;",
            (tuple(valid_perms),),
        )

        print("Re-mapping permissions to roles based on ROLE_CONFIG...")
        cur.execute("DELETE FROM auth_enabler.role_permissions;")

        for role_name, config in ROLE_CONFIG.items():
            r_id = role_ids.get(role_name)
            if not r_id:
                cur.execute(
                    "SELECT id FROM auth_enabler.roles WHERE name = %s;", (role_name,)
                )
                row = cur.fetchone()
                if row:
                    r_id = row["id"]
                    role_ids[role_name] = r_id
            if not r_id:
                continue
            for perm_name in config["permissions"]:
                p_id = perm_ids.get(perm_name)
                if p_id:
                    cur.execute(
                        """
                        INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                        """,
                        (r_id, p_id),
                    )

        conn.commit()
        print("Database roles soft-seeding completed successfully!")

        cur.close()
        conn.close()
    except Exception as e:
        conn.rollback()
        print(f"Error during soft-seeding cleanup: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    clean_and_reorder_roles()
