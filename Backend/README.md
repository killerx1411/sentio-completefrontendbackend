# Sentio Mind Backend

Flask backend for Sentio Mind — a behavioral-intelligence platform that analyses school CCTV
footage (face detection → emotion / posture / gaze → per-person wellbeing traits) and serves
those reports through a role-scoped, hardened auth API.

The Backend is **two systems behind one boundary**:

* **Stakeholder / auth service** — `app_factory.create_auth_app()`, entry `wsgi_auth:app`.
  Authentication, RBAC, scope, users, roles, admin, MFA, sessions, audit, security middleware.
  Imports no CV library; installs from `requirements.txt` alone.
* **CV / analysis system** — the `cv_analysis/` package, entry `cv_analysis.app:app`.
  CCTV processing, detection, emotion/posture/gaze, person profiles, reports.
  Installs `requirements-cv.txt` on top; authenticates against the auth service's stack.

`test_db:app` still exists and still serves both in one process (unchanged URLs). The split,
the dependency boundary and the endpoint classification are documented in
[`ARCHITECTURE_SEPARATION.md`](ARCHITECTURE_SEPARATION.md); the CV side has its own
[`cv_analysis/README.md`](cv_analysis/README.md).

This document is written to be self-contained: an engineer (or an LLM) with only this file
should be able to reason about the whole Backend folder without reading every source file.

---

## 1. Quick facts

| Thing | Value |
|---|---|
| Language / framework | Python 3.11+, Flask (blueprints + `create_auth_app()` factory) |
| Auth entry point | `wsgi_auth:app` — stakeholder/auth only, zero CV imports |
| CV entry point | `cv_analysis.app:app` — CV/analysis only |
| Combined entry point | `test_db:app` — auth app + CV blueprints in one process (current prod topology) |
| Test factory | `create_app(testing=True)` in `test_db.py` → `create_auth_app(testing=True)` — auth/API routes only, no CV stack |
| Database | PostgreSQL, schema `auth_enabler`, driver `psycopg2` with `RealDictCursor` |
| Cache / limits | Redis (Flask-Limiter storage + optional helper store), in-memory fallback |
| Auth model | Short-lived JWT access token (header) + opaque rotating refresh token (HttpOnly cookie) + double-submit CSRF |
| Authorization | RBAC (roles → permissions) **plus** row-level scope (GLOBAL / SCHOOL / CLASS / …) |
| Dev port | 5001 (`python wsgi_auth.py` or `python test_db.py`); CV standalone on `CV_PORT` 5002 |
| Prod port | 5000 (gunicorn, behind nginx) |
| Requirements | `requirements.txt` (auth) + `requirements-cv.txt` (CV stack) |

---

## 2. Directory map

```
Backend/
├── app_factory.py          ← create_auth_app() — STAKEHOLDER/AUTH app, zero CV imports
├── wsgi_auth.py            ← auth-only WSGI entry (gunicorn wsgi_auth:app)
├── test_db.py              ← combined entry: create_auth_app() + CV blueprints (73 lines)
├── common/http.py          ← ProxyFix + CORS header set + security/CSP headers (shared)
├── cv_analysis/            ← THE CV SYSTEM (see cv_analysis/README.md)
│   ├── app.py              ← create_cv_app(), standalone CV service
│   ├── libraries.py        ← the ONLY import site for cv2/DeepFace/MediaPipe/MTCNN
│   ├── config.py           ← CV paths, thresholds, CV rate limit (CV_* env vars)
│   ├── state.py            ← person_database, pinned_profiles, analysis_cache
│   ├── db.py               ← persons/videos/frames/analysis/traits writes
│   ├── pipeline.py         ← detection → emotion/posture/gaze → traits → report
│   ├── dashboard.py        ← operator dashboard HTML (GET /)
│   ├── routes.py           ← cv_bp: /run_analysis, /get_report, /pin_profile, …
│   ├── routes_analysis.py  ← analysis_bp (/analysis)
│   └── routes_person.py    ← person_bp (/person)
├── gunicorn_config.py      ← production WSGI config (gthread, 300s timeout, no preload)
├── testpg.py               ← ad-hoc Postgres connectivity script
├── requirements.txt        ← stakeholder/auth deps only
├── requirements-cv.txt     ← CV stack (opencv, mediapipe, deepface, tensorflow, …)
├── pytest.ini              ← pythonpath=., testpaths=tests
├── .env / .env.local       ← real secrets (gitignored); *.example are the templates
├── MIGRATIONS.sql          ← idempotent security migrations for a live DB
├── ARCHITECTURE_SEPARATION.md  ← CV/auth boundary: inventory, dependencies, endpoints
├── CHANGES.md, SECURITY_CHANGELOG.md
├── nginx/nginx.conf        ← TLS termination, CSP, static React, proxy → 127.0.0.1:5000
├── analysis_results/       ← generated JSON reports (multi_day_report.json is the key file)
├── input_videos/           ← CCTV source footage, organised by school/date folders
├── profiles/               ← person_database.json (face encodings + profile images)
├── tests/                  ← pytest suite, all security-focused
└── auth/                   ← the entire auth/authz subsystem (detailed in §5)
    ├── config.py           ← AuthConfig + validate_config()
    ├── env_loader.py       ← .env then .env.local (override)
    ├── db_connection.py    ← threaded psycopg2 pool, slow-query logging
    ├── db/connection.py    ← deprecated alias re-exporting db_connection
    ├── startup_checks.py   ← production hard-fail assertions
    ├── constants/          ← roles.py (ROLE_CONFIG), cookies.py
    ├── db/                 ← schema.sql, seed.sql, migrate*.py scripts
    ├── helpers/            ← jwt, password, cookie, audit, email, rate-limit, redis, validation, response, request
    ├── middleware/         ← auth_middleware.py, csrf.py, rate_limiter.py
    ├── queries/            ← raw parameterised SQL constants
    ├── routes/             ← blueprints (HTTP layer only)
    └── services/           ← business logic (DB transactions live here)
```

**Layering rule** used throughout `auth/`:

```
routes/ (HTTP: parse, validate, shape response)
   ↓ calls
services/ (business logic, owns the DB transaction, returns plain dicts)
   ↓ uses
queries/ (SQL string constants)  +  helpers/ (pure-ish utilities)
   ↓
db_connection.py (pool)
```

Services **never** return Flask responses. They return `{"data": ...}` / `{"message": ...}`
on success, or `{"error": "...", "status": <int>}` on failure. Routes translate that into
`success_response()` / `error_response()`.

---

## 3. Application bootstrap

Three entry points, one factory each. None of them duplicates the others.

### 3.1 Stakeholder/auth service — `app_factory.create_auth_app()`

Entry: `wsgi_auth:app`. This is the boundary marker — importing it loads **no** CV library.

1. `load_env()` — reads `Backend/.env`, then `Backend/.env.local` with `override=True`.
2. Auth blueprints and middleware are imported (this triggers `get_config()`, which runs
   `validate_config()` once — a bad `JWT_SECRET_KEY` fails here, at import).
