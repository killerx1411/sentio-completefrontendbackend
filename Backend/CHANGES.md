# Security Hardening — CHANGES

## Task 1 — Global Rate Limiting

| File | Description |
|------|-------------|
| `auth/config.py` | Rate-limit settings (`RATELIMIT_*`, per-endpoint constants) |
| `auth/middleware/rate_limiter.py` | Flask-Limiter init, 429 handler, audit on breach |
| `test_db.py` | Application entry point; limiter init and analysis route limits |
| `auth/routes/auth_routes.py` | Per-route limits on login/refresh/logout/reset-password |
| `auth/routes/admin_routes.py` | Admin blueprint limits (120/min per user) |
| `auth/routes/analysis_routes.py` | Analysis limits (60/min per user) |
| `auth/routes/person_routes.py` | Person routes limits (60/min per user) |
| `auth/routes/security_routes.py` | CSP report limit (100/min) |
| `requirements.txt` | `Flask-Limiter`, `limits`, `redis` |
| `tests/test_rate_limiting.py` | Burst 429, key separation, audit tests |

## Task 2 — CSRF Protection

| File | Description |
|------|-------------|
| `auth/middleware/csrf.py` | Redis-backed CSRF generate/validate/invalidate |
| `auth/helpers/redis_client.py` | Redis with in-memory fallback |
| `auth/constants/cookies.py` | `REFRESH_COOKIE` constant (breaks import cycles) |
| `auth/routes/auth_routes.py` | `csrf_token` on login; `@csrf_required` on refresh/logout |
| `Frontend/src/services/authApi.js` | In-memory CSRF header on cookie-auth calls |
| `tests/test_csrf.py` | CSRF header validation tests |

## Task 3 — Resource Scope (IDOR)

| File | Description |
|------|-------------|
| `auth/services/authorization_service.py` | `AuthorizationService`, `scope_required`, school/class/flagged checks |
| `auth/routes/analysis_routes.py` | Scoped report filtering blueprint |
| `auth/routes/person_routes.py` | Per-person scope check routes |
| `test_db.py` | Scope enforcement on report/person mutations |
| `MIGRATIONS.sql` | `school_id`, `class_id` on users |
| `tests/test_authorization.py` | Role scope and IDOR enumeration tests |

## Task 4 — TOTP MFA

| File | Description |
|------|-------------|
| `auth/services/mfa_service.py` | TOTP setup, confirm, recovery codes, disable |
| `auth/routes/mfa_routes.py` | `/api/auth/mfa/*` endpoints |
| `auth/helpers/jwt_helper.py` | `generate_mfa_pending_token` |
| `auth/services/auth_service.py` | MFA branch in login; `complete_login_after_mfa` |
| `auth/middleware/auth_middleware.py` | Reject `mfa_pending` as access token |
| `MIGRATIONS.sql` | `mfa_secret`, `mfa_recovery_codes` columns |
| `requirements.txt` | `pyotp`, `qrcode[pil]`, `cryptography` |
| `tests/test_mfa.py` | MFA flow tests |

## Task 5 — Frontend CSP & Reporting

| File | Description |
|------|-------------|
| `nginx/nginx.conf` | Strict CSP, HSTS, frame/options headers for React static |
| `auth/routes/security_routes.py` | `POST /api/csp-report` → audit log, 204 |
| `Frontend/src/HomePage.jsx` | SECURITY TODO on inline styles |
| `Frontend/src/services/authApi.js` | CSRF token wiring (Task 2) |

## Task 6 — Refresh Token Rotation

| File | Description |
|------|-------------|
| `auth/services/refresh_token_service.py` | Family rotation, reuse detection, device hash |
| `auth/services/auth_service.py` | Login/refresh/logout integration with `refresh_tokens` |
| `auth/helpers/cookie_helper.py` | Unconditional `secure=True` cookies |
| `MIGRATIONS.sql` | `auth_enabler.refresh_tokens` table |
| `tests/test_refresh_token.py` | Rotation and reuse tests |

## Task 7 — Secure Cookies & Startup

| File | Description |
|------|-------------|
| `auth/startup_checks.py` | Production config validation |
| `test_db.py` | `pre_flight_check()` startup checks via `run_startup_checks` |
| `auth/config.py` | `SESSION_COOKIE_*`, `REMEMBER_COOKIE_SECURE` |
| `tests/test_startup.py` | Production/dev startup tests |

## Task 8 — HIBP Circuit Breaker

| File | Description |
|------|-------------|
| `auth/services/hibp_service.py` | `HIBPService` with circuit breaker and cache |
| `auth/config.py` | `STRICT_PASSWORD_BREACH_CHECK`, HIBP timeouts |
| `auth/services/auth_service.py` | Uses `validate_password_not_breached` |
| `auth/helpers/password_helper.py` | Delegates to `HIBPService` |
| `tests/test_hibp.py` | Breach/strict/circuit/cache tests |

