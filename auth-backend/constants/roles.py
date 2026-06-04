# ROLE_CONFIG: single source of truth for authorization scopes and permissions
ROLE_CONFIG = {
    "Super Admin": {
        "scope": "GLOBAL",
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
        "permissions": ["users.read", "users.write", "reports.read"]
    },
    "Normal Admin": {
        "scope": "MONITORING",
        "permissions": ["users.read", "reports.read"]
    },
    "Principal": {
        "scope": "SCHOOL",
        "permissions": ["reports.read"]
    },
    "Psychologist": {
        "scope": "SCHOOL_FLAGGED",
        "permissions": ["reports.read"]
    },
    "Class Teacher": {
        "scope": "CLASS",
        "permissions": ["reports.read", "observations.write"]
    },
    "Behaviour Scientist": {
        "scope": "ANALYTICS",
        "permissions": ["reports.read"]
    }
}

ADMIN_ROLES = frozenset({"Super Admin", "Secondary Admin", "Normal Admin"})
EDUCATIONAL_ROLES = frozenset({"Principal", "Psychologist", "Class Teacher", "Behaviour Scientist"})