3. `app = Flask(__name__)`; `app.config.from_object(cfg)` — `AuthConfig` class attributes
   become Flask config. With `testing=True`, `FLASK_ENV=test`,
   `RATELIMIT_STORAGE_URI=memory://` and `RATELIMIT_STRATEGY=fixed-window` are forced.
4. `CORS(app, origins=cfg.ALLOWED_ORIGINS, supports_credentials=True,
   allow_headers=["Content-Type","Authorization","X-CSRF-Token"])`.
5. `init_rate_limiter(app)` — binds Flask-Limiter; **raises** if `RATELIMIT_STORAGE_URI` is a
   `redis://` URL that does not answer `PING` (outside `FLASK_ENV=test`).
6. `apply_proxy_fix(app)` (`common/http.py`) — `ProxyFix(x_for=TRUSTED_PROXY_COUNT, x_proto=1,
   x_host=1)` so `remote_addr` is the real client behind nginx.
7. `register_auth_blueprints(app)` — registers, in order:
   `auth_bp, role_bp, audit_bp, user_bp, admin_bp, mfa_bp, security_bp`.
8. `@app.after_request` → `apply_security_headers` (`common/http.py`) —
   `X-Content-Type-Options`, `X-Frame-Options: DENY`, HSTS (2y, preload), `Referrer-Policy`,
   `Permissions-Policy`, and a strict CSP (`default-src 'self'; script-src 'self';
   frame-ancestors 'none'; object-src 'none'`).
9. `GET /health` is registered here, so liveness never depends on the CV stack.
10. `init_auth_db()` in a try/except (skipped when `testing=True`) — a failure only warns;
    `run_auth_preflight()` retries.

`run_auth_preflight(app)` = `validate_config()` → `run_startup_checks(app)` → `init_auth_db()`.
`python wsgi_auth.py` runs it, then `app.run(host=0.0.0.0, port=PORT or 5001)`.

### 3.2 CV service — `cv_analysis.app.create_cv_app()`

Entry: `cv_analysis.app:app`, dev port `CV_PORT` (5002). Same CORS / limiter / ProxyFix /
security headers via `common/http.py`, then `register_cv_blueprints(app)` mounts
`cv_bp` (root CV routes), `analysis_bp` (`/analysis`) and `person_bp` (`/person`).

Heavy CV libraries are imported once, in `cv_analysis/libraries.py`, each behind `try/except`
setting an availability flag: `DEEPFACE_AVAILABLE`, `MEDIAPIPE_AVAILABLE`,
`FACE_RECOGNITION_AVAILABLE`, `MTCNN_AVAILABLE`, plus `cv2`/`np`. A missing library degrades
that feature instead of crashing the app; `library_status()` is what `GET /system_info` returns.

It authenticates with the *existing* auth stack (`@require_auth`, `@require_permission`,
`AuthorizationService`) — there is deliberately no second JWT, user store or role system.

### 3.3 Combined deployment — `test_db:app`

73 lines of composition, no logic:

```python
app = create_auth_app()      # auth/RBAC/audit/security — zero CV imports
register_cv_blueprints(app)  # CV routes on the same process
```

This is the current production topology and keeps every URL exactly as it was.
`create_app(testing=True)` delegates to `create_auth_app(testing=True)` — the slim auth/API app
the pytest suite uses, with **none** of the CV stack. `create_app(testing=False)` returns the
module-level combined `app`.

---

## 4. Configuration & environment

`auth/config.py` holds one class, `AuthConfig`, whose attributes are read from `os.environ` at
class-definition time. `get_config()` memoises a single instance and runs `validate_config()`
exactly once.

`validate_config()` raises `RuntimeError` when:
- `FLASK_ENV` is empty;
- `JWT_SECRET_KEY` is still `change-me-in-production` (unless `FLASK_ENV=test`);
- `FLASK_ENV=production` and `SMTP_PASSWORD` is empty, or `STRICT_PASSWORD_BREACH_CHECK` is false;
- `len(JWT_SECRET_KEY) < 32`.

`auth/startup_checks.py::run_startup_checks(app)` is the second gate (called from
`pre_flight_check()`); in production it additionally requires `SESSION_COOKIE_SECURE=True`,
`PREFERRED_URL_SCHEME=https`, `SECRET_KEY` ≥ 32 chars, a `postgresql...` DSN, and it also
requires `MFA_ENCRYPTION_KEY` to be set in any non-test env. On success it writes a
`startup_security_checks_passed` audit row.

### Key environment variables

