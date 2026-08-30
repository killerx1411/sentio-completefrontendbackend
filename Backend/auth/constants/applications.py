"""Registered consumer applications of the single authentication authority.

The ``auth`` package is the ONE authentication authority. Every product that
authenticates against it (the B2B / stakeholder web product, the Sentio Mobile
Admin backend, …) is registered here as an *application*.

An application is a token audience boundary, not a second auth system:

* login issues one access token bound to exactly one application (``app`` claim
  plus a per-application JWT ``aud``),
* a resource server only accepts tokens minted for the application it serves,
* role -> application entitlement is declared in ``auth.constants.roles``.

Adding a product means adding an entry here plus role entitlements — never a
second JWT/login/user/refresh/MFA/RBAC implementation.
"""

APP_B2B = "sentio-b2b"
APP_MOBILE = "sentio-mobile"

# NOTE: the B2B audience keeps its historical value so tokens already in flight
# and existing resource servers keep validating unchanged.
APPLICATIONS: dict[str, dict[str, str]] = {
    APP_B2B: {
        "audience": "sentio-mind-api",
        "label": "Sentio B2B / Stakeholder platform",
    },
    APP_MOBILE: {
        "audience": "sentio-mobile-api",
        "label": "Sentio Mobile Admin",
    },
}

DEFAULT_APPLICATION = APP_B2B

KNOWN_APPLICATIONS = frozenset(APPLICATIONS)
KNOWN_AUDIENCES = [cfg["audience"] for cfg in APPLICATIONS.values()]

_AUDIENCE_TO_APPLICATION = {
    cfg["audience"]: name for name, cfg in APPLICATIONS.items()
}


def is_known_application(application: str | None) -> bool:
    return application in APPLICATIONS


def normalize_application(application: str | None) -> str | None:
    """Return the canonical application id, or ``None`` if unknown.

    An empty/missing value resolves to :data:`DEFAULT_APPLICATION` so legacy
    clients that predate the application claim keep working.
    """
    if application is None or application == "":
        return DEFAULT_APPLICATION
    value = str(application).strip().lower()
    return value if value in APPLICATIONS else None


def audience_for(application: str | None) -> str:
    return APPLICATIONS[application or DEFAULT_APPLICATION]["audience"]


def application_for_audience(audience) -> str | None:
    """Map a JWT ``aud`` claim (string or list) back to an application id."""
    if isinstance(audience, (list, tuple, set)):
        for aud in audience:
            app = _AUDIENCE_TO_APPLICATION.get(aud)
            if app:
                return app
        return None
    return _AUDIENCE_TO_APPLICATION.get(audience)


def label_for(application: str | None) -> str:
    cfg = APPLICATIONS.get(application or DEFAULT_APPLICATION)
    return cfg["label"] if cfg else str(application)
