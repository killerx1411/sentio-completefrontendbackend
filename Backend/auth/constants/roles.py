# ROLE_CONFIG: single source of truth for authorization scopes and permissions.
#
# Every role declares the application(s) whose tokens it may be issued for.
# Mobile Admin roles are FIRST-CLASS roles of this one authority — they are not
# aliases of the B2B admin tier and carry their own `mobile.*` permissions.
from auth.constants.applications import APP_B2B, APP_MOBILE

ROLE_CONFIG = {
    "Super Admin": {
        "scope": "GLOBAL",
        "applications": [APP_B2B],
        "permissions": [
            "users.read", "users.write", "users.delete", "users.approve",
            "roles.assign", "permissions.manage",
            "reports.read", "reports.write",
            "observations.write",
            "audit.read",
        ]
    },
    "Secondary Admin": {
        "scope": "GLOBAL",
        "applications": [APP_B2B],
        "permissions": ["users.read", "users.write", "reports.read"]
    },
    "Normal Admin": {
        "scope": "MONITORING",
        "applications": [APP_B2B],
        "permissions": ["users.read", "reports.read"]
    },
    "Principal": {
        "scope": "SCHOOL",
        "applications": [APP_B2B],
        "permissions": ["reports.read"]
    },
    "Psychologist": {
        "scope": "SCHOOL_FLAGGED",
        "applications": [APP_B2B],
        "permissions": ["reports.read"]
    },
    "Class Teacher": {
        "scope": "CLASS",
        "applications": [APP_B2B],
        "permissions": ["reports.read", "observations.write"]
    },
    "Behaviour Scientist": {
        "scope": "ANALYTICS",
        "applications": [APP_B2B],
        "permissions": ["reports.read"]
    },
    # --- Sentio Mobile Admin -------------------------------------------------
    # Distinct roles, distinct scopes, distinct permission namespace.
    # MOBILE_* scopes are deliberately unknown to the B2B row-level scope engine
    # (auth/services/authorization_service.py), so a Mobile token can never
    # widen into school/class data — it fails closed there.
    "mobile_super_admin": {
        "scope": "MOBILE_GLOBAL",
        "applications": [APP_MOBILE],
        "permissions": [
            "mobile.users.read", "mobile.users.write", "mobile.users.delete",
            "mobile.users.approve",
            "mobile.admins.manage",
            "mobile.content.read", "mobile.content.write",
            "mobile.reports.read",
            "mobile.settings.manage",
            "mobile.audit.read",
        ]
    },
    "mobile_secondary_admin": {
        "scope": "MOBILE_SUPPORT",
        "applications": [APP_MOBILE],
        "permissions": [
            "mobile.users.read", "mobile.users.write",
            "mobile.content.read", "mobile.content.write",
            "mobile.reports.read",
        ]
    },
}

ADMIN_ROLES = frozenset({"Super Admin", "Secondary Admin", "Normal Admin"})
EDUCATIONAL_ROLES = frozenset({"Principal", "Psychologist", "Class Teacher", "Behaviour Scientist"})
STAKEHOLDER_ROLES = tuple(EDUCATIONAL_ROLES)

MOBILE_ADMIN_ROLES = frozenset({"mobile_super_admin", "mobile_secondary_admin"})

# Admin-tier roles across every application. Assigning any of these is a
# privileged operation reserved for the B2B Super Admin.
PRIVILEGED_ROLES = ADMIN_ROLES | MOBILE_ADMIN_ROLES

ALL_ROLES = tuple(ROLE_CONFIG)


def applications_for_role(role_name: str | None) -> frozenset:
    """Applications a role may receive tokens for. Unknown role -> empty set."""
    cfg = ROLE_CONFIG.get(role_name or "")
    if not cfg:
        return frozenset()
    return frozenset(cfg.get("applications") or (APP_B2B,))


def role_allows_application(role_name: str | None, application: str | None) -> bool:
    return application in applications_for_role(role_name)


def roles_for_application(application: str) -> tuple:
    return tuple(
        name for name in ROLE_CONFIG if role_allows_application(name, application)
    )