| Var | Purpose / default |
|---|---|
| `FLASK_ENV` | `development` \| `production` \| `test`. Drives cookie `Secure`, CORS defaults, URL scheme, error sanitising. Required. |
| `JWT_SECRET_KEY` | HS256 signing key **and** the CSRF HMAC key. ≥ 32 chars. |
| `MFA_ENCRYPTION_KEY` | SHA-256'd → base64 → Fernet key that encrypts TOTP secrets at rest. |
| `SENTIO_DB_URL` | Postgres DSN. |
| `SENTIO_DB_SSLMODE` | `require` (default) / `disable` / `prefer`. |
| `RATELIMIT_STORAGE_URI` | Flask-Limiter storage; default `redis://localhost:6379/1`. **Must** be Redis in prod — with `memory://` each gunicorn worker enforces limits independently, multiplying the effective limit by worker count. |
| `REDIS_URL` | Optional store for `helpers/redis_client.py`; falls back to an in-process dict. |
| `ALLOWED_ORIGINS` | CSV. Defaults to `https://product.sentiomind.in`, or the localhost:3000 pair when `FLASK_ENV=development`. |
| `FRONTEND_URL` | Used to build reset links and the unauthenticated redirect target. |
| `SMTP_*` | Credential + reset mail delivery. If `SMTP_HOST`/`SMTP_FROM` are unset, mail is skipped and the temp password is **deliberately not logged**. |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | 15 / 7. |
| `BCRYPT_ROUNDS` | 12. |
| `MAX_LOGIN_ATTEMPTS` / `MAX_IP_LOGIN_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | 5 / 5 / 15. |
| `TEMP_PASSWORD_EXPIRY_HOURS` | 12. |
| `STRICT_PASSWORD_BREACH_CHECK` | `true`. When HIBP is unreachable and this is true, password-setting requests fail 503 rather than silently skipping the check. |
| `ENABLE_OPEN_REGISTRATION` | `false`. Gates `POST /api/auth/register`. |
| `SERVICE_APPLICATIONS` | CSV of applications whose access tokens this deployment accepts; default = all registered (`sentio-b2b,sentio-mobile`). Set to `sentio-b2b` on a B2B-only deployment, `sentio-mobile` on the Mobile Admin backend. |
| `TRUSTED_PROXY_COUNT` | ProxyFix hop count; 1. |
| `PORT` | 5001 dev / 5000 gunicorn — must match nginx `upstream auth_api`. |

Per-route rate limits are also config constants (`RATELIMIT_LOGIN = "10/minute;100/hour"`,
`RATELIMIT_SIGNUP`, `RATELIMIT_MFA_VERIFY = "5/minute"`, etc.) so routes read them off `config`.

---

## 5. The auth subsystem, file by file

### 5.1 `auth/db_connection.py` — connection pool

- `psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=10)` created lazily on first use.
- Every connection: `sslmode` from `SENTIO_DB_SSLMODE`, `cursor_factory=RealDictCursor`
  (rows behave like dicts — this is why all service code does `row["column"]`),
  `connect_timeout=5`, and `options="-c statement_timeout=30000"` (30s server-side query cap).
- `get_db_connection()` returns a pooled conn with `autocommit=False`; **callers must**
  `release_db_connection(conn)` in a `finally` block — this is the dominant idiom in services.
- `db_cursor()` is a context manager that commits on success, rolls back on exception, always releases.
- `get_db_cursor()` returns a `_SlowQueryCursor` wrapper that logs any `execute` over 5s.
- `init_auth_db()` runs `SELECT 1` as a startup connectivity probe.
- `auth/db/connection.py` is a deprecated re-export kept for the migration scripts.

### 5.2 `auth/constants/roles.py` — the authorization source of truth

`ROLE_CONFIG` maps each role name to a `scope` and a permission list:

| Role | Scope | Permissions |
|---|---|---|
| Super Admin | `GLOBAL` | users.read/write/delete/approve, roles.assign, permissions.manage, reports.read/write, observations.write, audit.read |
| Secondary Admin | `GLOBAL` | users.read, users.write, reports.read |
| Normal Admin | `MONITORING` | users.read, reports.read |
| Principal | `SCHOOL` | reports.read |
| Psychologist | `SCHOOL_FLAGGED` | reports.read |
| Class Teacher | `CLASS` | reports.read, observations.write |
| Behaviour Scientist | `ANALYTICS` | reports.read |
| mobile_super_admin | `MOBILE_GLOBAL` | mobile.users.read/write/delete/approve, mobile.admins.manage, mobile.content.read/write, mobile.reports.read, mobile.settings.manage, mobile.audit.read |
| mobile_secondary_admin | `MOBILE_SUPPORT` | mobile.users.read/write, mobile.content.read/write, mobile.reports.read |

Every role also declares the `applications` it may receive tokens for
(`sentio-b2b`, `sentio-mobile` — see `auth/constants/applications.py`). The two
`mobile_*` roles are **first-class roles of this authority, not aliases** of the
B2B admin tier: different names, different scopes, and a `mobile.*` permission
namespace that is disjoint from the B2B one, so a Mobile token can never satisfy
a B2B permission check. See `MOBILE_ADMIN_INTEGRATION.md`.

Also exports `ADMIN_ROLES`, `EDUCATIONAL_ROLES`, `STAKEHOLDER_ROLES`,
`MOBILE_ADMIN_ROLES`, `PRIVILEGED_ROLES` (admin tier across *all* applications —
only a Super Admin may assign one) and `ALL_ROLES`.
`auth/db/seed.sql` seeds the same roles/permissions into Postgres — **keep the two in sync**
(`tests/test_mobile_admin_auth.py::TestDatabaseParity` guards the mobile half).

Note the two-track design: `ROLE_CONFIG` feeds the JWT claims (`role`, `scope_type`,
`permissions`), while `require_permission` re-checks the permission **in the database** on every
request. The DB is authoritative; the JWT claim is a convenience for the frontend and for scope
filtering.

### 5.3 `auth/helpers/jwt_helper.py` — tokens

- Algorithm `HS256` only, `iss="sentio-mind-auth"`, both verified on decode.
- `aud` is **per application**: `sentio-mind-api` for `sentio-b2b` (unchanged), `sentio-mobile-api`
  for `sentio-mobile`. `decode_token()` accepts any registered audience and additionally stamps an
  `app` claim; pass `expected_application=` to bind a token to one application
  (raises `TokenApplicationError`).
- `generate_access_token(user_id, email, roles, role, scope_type, permissions, application)` →
  claims `exp` (now + `JWT_ACCESS_MINUTES`), `iat`, `sub` (**string** user id), `email`,
  `roles` (list of names), `type="access"`, `jti` (uuid4), `app`, plus optional `role`/`scope_type`/`permissions`.
- `generate_mfa_pending_token(user_id, email, remember, application)` → `type="mfa_pending"`,
  5-minute expiry, carries the `remember` flag **and** the application so the MFA round-trip
  cannot cross an application boundary.
- Tokens minted before this change (no `app` claim) resolve to `sentio-b2b` from their audience.
- `generate_refresh_token_value()` → a bare uuid4 string (opaque; **not** a JWT).
- `decode_token()` raises `TokenExpiredError` / `TokenInvalidError` (never leaks the PyJWT type).
- `revoke_access_token(jti, expires_at)` inserts into `auth_enabler.revoked_tokens`
  (`ON CONFLICT DO NOTHING`); `is_token_revoked(jti)` checks it and **fails closed** — if the DB
  query raises, it returns `True` and logs `[SECURITY]`.

### 5.4 `auth/helpers/password_helper.py`

- bcrypt with `BCRYPT_ROUNDS` (12).
- `validate_password_strength`: ≥ 10 chars, **≤ 72 bytes** (bcrypt truncates past 72 bytes, which
  would make distinct passwords collide), upper + lower + digit + special.
- `is_password_pwned()` delegates to `HIBPService`.

### 5.5 `auth/services/hibp_service.py` — breach checking

k-anonymity call to `api.pwnedpasswords.com/range/<first 5 SHA-1 hex>`; only the prefix leaves the
process. Returns `CLEAN` / `BREACHED` / `UNAVAILABLE`. Has a per-prefix cache
(`HIBP_CACHE_TTL_SECONDS`, 24h) and a 60-second circuit breaker after a network failure.
`validate_password_not_breached()` is the API-facing wrapper: `BREACHED` → 400;
`UNAVAILABLE` → 503 if `STRICT_PASSWORD_BREACH_CHECK` else an audit row + pass.

### 5.6 `auth/helpers/cookie_helper.py` + `auth/middleware/csrf.py` — cookies & CSRF

Two cookies:

| Cookie | HttpOnly | Path | Contents |
|---|---|---|---|
| `sentio_refresh` | **yes** | `/api/auth` | opaque refresh token (uuid4) |
| `sentio_csrf` | **no** (intentional) | `/` | `nonce.exp.hmac` |

`max_age` on the refresh cookie is set only when `remember=true`; otherwise it is a session cookie.
`Secure` follows `SESSION_COOKIE_SECURE` (= `FLASK_ENV == "production"`), `SameSite=Lax` on both.

CSRF is **stateless double-submit**: `generate_csrf_token(user_id)` returns
`f"{nonce}.{exp}.{HMAC_SHA256(JWT_SECRET_KEY, f'{user_id}:{nonce}:{exp}')}"`, TTL 7 days.
`@csrf_required` requires all four of: the `sentio_csrf` cookie present, the `X-CSRF-Token` header
present, cookie == header (`compare_digest`), and the HMAC valid for the user id resolved from the
refresh cookie. Any failure → `403 {"error": "csrf_validation_failed"}`.
`invalidate_csrf_token()` is a documented no-op (tokens are stateless).
The `httponly=False` on the CSRF cookie is required by the double-submit pattern and is documented
in-file alongside its compensating controls (strict CSP, no `dangerouslySetInnerHTML`, SameSite).

### 5.7 `auth/middleware/auth_middleware.py` — `@require_auth`, `@require_permission`

`@require_auth` (usable bare or as `@require_auth(redirect_url=...)` for HTML routes) rejects, in order:

1. a token passed via `?token=` / `?access_token=` query string (401 — header only);
2. missing/malformed `Authorization: Bearer` header;
3. empty bearer value;
4. expired token → 401 `"Signature expired. Please log in again."`;
5. invalid token → 401;
6. `type == "mfa_pending"` used as an access token → 401;
7. any `type != "access"` → 401;
8. `is_token_revoked(jti)` → 401 `"Token has been revoked"`.

On success it sets `g.user = payload` and `g.jti`, then does a **live DB re-check** of the user row:
`registration_status != 'APPROVED'` → 403; `status != 'active'` → 403; and if `is_first_login` is
true, every path outside `FIRST_LOGIN_ALLOWED_PATHS`
(`/api/auth/change-temp-password`, `/api/auth/logout`, `/api/auth/refresh`) → 403
`"Password change required on first login."`. Failures are written to `audit_logs` as
`LOGIN_FAILED_TOKEN`.

`@require_permission("users.write")` runs `CHECK_USER_PERMISSION` (user_roles ⋈ role_permissions ⋈
permissions) against the DB. It first expands the requested permission through
`get_implied_permissions()`: a stronger verb satisfies a weaker one, so `users.delete` satisfies a
`users.read` requirement (`read`/`view` ← read, view, write, create, edit, delete; `write`/`create`/
`edit` ← write, create, edit, delete; `delete` ← delete; `approve`/`assign`/`manage` are exact).
Decorator order is always `@require_auth` **above** `@require_permission` — the latter reads `g.user`.

### 5.8 `auth/middleware/rate_limiter.py` — Flask-Limiter

Global default `200/minute` keyed on the real client IP (`X-Real-IP` → first `X-Forwarded-For` hop →
`remote_addr`, via `helpers/request_helper.py::get_client_ip`).
`limit_ip(spec)` keys on IP; `limit_authenticated(spec)` keys on `user:<sub>` when a valid access
token is present, else falls back to IP. `on_breach` writes a `rate_limit_exceeded` audit row.
The 429 handler returns `{"error": "rate_limit_exceeded", "retry_after": n}` with a `Retry-After`
header. `init_rate_limiter` also validates the Redis URI by pinging it (raises if down, outside tests).

### 5.9 `auth/helpers/rate_limit_helper.py` — login lockout (separate from Flask-Limiter)

DB-backed brute-force tracking in `auth_enabler.login_attempts`, windowed by
`LOGIN_LOCKOUT_MINUTES`. `is_locked_out(email, ip)` locks when either the `(email, ip)` count
reaches `MAX_LOGIN_ATTEMPTS` or the IP-wide count reaches `MAX_IP_LOGIN_ATTEMPTS`, and **fails
closed in every environment** if the DB is unreachable (SEC-012). `clear_attempts(email)` runs on
successful login. The same module rate-limits password-reset requests
(`password_reset_requests` table, `PASSWORD_RESET_MAX_PER_HOUR = 3`, also fail-closed).

### 5.10 `auth/helpers/audit_helper.py` — append-only audit log

`log_activity(user_id, action, module, description, ip_address, severity, details, user_agent, cur=None)`
inserts into `auth_enabler.audit_logs`. Severity is clamped to `INFO|WARNING|CRITICAL`; `details` is
JSONB. Passing `cur` joins the caller's transaction (used so signup + terms-acceptance commit
atomically); otherwise it opens its own connection and **swallows failures** — audit logging never
breaks the request. A Postgres `BEFORE UPDATE OR DELETE` trigger
(`prevent_audit_log_modification`, in the module docstring and `MIGRATIONS.sql`) makes the table
genuinely append-only at the DB level.

### 5.11 `auth/helpers/validation_helper.py` / `response_helper.py`

- `sanitize_email` normalises via `email_validator` (no deliverability check) and lowercases.
- `sanitize_string(value, max_length, field_name)` strips, rejects NUL bytes, enforces length.
- `validate_pagination`, `validate_uuid`, `mask_sensitive` (redacts JWT-shaped substrings from logs).
- `success_response(data, message, status_code)` → `{"status":"success","message":...,"data":...}`.
- `error_response(message, status_code)` → `{"status":"error","message":...}`, and in **production**
  any message matching `Error|Exception|Traceback|psycopg2|line ` is replaced with
  `"An internal error occurred"`.
- `sanitize_user_output(user)` strips `password_hash`, `created_by`, `updated_by`, and converts
  `temp_password_expiry` into a boolean `is_temp_password_expired`. Every route that returns a user
  passes it through this.

### 5.12 `auth/services/refresh_token_service.py` — rotation & reuse detection

Refresh tokens are opaque uuid4 values; only `sha256(token)` is stored (`hash_token`). Each row in
`auth_enabler.refresh_tokens` carries `user_id`, `token_hash`, `device_hash`
(`sha256(user_agent|accept_language)`), `family_id`, `expires_at`, `replaced_by`, `remember`.

`rotate_refresh_token(raw)`:
1. unknown hash → 401 `"Invalid refresh token"`;
2. row already has `revoked_at` → **reuse detected**: revoke the entire `family_id`, log
   `refresh_token_reuse` at CRITICAL, return `token_reuse_detected` + `clear_cookie`;
3. expired → 401;
4. stored `device_hash` present and different → log `REFRESH_DEVICE_MISMATCH` CRITICAL, revoke the
   family, return `device_mismatch` + `clear_cookie`;
5. otherwise mint a new token in the same family, point the old row's `replaced_by` at it, stamp the
   old row `revoked_at = NOW()`, and return the new raw token.

`revoke_family_for_token` (logout), `revoke_all_refresh_tokens_for_user` (password reset, temp
password change) and `resolve_user_id_from_refresh_cookie` (used by CSRF) round out the module.

### 5.13 `auth/services/auth_service.py` — the core flows (908 lines)

Module constants: `MAX_ACTIVE_SESSIONS = 10`, `PASSWORD_RESET_EXPIRY_MINUTES = 15`, and
`_DUMMY_PASSWORD_HASH` (a bcrypt hash computed once at import, used to burn identical CPU time on
unknown-email logins so response latency cannot be used to enumerate accounts).

**`signup_user(...)`** — public "request access". Inserts a user with a random placeholder password
hash, `status='inactive'`, `registration_status='PENDING'`, records `terms_accepted_at` and a
`terms_accepted` audit row in the same transaction. Returns the **same** message whether or not the
email already exists (`UniqueViolation` is swallowed) — no enumeration.

**`register_user(...)`** — self-service registration with a chosen password. Gated by
`ENABLE_OPEN_REGISTRATION`. Validates strength + HIBP, still lands in `PENDING`.

**`login_user(email, password, device_info, ip_address, accept_language, accept_encoding, remember)`** —
the main path:
1. `is_locked_out(email, ip)` → 429;
2. load user by email; if absent, run `verify_password` against `_DUMMY_PASSWORD_HASH`, record a
   failed attempt, and return the generic `"Invalid email or password"` 401;
3. `registration_status` gates: `PENDING` → 403 "awaiting approval", `REJECTED` / `SUSPENDED` /
   anything not `APPROVED` → 403;
4. `status != 'active'` → 403;
5. bcrypt verify; on failure record the attempt and audit `LOGIN_FAILED` at WARNING, escalating to
   CRITICAL from the 3rd recent failure (`_login_failed_severity`);
6. if `mfa_enabled` → clear attempts and return `{"mfa_required": True, "pending_token": ...}` (5-min token);
7. if `is_first_login` and `temp_password_expiry` has passed → 401 "contact an administrator";
8. no roles assigned → 403;
9. build claims from `ROLE_CONFIG[roles[0].name]` (`_resolve_role_claims` upper-snake-cases the role:
   `"Class Teacher"` → `CLASS_TEACHER`), mint the access token;
10. mint the refresh token, compute a device fingerprint
    (`sha256(user_agent|accept_language|accept_encoding)`), `_enforce_session_limit` revokes the
    oldest sessions beyond 10, insert into **both** `user_sessions` (legacy, stores the token hash)
    and `refresh_tokens` (rotation family), commit;
11. `clear_attempts`, audit `LOGIN_SUCCESS`, return access token + refresh token + user.

**`complete_login_after_mfa(user_id, ...)`** — same token/session issuance as steps 9–10, called
after `POST /api/auth/mfa/verify` succeeds.

**`refresh_session(refresh_token, ...)`** — delegates to `rotate_refresh_token`, propagates
`token_reuse_detected`, then re-reads the user and **re-checks `status`/`registration_status`**
before minting a fresh access token. A user disabled mid-session cannot refresh.

**`logout_user(refresh_token, revoke_all, access_jti, access_exp)`** — revokes the refresh family,
marks `user_sessions` rows revoked (all of them when `revoke_all`), and blocklists the current
access-token `jti` until its natural expiry so the ≤15-minute window is actually closed.
Audits `LOGOUT` (CRITICAL when `revoke_all`) and `TOKEN_REVOKED`.

**`change_temp_password(user_id, temp, new)`** — only valid while `is_first_login`; validates
strength + HIBP, verifies the temp password, then sets the new hash, clears `is_first_login` and
`temp_password_expiry`, forces `registration_status='APPROVED'`/`status='active'`, and revokes every
session and refresh token for that user.

**`request_password_reset(email, ip)`** — always returns `{"message": "ok"}`. Internally: audit the
request, bail silently if the user is missing or inactive or over the reset rate limit, then store
`sha256(token)` in `password_reset_tokens` with a 15-minute expiry and email the **raw** token
(the raw token is never logged).

**`reset_password(token, new_password, ip)`** — hashes the presented token, looks up the newest
matching row, rejects when missing / `used_at` set / expired (all with the same
`"Invalid or expired token."` message), then updates the hash, marks the token used, revokes all
sessions and refresh tokens, and audits `PASSWORD_RESET_SUCCESS` at WARNING.

### 5.14 `auth/services/user_service.py` — admin user management

`MAX_SUPER_ADMINS = 2` is enforced by `get_super_admin_count()` on both direct role assignment and
approval. Functions: `create_user`, `update_user`, `delete_user`, `get_all_users`, `get_user_by_id`,
`get_pending_users`, `approve_user`, `approve_user_by_role_name`, `reject_user`.

`approve_user(user_id, role_id, admin_id)` is the important one: it requires the caller to hold
**Super Admin** (checked again inside the service, not only via the permission decorator), requires
the target to be `PENDING`, generates a 12-character random temporary password, hashes it, sets
`registration_status='APPROVED'`, `status='active'`, `is_first_login=TRUE`,
`temp_password_expiry = now + TEMP_PASSWORD_EXPIRY_HOURS`, replaces the user's roles with the granted
one, commits, then emails the credentials and audits `APPROVE_USER` at CRITICAL. If SMTP is not
configured the password is *not* logged — it must be delivered out of band.

### 5.15 `auth/services/role_service.py`

`create_role`, `get_all_roles`, `create_permission`, `assign_permission_to_role`, and
`assign_role_to_user` (which is single-role: it `DELETE`s existing `user_roles` rows first, and
refuses to exceed the Super Admin seat limit). Role/permission mutations audit at CRITICAL/WARNING.

### 5.16 `auth/services/mfa_service.py` — TOTP

`pyotp` TOTP with `valid_window=1`. The secret is stored **encrypted** with Fernet, where the key is
`urlsafe_b64encode(sha256(MFA_ENCRYPTION_KEY))`. `store_pending_mfa_secret` writes the secret with
`mfa_enabled=FALSE`; `confirm_mfa` verifies a code, flips `mfa_enabled=TRUE`, and returns 8 recovery
codes in `XXXX-XXXX-XXXX` form — stored bcrypt-hashed in a `TEXT[]`, and consumed by setting that
array slot to `NULL`. `disable_mfa` requires both the password and a valid TOTP code.

### 5.17 `auth/services/authorization_service.py` — row-level scope (IDOR defence)

RBAC answers "may this user call this endpoint"; this module answers "may this user see **this
row**". `school_name_to_id(name)` = first 8 hex chars of `sha256(lowercased name)` as an int, so a
school/class string maps to a stable numeric id (`"School:Class"` for classes).

- `_load_user_scope(user_id)` reads roles + `school_id`/`class_id` (falling back to hashing
  `assigned_school` / `assigned_class`) and returns a `User` with `scope_type` from `ROLE_CONFIG`.
- `user_from_jwt()` builds the same object from claims without a DB hit.
- `AuthorizationService.assert_school_scope` — `GLOBAL`/`MONITORING` pass; everyone else must match
  `school_id`. `assert_class_scope` — only `CLASS` is actually narrowed. `assert_flagged_only` —
  a `SCHOOL_FLAGGED` user (Psychologist) may only see students marked `flagged`
  (defaulting to `average_wellbeing < 40`). `assert_person_access` composes all three.
- `get_school_filter` / `get_class_filter` return the values used to filter list endpoints.
- Decorators `scope_required(scope)` and `require_person_scope(person_loader)`.
- Violations raise `PermissionError` → the routes convert it to `403 {"error": "forbidden"}`.

---

## 6. HTTP surface

### 6.1 `auth_bp` — `/api/auth` (`routes/auth_routes.py`)

| Method & path | Guards | Behaviour |
|---|---|---|
| `POST /login` | `limit_ip(10/min;100/hour)` | Body `{email, password, remember?, application?}` (or the `X-Sentio-Application` header; defaults to `sentio-b2b`). 400 on an unregistered application, 403 if the user's role is not entitled to it. Returns `{access_token, user, csrf_token, application}` and sets both cookies — **or** `{mfa_required: true, pending_token, application}` with no cookies. |
| `POST /signup` | `limit_ip(5/min;20/hour)` | Requires `terms_accepted === true`. Always 201 with the same message. |
| `POST /register` | `limit_ip(5/min;20/hour)` | 403 unless `ENABLE_OPEN_REGISTRATION`. Requires `terms_accepted`. |
| `POST /refresh` | `@csrf_required`, `limit_ip(30/min)` | Reads the `sentio_refresh` cookie, rotates it, returns a new `{access_token, csrf_token}` and re-sets both cookies. On reuse → 401 `{"error":"session_invalidated","reason":"token_reuse_detected"}` + cookie cleared. |
| `POST /logout` | `@csrf_required`, `limit_ip(20/min)` | Optional `{revoke_all: true}`. Blocklists the presented access `jti`, clears both cookies. |
| `POST /change-temp-password` | `@require_auth` | `{temp_password, new_password}`. One of the three paths allowed while `is_first_login`. |
| `POST /forgot-password` | `limit_ip(5/min;10/hour)` + a global `30/hour` bucket | Always `{"message":"ok"}`, whatever happens. |
| `POST /reset-password` | `limit_ip(5/min;10/hour)` | `{token, new_password}`. |
| `GET /me` | `@require_auth` | Current user + roles; audits `VIEW_PROFILE`. |
| `GET /introspect` | `@require_auth` | Token introspection for consumer backends (e.g. Sentio Mobile Admin) that do not hold the signing key. Returns `{active, sub, email, application, roles, role, scope_type, permissions, exp, jti}`. |

### 6.2 `mfa_bp` — `/api/auth/mfa` (`routes/mfa_routes.py`)

| Endpoint | Guards | Notes |
|---|---|---|
| `POST /setup` | `@require_auth` | Generates a secret, stores it encrypted (still disabled), returns `{qr_code_base64}`. Rejects `mfa_pending` tokens. |
| `POST /confirm` | `@require_auth` | `{totp_code}` → enables MFA, returns the one-time recovery codes. |
| `POST /disable` | `@require_auth` | `{password, totp_code}`. |
| `POST /verify` | `limit_ip(5/min)`, **no** `@require_auth` | `{pending_token, totp_code \| recovery_code}`. Validates `type=="mfa_pending"`, verifies, then calls `complete_login_after_mfa` and returns the same payload/cookies as `/login`. |

### 6.3 `user_bp` — `/api` (`routes/user_routes.py`)

`GET /users` (`users.read`), `GET /users/<id>` (`users.read`; audit logs in the response are blanked
unless the caller is Super Admin), `POST /users` (`users.write`), `PUT /users/<id>` (`users.write`),
`DELETE /users/<id>` (`users.delete`), `GET /dashboard/stats` (`users.read`).
Extra in-route rules on top of the permission check: only a Super Admin may create/assign an
admin-tier role, or modify/delete an existing Super Admin.

### 6.4 `admin_bp` — `/api/admin` (`routes/admin_routes.py`)

`GET /pending-users`, `POST /approve-user/<id>` (accepts `role_id` or a `role` name, the latter
normalised through `ROLE_ALIASES` — e.g. `Principle`→`Principal`, `Counsellor`→`Psychologist`,
`Teacher`→`Class Teacher`), `POST /reject-user/<id>`, plus `POST /users/<id>/approve|reject`
aliases. All require `users.approve` and carry a per-user `120/minute` limit.

### 6.5 `role_bp` — `/api` (`routes/role_routes.py`)

`POST /roles`, `GET /roles`, `POST /permissions`, `POST /roles/<role_id>/permissions/<permission_id>`
(`permissions.manage`), `POST /users/<user_id>/roles/<role_id>` (`roles.assign`, plus the Super
Admin guards).

### 6.6 `audit_bp` — `/api/audit-logs`

`GET ""` with `audit.read`. A `?user_id=` filter is restricted to **self** unless the caller is
Super Admin (SEC-005); unfiltered returns the newest 100 global rows joined to user emails.

### 6.7 `security_bp` — `/api/csp-report`

Unauthenticated, `limit_ip(20/min)`. Accepts browser CSP violation reports (`application/csp-report`
or JSON), truncates to 4000 chars into an audit row, returns 204.

### 6.8 `analysis_bp` — `/analysis`, `person_bp` — `/person` (CV-owned)

Both live in `cv_analysis/` (`routes_analysis.py`, `routes_person.py`) — they serve only
CV-generated data, but apply the auth package's RBAC + row-level scope.

`GET /analysis/report` (`reports.read`) loads `analysis_results/multi_day_report.json` and passes it
through `_filter_report_for_user`, which drops every `person_profiles` entry outside the caller's
school/class scope, drops non-flagged students for `SCHOOL_FLAGGED`, and rewrites
`overall_stats.total_unique_persons` to the filtered count. `POST /analysis/run` is a 501 stub
pointing at `POST /run_analysis`. `GET /person/<id>` and `POST /person/<id>/access-check` enforce
`assert_person_access` per row.

### 6.9 CV platform routes — `cv_bp` (`cv_analysis/routes.py`)

| Route | Guards |
|---|---|
| `GET /` | `@require_auth(redirect_url=FRONTEND_URL)` — serves the dashboard from `cv_analysis/dashboard.py`, redirects instead of 401ing browsers |
| `POST /run_analysis` | `@require_auth` + `observations.write` + analysis limit — runs the **synchronous** CV pipeline |
| `GET /get_report` | `@require_auth` + `reports.read` — scope-filtered |
| `POST /pin_profile` | `reports.write` + per-person scope check |
| `POST /update_person_name`, `/update_person_photo`, `/delete_person` | `@require_auth` + permission + scope; images capped at `MAX_IMAGE_BYTES = 2 MiB` |
| `GET /system_info` | `audit.read` — reports which CV libraries loaded (`library_status()`) |

`GET /health` is **not** here: it belongs to the stakeholder/auth service (`app_factory.py`), so a
liveness probe never depends on the CV stack.

React static files are served by nginx only — there is deliberately no unauthenticated Flask static
route (SEC-010).

---

## 7. End-to-end flows

### 7.1 Access request → approval → first login

```
POST /api/auth/signup            → users row: status=inactive, registration_status=PENDING
                                   audit: terms_accepted
   (Super Admin) GET /api/admin/pending-users
   (Super Admin) POST /api/admin/approve-user/<id> {role_id|role}
                                 → temp password generated + hashed
                                   registration_status=APPROVED, status=active,
                                   is_first_login=TRUE, temp_password_expiry=+12h
                                   role assigned, credentials emailed
                                   audit: APPROVE_USER (CRITICAL)
