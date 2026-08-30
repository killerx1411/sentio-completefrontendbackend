# Sentio Mobile Admin — integrating with the authentication authority

The `auth/` package is the **one** authentication authority for every Sentio
product. Sentio Mobile Admin does not get its own login, JWT, user table,
password store, refresh-token rotation, MFA or RBAC engine. It becomes another
**authorized consumer** of this one.

This document is the contract between the two backends. The CV /
behavioural-intelligence system (`cv_analysis/`) is not involved and is
unchanged — see `ARCHITECTURE_SEPARATION.md`.

---

## 1. The one new concept: applications

An **application** is a token-audience boundary, registered in
`auth/constants/applications.py`:

| id | JWT `aud` | Consumer |
|---|---|---|
| `sentio-b2b` | `sentio-mind-api` | B2B / stakeholder web product (default; unchanged) |
| `sentio-mobile` | `sentio-mobile-api` | Sentio Mobile Admin backend |

Rules the auth layer now enforces:

1. Login mints **one** access token bound to **one** application (`app` claim +
   that application's `aud`).
2. A role may only be issued a token for the applications it declares
   (`ROLE_CONFIG[role]["applications"]`).
3. A refresh-token family is bound to the application the session was opened
   for; rotation cannot move a session across the boundary, and it re-checks
   entitlement on every rotation (revoking the family if the role lost it).
4. A resource server only accepts tokens for the applications it serves
   (`SERVICE_APPLICATIONS`, or `@require_auth(application=...)` per route).

Nothing else about the auth mechanism changed: short-lived HS256 access tokens,
rotating opaque refresh tokens with reuse detection, TOTP MFA, DB-backed
permission checks, RBAC, row-level scope, append-only audit log.

---

## 2. The Mobile Admin roles

Registered in `auth/constants/roles.py` and seeded by
`auth/db/migrate_mobile_admin.py`. They are **first-class roles, not aliases**
of `Super Admin` / `Secondary Admin` / `Normal Admin`.

| Role | Scope | Permissions |
|---|---|---|
| `mobile_super_admin` | `MOBILE_GLOBAL` | `mobile.users.read` `mobile.users.write` `mobile.users.delete` `mobile.users.approve` `mobile.admins.manage` `mobile.content.read` `mobile.content.write` `mobile.reports.read` `mobile.settings.manage` `mobile.audit.read` |
| `mobile_secondary_admin` | `MOBILE_SUPPORT` | `mobile.users.read` `mobile.users.write` `mobile.content.read` `mobile.content.write` `mobile.reports.read` |

Three separations make "not an alias" enforceable rather than a naming
convention:

- **Permission namespace.** All Mobile permissions are `mobile.*` and disjoint
  from the B2B set, so a Mobile role can never satisfy a B2B
  `@require_permission("users.read")` — and vice versa.
- **Scope.** `MOBILE_GLOBAL` / `MOBILE_SUPPORT` are deliberately unknown to the
  B2B row-level scope engine (`auth/services/authorization_service.py`), which
  fails closed on them: a Mobile token cannot widen into school/class data.
- **Application.** A `mobile_*` role logging into `sentio-b2b` is rejected 403,
  and a B2B role logging into `sentio-mobile` is rejected 403.

Assignment is privileged: `PRIVILEGED_ROLES` now covers the Mobile Admin roles,
so only a B2B **Super Admin** can grant `mobile_super_admin` /
`mobile_secondary_admin` (via `POST /api/users/<id>/roles/<role_id>`,
`POST /api/admin/approve-user/<id>`, or user create/update). Secondary Admins
cannot.

---

## 3. What the Mobile Admin backend does

### 3.1 Login

```http
POST /api/auth/login
Content-Type: application/json

{ "email": "...", "password": "...", "application": "sentio-mobile" }
```

`application` may also be sent as the `X-Sentio-Application` header. Omitting it
means `sentio-b2b` — so the existing web client needs no change.

Responses:

| Case | Result |
|---|---|
| Success | `200 {access_token, user, csrf_token, application}` + `sentio_refresh` cookie |
| MFA enabled | `200 {mfa_required: true, pending_token, application}`, no cookies |
| Role not entitled to `sentio-mobile` | `403` |
| Unregistered application id | `400` |
| Pending / rejected / suspended / inactive account | unchanged (`403`) |

MFA completion (`POST /api/auth/mfa/verify`) needs no new field — the
`pending_token` carries the application.

Refresh (`POST /api/auth/refresh`) and logout (`POST /api/auth/logout`) are
unchanged; refresh reissues a token for the same application as the session.

### 3.2 Validating a token on each Mobile API request

Two supported options — pick one, do not write a third:

**A. Local verification (preferred, no round trip).** The Mobile backend holds
the same `JWT_SECRET_KEY` and verifies:

- signature `HS256`
- `iss == "sentio-mind-auth"`
- `aud == "sentio-mobile-api"` **and** `app == "sentio-mobile"`
- `type == "access"`, `exp` in the future

Then authorize on the `permissions` claim (`mobile.*`). If the Mobile backend
runs this codebase, it gets all of that from
`@require_auth(application=APP_MOBILE)` with `SERVICE_APPLICATIONS=sentio-mobile`.

**B. Introspection (no shared secret).**

```http
GET /api/auth/introspect
Authorization: Bearer <end user's access token>
```

Returns `{active, sub, email, application, roles, role, scope_type,
permissions, exp, jti}`. This path also re-checks revocation, account status and
approval on every call, at the cost of a round trip per request.

Either way the Mobile backend performs **no** authentication of its own.

---

## 4. Deployment

```bash
# 1. Migrate (idempotent). Adds the application binding + Mobile roles,
#    and syncs mobile.* role->permission grants from ROLE_CONFIG.
python -m auth.db.migrate_mobile_admin

# 2. Auth service — serves every application (default; may be left unset)
SERVICE_APPLICATIONS=sentio-b2b,sentio-mobile

# 3. Mobile Admin backend — accepts Mobile tokens only
SERVICE_APPLICATIONS=sentio-mobile

# 4. B2B resource servers — accepts B2B tokens only
SERVICE_APPLICATIONS=sentio-b2b
```

Then have a Super Admin approve/assign the first `mobile_super_admin`. No
credentials are seeded, by design (SEC-003).

Fresh installs get the same result from `auth/db/schema.sql` + `auth/db/seed.sql`.

---

## 5. Files touched

| File | Change |
|---|---|
| `auth/constants/applications.py` | **new** — application registry, audiences, normalisation |
| `auth/constants/roles.py` | Mobile roles, per-role `applications`, `MOBILE_ADMIN_ROLES`, `PRIVILEGED_ROLES`, `ALL_ROLES`, lookup helpers |
| `auth/config.py` | `SERVICE_APPLICATIONS` (validated at startup) |
| `auth/helpers/jwt_helper.py` | per-application `aud`, `app` claim, `expected_application`, `TokenApplicationError`, `token_application()` |
| `auth/middleware/auth_middleware.py` | rejects tokens from other applications; `require_auth(application=…)`, `require_application()` |
| `auth/services/auth_service.py` | login / MFA-completion / refresh bind + enforce the application; `LOGIN_DENIED_APPLICATION`, `REFRESH_DENIED_APPLICATION` audit events |
| `auth/services/refresh_token_service.py` | refresh families carry `application` through rotation |
| `auth/routes/auth_routes.py` | `application` on login, `GET /api/auth/introspect` |
| `auth/routes/mfa_routes.py` | MFA completion inherits the pending token's application |
| `auth/routes/{user,role,admin}_routes.py`, `auth/services/user_service.py` | admin-tier assignment gates extended to the Mobile roles |
| `auth/db/schema.sql`, `auth/db/seed.sql`, `MIGRATIONS.sql`, `auth/db/migrate_mobile_admin.py`, `auth/db/clean_roles.py` | `application` columns; Mobile roles + `mobile.*` permissions |
| `tests/test_mobile_admin_auth.py` | **new** — 28 tests over the boundary above |

Not touched: `cv_analysis/`, and every existing auth mechanism.
