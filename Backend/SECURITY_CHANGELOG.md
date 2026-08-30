# Security Changelog — Sentio Mind Auth Hardening

## Critical Fix

- **JWT decode errors as strings** — `decode_token` now raises `TokenExpiredError` / `TokenInvalidError`; middleware no longer relies on `isinstance(decoded, str)`.
- **Refresh tokens as access tokens** — Middleware enforces `payload["type"] == "access"`.
- **Unauthenticated analysis/report routes** — `/run_analysis`, `/get_report`, `/pin_profile`, `/update_person_name`, `/update_person_photo`, `/delete_person`, `/system_info` now require `@require_auth` and appropriate RBAC permissions.
- **Exception leakage to clients** — `error_response` redacts internal details in production; service layers and `test_db.py` routes return generic 500 messages.
- **Broken `auth/db/connection.py`** — Removed dependency on non-existent `DATABASE_URL`; re-exports pooled `auth.db_connection`.
- **Temp password in API response** — `approve_user` no longer returns `temp_password` in JSON (email-only).
- **Weak temp password generation** — 12-char `secrets.choice` with symbol alphabet; expiry from `TEMP_PASSWORD_EXPIRY_HOURS`.
- **bcrypt default rounds** — Uses configurable `BCRYPT_ROUNDS` (default 12).
- **SQL injection audit** — All `cur.execute` calls verified parameterized; no f-string SQL found.

## Hardening

- **Config validation** — `validate_config()` on boot: production secret length, default JWT secret ban, SMTP password in production.
- **Rate limiting** — `login_attempts` table + in-memory fallback; lockout via `MAX_LOGIN_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES`.
- **JWT claims** — `jti`, `iss` (`sentio-mind-auth`), `aud` (`sentio-mind-api`); `SUPPORTED_ALGORITHMS = ["HS256"]` only.
- **Token revocation** — `revoked_tokens` table; middleware checks `is_token_revoked(jti)`; logout revokes access `jti`.
- **Middleware** — Bearer header only; audit on token failures; generic 500 logging with `exc_info=True`; pooled DB release.
- **Password policy** — `validate_password_strength` + optional HaveIBeenPwned k-anonymity check on register/change/create/update.
- **Input validation** — `validation_helper`: email (RFC), string sanitization, NUL rejection, `mask_sensitive` for logs.
- **Response sanitization** — `sanitize_user_output` strips `password_hash`, audit fields, maps temp expiry to boolean.
- **Sessions** — Max 10 active sessions; device fingerprint SHA-256; suspicious refresh IP logging (non-blocking).
- **Logout** — `revoke_all` revokes all user sessions; access token revocation on logout.
- **Super Admin cap** — Maximum 2 Super Admin accounts enforced on role assignment.
- **Audit** — `severity` column (INFO/WARNING/CRITICAL); append-only DB trigger; removed meaningless `updated_by` on insert.
- **CORS** — Driven by `ALLOWED_ORIGINS` env var.
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, HSTS, CSP, Referrer-Policy, Permissions-Policy.
- **DB pool** — `ThreadedConnectionPool` (2–10), `connect_timeout=5`, `statement_timeout=30s`, slow-query warning.
- **Image upload** — `/update_person_photo`: 2MB max, JPEG/PNG magic-byte validation.
- **Logging** — Replaced `print()` in auth paths; `%s` style logging; no secrets in logs.

## New Feature

- **`auth/helpers/rate_limit_helper.py`** — DB-backed brute-force protection with memory fallback.
- **`auth/helpers/validation_helper.py`** — Centralized input validation and JWT log masking.
- **`get_audit_logs_for_user()`** — Per-user audit query for `/api/audit-logs?user_id=`.
- **`pre_flight_check()`** — Startup validation and structured boot logging in `test_db.py`.
- **`MIGRATIONS.sql`** — Consolidated schema changes for operators.
- **Dependencies** — `email-validator`, `Flask-Talisman` (headers via `@app.after_request`), `python-dotenv` pinned in requirements.