POST /api/auth/login             → tokens issued, but @require_auth now 403s every path except
                                   change-temp-password / refresh / logout
POST /api/auth/change-temp-password
                                 → new hash, is_first_login=FALSE,
                                   all sessions + refresh tokens revoked
POST /api/auth/login             → normal session
```

### 7.2 Login (no MFA)

```
client                      server
  │ POST /api/auth/login  ──▶ lockout check (login_attempts, fail-closed)
  │                          user lookup → status/registration gates
  │                          bcrypt verify (dummy hash if user unknown → constant time)
  │                          roles → ROLE_CONFIG → claims
  │                          access JWT (15 min, jti) + refresh uuid4
  │                          session cap (10) enforced; rows in user_sessions + refresh_tokens
  │ ◀── 200 {access_token, user, csrf_token}
  │     Set-Cookie: sentio_refresh (HttpOnly, /api/auth)
  │     Set-Cookie: sentio_csrf    (readable, /)
```

The client keeps `access_token` **in memory** (not localStorage), sends it as
`Authorization: Bearer <token>`, and echoes the CSRF cookie back as `X-CSRF-Token` on
`/refresh` and `/logout`.

### 7.3 Login with MFA

```
POST /api/auth/login   → 200 {mfa_required: true, pending_token}   (no cookies yet)
POST /api/auth/mfa/verify {pending_token, totp_code|recovery_code}
                       → complete_login_after_mfa → same payload + cookies as a normal login