## Task 9 — Dependency Security Pipeline

| File | Description |
|------|-------------|
| `.github/workflows/security.yml` | pip-audit, safety, SBOM on push/PR |
| `.github/dependabot.yml` | Weekly pip and Actions updates |
| `.pre-commit-config.yaml` | pip-audit on push |

## Task 10 — Integration Tests

| File | Description |
|------|-------------|
| `tests/conftest.py` | App fixture, DB pool mock |
| `tests/test_security_integration.py` | Cross-cutting auth security tests |
| `pytest.ini` | Pytest configuration |

## Other

| File | Description |
|------|-------------|
| `CHANGES.md` | This file |

---

## CV / stakeholder-auth separation

Architectural split only — no product behaviour, permission, role, schema or endpoint changed.
Full inventory in `ARCHITECTURE_SEPARATION.md`.

| File | Change |
|---|---|
| `app_factory.py` | New. `create_auth_app()` — stakeholder/auth Flask app, zero CV imports |
| `wsgi_auth.py` | New. Auth-only WSGI entry (`gunicorn wsgi_auth:app`) |
| `common/http.py` | New. ProxyFix + CORS header set + security/CSP headers shared by both services |
| `cv_analysis/` | New package. CV libraries, config, state, DB writes, pipeline, dashboard, routes, standalone app |
| `auth/routes/analysis_routes.py` | Moved → `cv_analysis/routes_analysis.py` (serves CV-generated reports) |
| `auth/routes/person_routes.py` | Moved → `cv_analysis/routes_person.py` (serves CV-generated profiles) |
| `test_db.py` | 2832 → 73 lines. Now composes `create_auth_app()` + CV blueprints; same WSGI target, same URLs |
| `requirements.txt` | CV stack removed (auth service installs without OpenCV/TensorFlow/MediaPipe/dlib) |
| `requirements-cv.txt` | New. CV stack, plus `mtcnn` which was imported but never declared |
| `tests/test_service_boundary.py` | New. Fails the build if `auth/` ever imports `cv_analysis` or a CV library |

Test suite: 60 passed before, 65 passed after (5 new boundary tests), 0 failures, 72.4 s → 39.5 s.

## Sentio Mobile Admin — multi-application auth

One authentication authority, many consumer applications. Access tokens, refresh
families and roles are bound to the application they belong to. Full contract in
`MOBILE_ADMIN_INTEGRATION.md`.

| File | Description |
|------|-------------|
| `auth/constants/applications.py` | **New.** Registry of consumer applications (`sentio-b2b`, `sentio-mobile`), per-application JWT audiences |
| `auth/constants/roles.py` | `mobile_super_admin` / `mobile_secondary_admin` roles with `mobile.*` permissions and `MOBILE_*` scopes; per-role application entitlement; `PRIVILEGED_ROLES` (admin tier across all applications) |
| `auth/config.py` | `SERVICE_APPLICATIONS` — which applications' tokens a deployment accepts |
| `auth/helpers/jwt_helper.py` | Per-application `aud`, `app` claim, `expected_application`, `TokenApplicationError` |
| `auth/middleware/auth_middleware.py` | Rejects cross-application tokens; `require_auth(application=…)`, `require_application()` |
| `auth/services/auth_service.py` | Login / MFA completion / refresh enforce role→application entitlement; `LOGIN_DENIED_APPLICATION`, `REFRESH_DENIED_APPLICATION` audit events |
| `auth/services/refresh_token_service.py` | Rotation carries the session's application |
| `auth/routes/auth_routes.py` | `application` on `POST /login`; `GET /introspect` for consumer backends |
| `auth/routes/mfa_routes.py` | MFA completion inherits the pending token's application |
| `auth/routes/{user,role,admin}_routes.py`, `auth/services/user_service.py` | Only a Super Admin may assign Mobile Admin roles |
| `auth/db/migrate_mobile_admin.py` | **New.** Idempotent migration; seeds Mobile RBAC from `ROLE_CONFIG` |
| `auth/db/schema.sql`, `auth/db/seed.sql`, `MIGRATIONS.sql`, `auth/db/clean_roles.py` | `application` columns on sessions/refresh tokens; Mobile roles + `mobile.*` permissions |
| `tests/test_mobile_admin_auth.py` | **New.** Role distinctness, permission-namespace disjointness, token/application binding, login+refresh entitlement, SQL parity |
| `MOBILE_ADMIN_INTEGRATION.md` | **New.** Integration contract for the Mobile Admin backend |