```

### 7.4 Refresh rotation and reuse detection

```
POST /api/auth/refresh   (cookie sentio_refresh + header X-CSRF-Token)
  ├─ csrf_required: cookie==header, HMAC valid for the cookie's user
  ├─ rotate: old row revoked_at=NOW(), replaced_by=new; new row same family_id
  ├─ user re-checked: status=active AND registration_status=APPROVED
  └─ 200 {access_token, csrf_token} + rotated cookies

replay of an already-rotated token
  └─ entire family revoked, audit refresh_token_reuse (CRITICAL),
     401 {"error":"session_invalidated","reason":"token_reuse_detected"}, cookie cleared
```

The same family kill happens when the `device_hash` (`user_agent|accept_language`) changes.

### 7.5 A generic authorized request

```
Authorization: Bearer <access>
  → @require_auth        : signature, iss/aud, type=="access", jti not revoked (fail-closed),
                           then DB re-check of registration_status / status / is_first_login
  → @require_permission  : implied-permission expansion, then user_roles ⋈ role_permissions ⋈ permissions
  → @limit_authenticated : per-user (or per-IP) Flask-Limiter bucket
  → route                : _load_user_scope() → AuthorizationService row-level filtering
  → after_request        : security headers
```

### 7.6 Password reset

```
POST /api/auth/forgot-password {email}   → always 200 {"message":"ok"}
      (internally: rate limit 3/hour/email + 30/hour global; sha256(token) stored, 15-min expiry;
       raw token only ever appears in the email body)
POST /api/auth/reset-password {token, new_password}
      → strength + HIBP checks, token marked used_at,
        every session and refresh token for the user revoked
```

### 7.7 The analysis pipeline (`cv_analysis/pipeline.py`)

```
input_videos/<School>/<DD_MM_YYYY>/*.mp4
   ↓ extract_intelligent_frames()      (frame-difference sampling, ≤12 frames/video)
   ↓ enhance_frame_for_cctv()          (contrast/denoise for low-quality CCTV)
   ↓ detect_all_faces_in_frame()       (face_recognition / MTCNN / OpenCV fallbacks)
   ↓ per face, in a ThreadPoolExecutor:
        analyze_emotion_full()         (DeepFace, fallback heuristics)
        analyze_posture_for_person()   (MediaPipe Pose)
        analyze_gaze_and_attention()   (MediaPipe FaceMesh)
        analyze_face_texture_traits()  (OpenCV)
   ↓ compute_10_trait_wellbeing()      → per-person trait scores
   ↓ match_or_create_person()          (face-encoding similarity → stable person_id)
   ↓ db_upsert_person / db_insert_video / db_insert_frame / db_insert_analysis_with_traits
   ↓ generate_multi_day_report()       → analysis_results/multi_day_report.json
                                         (+ profiles/person_database.json)
```

Every consumer of that JSON (`/get_report`, `/analysis/report`, `/person/<id>`) filters it through
`AuthorizationService` before returning it, so a Class Teacher never sees another class's students.
`/run_analysis` is synchronous — hence gunicorn's 300s timeout and the note to move it to a queue.

---

## 8. Database schema (`auth_enabler`)

Base tables from `auth/db/schema.sql`:

| Table | Purpose |
|---|---|
| `users` | identity + `status`, `registration_status`, `is_first_login`, `temp_password_expiry`, `mfa_enabled`, `approved_by/at`, `organization`, `requested_role`, `created_by/updated_by` |
| `roles` | 7 seeded roles |
| `permissions` | `name`, `module`, `action` |
| `role_permissions` | role ⇄ permission |
| `user_roles` | user ⇄ role (effectively single-role: assignment clears first) |
| `user_sessions` | legacy session rows: hashed refresh token, `device_info`, `ip_address`, `revoked` |
| `audit_logs` | append-only activity trail |

Added by `MIGRATIONS.sql` (idempotent, safe on a live DB):

| Object | Purpose |
|---|---|
| `login_attempts` | brute-force window (email, ip, attempted_at) |
| `password_reset_requests` | reset throttling |
| `password_reset_tokens` | `token_hash`, `expires_at`, `used_at` |
| `revoked_tokens` | JWT `jti` blocklist with `expires_at` |
| `refresh_tokens` | rotation families: `token_hash`, `device_hash`, `family_id`, `replaced_by`, `remember` |
| `users.mfa_secret`, `users.mfa_recovery_codes TEXT[]`, `users.school_id`, `users.class_id`, `users.terms_accepted_at` | added columns |
| `user_sessions.device_fingerprint` | added column |
| `audit_logs.severity`, `.details JSONB`, `.user_agent` | added columns |
| trigger `audit_logs_append_only` | raises on any UPDATE/DELETE of an audit row |

Bring a database up with:

```powershell
psql "$env:SENTIO_DB_URL" -f auth/db/schema.sql
psql "$env:SENTIO_DB_URL" -f auth/db/seed.sql
psql "$env:SENTIO_DB_URL" -f MIGRATIONS.sql
```

The CV system's tables (`persons`, `videos`, `frames`, `analysis`, `traits`) live in the default
schema, not `auth_enabler`, and are written only by `cv_analysis/db.py`. They are not defined in
`auth/db/schema.sql` and were not touched by the CV/auth separation.

`auth/db/*.py` are one-shot Python migration helpers kept for history
(`migrate.py`, `migrate_audit_fields.py`, `migrate_iam_fields.py`, `migrate_security_audit.py`,
`migrate_all_tables_audit.py`, `upgrade_rbac.py`, `clean_roles.py`). `MIGRATIONS.sql` is the
authoritative, current list.

---

## 9. Running it

### Local development

```powershell
cd Backend
copy .env.local.example .env.local
# edit .env.local (SENTIO_DB_URL, JWT_SECRET_KEY, MFA_ENCRYPTION_KEY, …)
# Set up PostgreSQL in pgAdmin — see .env.local.example (bottom section)

pip install -r requirements.txt          # stakeholder/auth only
python wsgi_auth.py                      # auth service, no CV libraries needed

pip install -r requirements-cv.txt       # add the CV stack
python -m cv_analysis.app                # CV service on CV_PORT (5002)
python test_db.py                        # or both in one process on PORT (5001)
```

`.env` holds production values; `.env.local` overrides it and is gitignored.
`FLASK_ENV=development` gives localhost CORS, non-`Secure` cookies, and relaxed checks.
Default port is **5001** (`PORT` overrides).

### Production

Never run `python test_db.py` in production — Flask's built-in server is single-process and not
hardened for concurrent/untrusted traffic. Use Gunicorn behind nginx (`nginx/nginx.conf` proxies to
`127.0.0.1:5000`):

```bash
cd Backend

# combined auth + CV (current topology, unchanged URLs)
pip install -r requirements.txt -r requirements-cv.txt
gunicorn -c gunicorn_config.py test_db:app

# or split, once you want the CV stack off the auth hosts:
pip install -r requirements.txt   && gunicorn -c gunicorn_config.py wsgi_auth:app
pip install -r requirements-cv.txt && gunicorn -c gunicorn_config.py cv_analysis.app:app
```

`PORT` (default 5000 in `gunicorn_config.py`) must match nginx's `upstream auth_api` block. Set
`FLASK_ENV=production` and fill in `.env` per `.env.example` — `auth/startup_checks.py` will refuse
to start if `JWT_SECRET_KEY` / `MFA_ENCRYPTION_KEY` / `SESSION_COOKIE_SECURE` / HTTPS settings are
missing or weak. Set `RATELIMIT_STORAGE_URI=redis://...` so Flask-Limiter limits are shared across
workers — with the default `memory://` storage each worker enforces limits independently, letting a
client multiply its effective rate limit by the worker count.

`preload_app` is intentionally `False`: TensorFlow/MediaPipe/dlib initialise native state at import
time that does not survive `fork()`, so each worker pays the ~15s import cost itself.

### Tests

```powershell
cd Backend
pytest
```

`tests/conftest.py` builds the app via `create_app(testing=True)` → `create_auth_app(testing=True)`
— auth/API routes without the analysis stack. The suite is security-focused:
`test_authorization.py` (scope/IDOR), `test_csrf.py`, `test_jwt_revocation.py`, `test_mfa.py`,
`test_rate_limiting.py`, `test_refresh_token.py` (rotation + reuse), `test_hibp.py`,
`test_startup.py` (production guardrails), `test_platform_routes_auth.py` (every CV platform route
is actually guarded), `test_security_integration.py`, `test_security_audit_fixes.py`,
`test_auth_security_extras.py`, and `test_service_boundary.py` (the auth service must start with
no CV library loaded, and `auth/` must never import `cv_analysis`).

### Other folders in the repo

- `auth-backend/` at the repo root is an older auth-only prototype; do not use it for this product.
- `devcode/sentio_mind_app.py` is archived dev code; production runs the Backend entry points above.

---

## 10. Security model summary

Defences currently in place, and where each lives:

| Threat | Control | File |
|---|---|---|
| Credential stuffing / brute force | per-(email,ip) and per-ip lockout, fail-closed | `helpers/rate_limit_helper.py` |
| Endpoint abuse | Flask-Limiter, per-user or per-IP, Redis-backed | `middleware/rate_limiter.py` |
| Account enumeration | identical responses + dummy bcrypt on unknown email; signup/forgot-password always succeed | `services/auth_service.py` |
| Stolen access token | 15-min expiry, `jti` blocklist checked fail-closed, live DB status re-check per request | `helpers/jwt_helper.py`, `middleware/auth_middleware.py` |
| Stolen refresh token | opaque + hashed at rest, one-time rotation, family revocation on reuse, device-hash binding | `services/refresh_token_service.py` |
| XSS token theft | access token never persisted; refresh cookie HttpOnly; strict CSP | `helpers/cookie_helper.py`, `common/http.py` |
| CSRF | double-submit cookie + HMAC token bound to user id | `middleware/csrf.py` |
| Weak / breached passwords | 10-char policy incl. 72-byte cap, bcrypt cost 12, HIBP k-anonymity with strict mode | `helpers/password_helper.py`, `services/hibp_service.py` |
| Privilege escalation | DB-backed permission check per request, Super-Admin-only admin-tier assignment, `MAX_SUPER_ADMINS=2` | `middleware/auth_middleware.py`, `services/user_service.py` |
| IDOR / cross-school data access | scope model + per-row `assert_person_access` + list filtering | `services/authorization_service.py` |
| Tampered audit trail | append-only DB trigger; audit failures never break requests | `helpers/audit_helper.py` |
| Info leakage in errors | production error messages matching `Error\|Exception\|Traceback\|psycopg2` are replaced | `helpers/response_helper.py` |
| SQL injection | every query parameterised via psycopg2 (`%s`), no string interpolation | `queries/*.py` and inline SQL |
| Spoofed client IP | ProxyFix + `X-Real-IP`/`X-Forwarded-For` precedence, `TRUSTED_PROXY_COUNT` | `helpers/request_helper.py` |
| Session sprawl | max 10 active sessions, oldest revoked first | `services/auth_service.py` |
| Secret misconfiguration | import-time `validate_config` + `run_startup_checks` hard failures | `config.py`, `startup_checks.py` |

`SECURITY_CHANGELOG.md` tracks the `SEC-0xx` fix ids referenced in code comments;
`CHANGES.md` tracks broader changes.

---

## 11. Conventions to follow when extending this code

- **New endpoint** → blueprint in `auth/routes/`, logic in `auth/services/`, SQL in `auth/queries/`.
- **Decorator order**: rate limit → `@require_auth` → `@require_permission` → view.
  (`admin_routes.py` puts the limit outermost; `user_routes.py` has no per-route limit and relies on
  the global default.)
- Services return dicts, never Flask responses. Errors are `{"error": str, "status": int}`.
- Always `release_db_connection(conn)` in `finally`; commit explicitly (`autocommit` is off).
- Anything that returns a user must go through `sanitize_user_output()`.
- Any state change worth investigating later gets a `log_activity(...)` call with a deliberate
  severity (`INFO` routine, `WARNING` suspicious/security-relevant, `CRITICAL` privileged or
  attack-indicating).
- New role? Add it to `auth/constants/roles.py` **and** `auth/db/seed.sql`.
- New schema change? Append an idempotent block to `MIGRATIONS.sql`.
- Never log a raw password, temp password, reset token, refresh token, or TOTP secret.
