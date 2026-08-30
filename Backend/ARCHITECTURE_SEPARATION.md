# CV / Stakeholder-Auth Separation

Record of the architectural split that isolated the CV / behavioural-intelligence
system from the stakeholder / authentication backend. Nothing was deleted: every
route, permission, role, audit event and CV capability that existed before still
exists, in a named place.

---

## A. Before / After architecture

### Before

```
Backend/
└── test_db.py   (2832 lines)  ← ONE module
    ├── import cv2 / numpy                        (module top)
    ├── Flask app + CORS + rate limiter + CSP     (auth infra)
    ├── auth blueprint registration (9 blueprints)
    ├── init_auth_db()
    ├── import deepface / mediapipe / face_recognition / mtcnn
    ├── CV paths: input_videos, profiles, snapshots, analysis_results
    ├── CV DB writes: persons / videos / frames / analysis / traits
    ├── ~1200 lines of CV pipeline
    ├── ~1000 lines of dashboard HTML
    ├── 7 CV HTTP routes + /health + /
    └── pre_flight_check() + __main__
```

Coupling that existed:

| Coupling | Effect |
|---|---|
| `test_db.py` is both the auth bootstrap and the CV pipeline | Importing the auth app imported TensorFlow, dlib, MediaPipe (~15 s, GBs of RAM) |
| `auth/routes/analysis_routes.py` read `analysis_results/` | The auth package depended on CV output files |
| `auth/routes/person_routes.py` read the CV person registry | Same |
| `AuthConfig.RATELIMIT_ANALYSIS` | CV route tuning lived in the auth config class |
| `requirements.txt` | Installing the auth service pulled the entire CV stack |
| `create_app(testing=True)` | The only CV-free path, and it was test-only |

### After

```
Backend/
├── app_factory.py            ← create_auth_app()  — STAKEHOLDER/AUTH, zero CV imports
├── wsgi_auth.py              ← auth-only entry (gunicorn wsgi_auth:app)
│
├── common/http.py            ← shared HTTP hardening (ProxyFix, CORS headers, CSP)
│
├── auth/                     ← unchanged stakeholder/auth package (see §C)
│
├── cv_analysis/              ← CV SYSTEM, self-contained
│   ├── app.py                ← create_cv_app() — standalone CV service
│   ├── config.py             ← CV paths / thresholds / CV rate limit
│   ├── libraries.py          ← the ONLY module importing cv2/DeepFace/MediaPipe/MTCNN
│   ├── state.py              ← person_database, pinned_profiles, analysis_cache
│   ├── db.py                 ← persons/videos/frames/analysis/traits writes
│   ├── pipeline.py           ← detection → emotion/posture/gaze → traits → report
│   ├── dashboard.py          ← operator dashboard HTML
│   ├── routes.py             ← cv_bp: /run_analysis, /get_report, /pin_profile, …
│   ├── routes_analysis.py    ← analysis_bp (moved from auth/routes/)
│   └── routes_person.py      ← person_bp   (moved from auth/routes/)
│
├── test_db.py (73 lines)     ← combined deployment: create_auth_app() + CV blueprints
├── requirements.txt          ← auth only
└── requirements-cv.txt       ← CV stack
```

Three runnable applications, same code:

| Command | What it serves |
|---|---|
| `gunicorn -c gunicorn_config.py wsgi_auth:app` | Stakeholder/auth only — no CV libraries installed or imported |
| `gunicorn -c gunicorn_config.py cv_analysis.app:app` | CV only — authenticates against the existing auth stack |
| `gunicorn -c gunicorn_config.py test_db:app` | Both in one process (current production topology, unchanged URLs) |

### What remains shared

| Shared thing | Owner | Why it is shared |
|---|---|---|
| `auth.middleware.auth_middleware` (`@require_auth`, `@require_permission`) | Auth | CV endpoints must keep using the *existing* authn/authz. Duplicating it would mean a second JWT implementation — explicitly forbidden. |
| `auth.services.authorization_service` (scope model, `assert_person_access`) | Auth | Row-level scope is an auth concept. CV consumes it; it does not define it. |
| `auth.middleware.rate_limiter` (Flask-Limiter singleton) | Auth | One limiter, one Redis store, one 429 audit path. |
| `auth.db_connection` pool | Auth | CV borrows the pool instead of opening a second one against the same PostgreSQL instance. Isolated behind `cv_analysis/db.py`. |
| `auth.config` (`FRONTEND_URL`, `ALLOWED_ORIGINS`) | Auth | Deployment-level settings, not CV settings. |
| `common/http.py` | Neither | Pure infrastructure so neither service imports the other for CSP/ProxyFix. |

---

## B. CV dependency inventory

### Libraries (now `requirements-cv.txt`, previously `requirements.txt`)

`opencv-python`, `numpy`, `mediapipe`, `deepface`, `tensorflow`, `face-recognition`,
`Pillow`, and `mtcnn` (previously imported but never declared — now declared).

### Imports

| Import | Was | Now |
|---|---|---|
| `cv2` | `test_db.py:13` | `cv_analysis/libraries.py` |
| `numpy` | `test_db.py:17` | `cv_analysis/libraries.py` |
| `deepface.DeepFace` | `test_db.py:171` | `cv_analysis/libraries.py` |
| `mediapipe` (`mp_pose`, `mp_face_mesh`) | `test_db.py:178` | `cv_analysis/libraries.py` |
| `face_recognition` | `test_db.py:187` | `cv_analysis/libraries.py` |
| `mtcnn.MTCNN` | `test_db.py:194` | `cv_analysis/libraries.py` |

`cv_analysis/libraries.py` is the single import site. Every other CV module imports
from it, so the heavy-import cost and the graceful-degradation flags
(`DEEPFACE_AVAILABLE`, `MEDIAPIPE_AVAILABLE`, `FACE_RECOGNITION_AVAILABLE`,
`MTCNN_AVAILABLE`) have exactly one definition.

### Modules / functions

| Function (old `test_db.py` lines) | Now |
|---|---|
| `enhance_frame_for_cctv`, `enhance_face_crop`, `upscale_for_detection`, `calculate_frame_difference`, `extract_intelligent_frames` (389–487) | `cv_analysis/pipeline.py` |
| `get_face_encoding_from_crop`, `detect_all_faces_in_frame` (488–684) | `cv_analysis/pipeline.py` |
| `analyze_gaze_and_attention` (685–840) | `cv_analysis/pipeline.py` |
| `analyze_posture_for_person` (841–927) | `cv_analysis/pipeline.py` |
| `analyze_face_texture_traits`, `analyze_emotion_full`, `compute_10_trait_wellbeing` (928–1063) | `cv_analysis/pipeline.py` |
| `create_profile_image`, `score_frame_quality`, `calculate_person_similarity`, `match_or_create_person` (1064–1265) | `cv_analysis/pipeline.py` |
| `analyze_frame`, `analyze_video_file`, `analyze_date_folder`, `analyze_all_dates` (1266–1461) | `cv_analysis/pipeline.py` |
| `generate_multi_day_report` (1463–1570) | `cv_analysis/pipeline.py` |
| `HTML_TEMPLATE` (1572–2573) | `cv_analysis/dashboard.py` |
| `db_upsert_person`, `db_insert_video`, `db_insert_frame`, `db_insert_analysis_with_traits`, `_db_available`, `_USE_DB` (223–370) | `cv_analysis/db.py` |
| `person_database`, `analysis_cache`, `pinned_profiles`, `_db_lock` (375–383) | `cv_analysis/state.py` |
| `_clahe` (382) | `cv_analysis/libraries.py` |
| `SIMILARITY_THRESHOLD`, `FRAME_DIFFERENCE_THRESHOLD` (379–380) | `cv_analysis/config.py` |
| `INPUT_VIDEOS_DIR`, `PROFILES_DIR`, `SNAPSHOTS_DIR`, `ANALYSIS_DIR` (205–212) | `cv_analysis/config.py` |
| `MAX_IMAGE_BYTES` (2585) | `cv_analysis/config.py` |

### Routes

| Route | Was | Now |
|---|---|---|
| `GET /` (dashboard) | `test_db.py:2578` | `cv_analysis/routes.py` (`cv_bp`) |
| `POST /run_analysis` | `test_db.py:2588` | `cv_analysis/routes.py` |
| `GET /get_report` | `test_db.py:2602` | `cv_analysis/routes.py` |
| `POST /pin_profile` | `test_db.py:2623` | `cv_analysis/routes.py` |
| `POST /update_person_name` | `test_db.py:2662` | `cv_analysis/routes.py` |
| `POST /update_person_photo` | `test_db.py:2704` | `cv_analysis/routes.py` |
| `POST /delete_person` | `test_db.py:2749` | `cv_analysis/routes.py` |
| `GET /system_info` | `test_db.py:2791` | `cv_analysis/routes.py` |
| `GET /analysis/report`, `POST /analysis/run` | `auth/routes/analysis_routes.py` | `cv_analysis/routes_analysis.py` |
| `GET /person/<id>`, `POST /person/<id>/access-check` | `auth/routes/person_routes.py` | `cv_analysis/routes_person.py` |

URLs are byte-for-byte unchanged, so `nginx/nginx.conf` needed no edit.

### Configuration

CV settings moved out of `auth/config.py` and the `test_db.py` module body into
`cv_analysis/config.py`, all now overridable:

`CV_INPUT_VIDEOS_DIR`, `CV_PROFILES_DIR`, `CV_SNAPSHOTS_DIR`, `CV_ANALYSIS_DIR`,
`CV_SIMILARITY_THRESHOLD`, `CV_FRAME_DIFFERENCE_THRESHOLD`, `CV_RATELIMIT_ANALYSIS`,
`CV_MAX_IMAGE_BYTES`, `CV_DATABASE_URL`, `CV_PORT`.

Defaults are identical to the previous hard-coded values, so behaviour is unchanged
when none are set.

### Filesystem

`input_videos/`, `profiles/person_database.json`, `analysis_results/`, `snapshots/`
— all CV-owned, all now addressed only through `cv_analysis/config.py`.

### Database

CV tables `persons`, `videos`, `frames`, `analysis`, `traits` (default/public schema).
They are **not** in `auth/db/schema.sql`, which defines only the `auth_enabler`
schema. No schema change was made by this refactor.

---

## C. Stakeholder / auth inventory (unchanged, stays put)

| Area | Files |
|---|---|
| Bootstrap | `app_factory.py`, `wsgi_auth.py`, `auth/env_loader.py`, `auth/startup_checks.py` |
| Configuration | `auth/config.py` (JWT, MFA, SMTP, CORS, cookies, HIBP, rate limits, password policy) |
| Authentication | `auth/routes/auth_routes.py`, `auth/services/auth_service.py`, `auth/services/refresh_token_service.py`, `auth/helpers/jwt_helper.py`, `auth/helpers/password_helper.py`, `auth/helpers/cookie_helper.py`, `auth/services/hibp_service.py` |
| MFA | `auth/routes/mfa_routes.py`, `auth/services/mfa_service.py` |
| Authorization | `auth/middleware/auth_middleware.py`, `auth/services/authorization_service.py`, `auth/constants/roles.py`, `auth/services/role_service.py`, `auth/routes/role_routes.py`, `auth/queries/role_queries.py` |
| Users | `auth/routes/user_routes.py`, `auth/services/user_service.py`, `auth/queries/user_queries.py` |
| Admin | `auth/routes/admin_routes.py` (pending users, approve, reject) |
| Sessions | `auth/db/schema.sql` `user_sessions`, refresh-token rotation/revocation |
| Audit | `auth/routes/audit_routes.py`, `auth/helpers/audit_helper.py`, append-only `auth_enabler.audit_logs` |
| Security | `auth/middleware/csrf.py`, `auth/middleware/rate_limiter.py`, `auth/helpers/rate_limit_helper.py`, `auth/routes/security_routes.py`, `common/http.py` |
| Data | `auth/db_connection.py`, `auth/db/schema.sql`, `auth/db/seed.sql`, migrations |

Roles are untouched: Super Admin, Secondary Admin, Normal Admin, Principal,
Psychologist, Class Teacher, Behaviour Scientist. `mobile_super_admin` /
`mobile_secondary_admin` were **not** added — Mobile Admin stays a separate concern.

---

## D. Dependency boundary

```
Stakeholder/Auth  →  CV      : NONE
CV                →  Auth    : 5 explicit, one-directional dependencies
```

**`Stakeholder/Auth → CV` is empty.** `app_factory.py` imports only `flask`,
`flask_cors`, `auth.*` and `common.http`. `auth/` contains zero references to
`cv_analysis` and zero CV library imports. Enforced by
`tests/test_service_boundary.py::test_no_cv_imports_inside_shared_packages` and
`::test_auth_app_starts_without_cv_libraries`.

**`CV → Auth`**, each deliberate:

| # | Dependency | Site | Why | Cost of extraction |
|---|---|---|---|---|
| 1 | `@require_auth`, `@require_permission` | `cv_analysis/routes*.py` | CV endpoints must keep the existing JWT + DB-backed permission check. A second implementation is forbidden. | Extracted service calls the same middleware over the same JWT/DB, or the auth service exposes an introspection endpoint. |
| 2 | `AuthorizationService`, `_load_user_scope`, `school_name_to_id` | `cv_analysis/routes*.py` | Row-level scope is auth-owned; CV applies it to CV data. | Same package import, or a thin `/api/me/scope` call. |
| 3 | `limit_authenticated` (Flask-Limiter) | `cv_analysis/routes*.py` | One limiter instance, one Redis store, one audited 429 path. | Own limiter with the same Redis URI. |
| 4 | `auth.db_connection` pool | `cv_analysis/db.py` (2 functions) | Avoids a second pool to the same database today. | Point the two helpers at `CV_DATABASE_URL`. Nothing else changes. |
| 5 | `auth.config` (`FRONTEND_URL`, `ALLOWED_ORIGINS`) | `cv_analysis/routes.py`, `cv_analysis/app.py` | Deployment-level values, not CV values. | Read from env directly. |

No circular dependency exists: the arrow only ever points CV → Auth.

---

## E. Endpoint classification

Every route in the combined app, classified by trace rather than by name.

| Endpoint | Owner | Reason |
|---|---|---|
| `/api/auth/*` (`auth_bp`) | Stakeholder/Auth | Signup, login, logout, refresh, password reset/change, temp-password flow |
| `/api/auth/mfa/*` (`mfa_bp`) | Stakeholder/Auth | TOTP enrol/verify/disable |
| `/api/admin/*` (`admin_bp`) | Stakeholder/Auth | Pending registrations, approve, reject |
| `/api/users*`, `/api/…` (`user_bp`) | Stakeholder/Auth | User CRUD, status handling |
| `/api/roles*`, permission endpoints (`role_bp`) | Stakeholder/Auth | RBAC administration, role assignment |
| `/api/audit-logs/*` (`audit_bp`) | Stakeholder/Auth | Append-only audit reads |
| `/api/csp-report` (`security_bp`) | Stakeholder/Auth | Browser security reporting |
| `/health` | Stakeholder/Auth | Liveness. Must not depend on CV libraries — moved to `app_factory.py` so the auth service answers it with the CV stack absent. |
| `POST /run_analysis` | CV | Executes the CCTV pipeline in-process |
| `GET /system_info` | CV | Reports CV library availability |
| `GET /` | CV | Operator dashboard for CV output |
| `GET /get_report` | CV (stakeholder-facing) | Serves CV-generated `multi_day_report.json`; scope-filtered via auth |
| `GET /analysis/report` | CV (stakeholder-facing) | Same data, scoped, under `/analysis` |
| `POST /analysis/run` | CV | 501 stub pointing at `/run_analysis` |
| `POST /pin_profile` | CV (stakeholder-facing) | Pins a CV-generated profile; writes to `analysis_results/` |
| `GET /person/<id>`, `POST /person/<id>/access-check` | CV (stakeholder-facing) | CV-generated person profiles, not identity records |
| `POST /update_person_name`, `POST /update_person_photo`, `POST /delete_person` | CV | Edit CV-derived person profiles in `profiles/` + `analysis_results/`. Named `person`/`users.*` but they never touch `auth_enabler.users` — traced, not assumed. |

Judgement calls worth stating:

* `/update_person_name` and `/delete_person` require `users.write` / `users.delete`.
  Those permission names read like identity management, but the handlers operate
  purely on the CV person registry. Permissions were **not** renamed — that would be
  a product change. They moved with the CV code as-is.
* `/health` was previously defined next to the CV routes but has no CV dependency,
  so it stayed with the auth service.
* `/analysis/*` and `/person/*` are stakeholder-facing but CV-owned: they serve only
  CV-produced data, so keeping them in `auth/` would have left the auth package
  reading `analysis_results/`.

---

## F. Tests

| | Before | After |
|---|---|---|
| Tests collected | 60 | 65 |
| Passed | 60 | 65 |
| Failed | 0 | 0 |
| Wall clock | 72.4 s | 39.5 s |

* **Failures caused by the refactor:** none.
* **Pre-existing failures:** none.
* Runtime nearly halved because `create_app(testing=True)` no longer imports
  TensorFlow/dlib/MediaPipe for the auth suite.

Five tests added, all in `tests/test_service_boundary.py`:

1. `test_auth_app_starts_without_cv_libraries` — subprocess builds the auth app and
   asserts `cv2`, `deepface`, `mediapipe`, `face_recognition`, `mtcnn`, `tensorflow`
   are absent from `sys.modules`.
2. `test_auth_app_serves_health_without_cv_stack` — `/health` returns 200 in that
   same CV-free process.
3. `test_auth_app_registers_no_cv_routes` — the auth app exposes none of the CV URLs.
4. `test_no_cv_imports_inside_shared_packages[auth]` — static check on `auth/`.
5. `test_no_cv_imports_inside_shared_packages[common]` — static check on `common/`.

CV tests were not deleted. `tests/test_platform_routes_auth.py` (401-on-every-CV-route)
and the person-scope IDOR tests in `tests/test_security_audit_fixes.py` still exercise
the CV routes through `test_db.app`, which is the combined deployment.

Coverage confirmed unchanged for: login, signup/access request, approval, rejection,
password flow, MFA, refresh, logout, role assignment, permission enforcement, scope
enforcement, audit logging, rate limiting, security middleware, user management,
admin routes.

---

## Success criteria

| # | Criterion | Status |
|---|---|---|
| 1 | Stakeholder/auth backend starts without the CV stack | Yes — `wsgi_auth:app`, verified by test |
| 2 | Authentication works independently of CV libraries | Yes — 65 tests pass, `/health` 200 with no CV modules loaded |
| 3 | RBAC and permissions still work | Yes — `auth/` untouched |
| 4 | Stakeholder roles intact | Yes — `auth/constants/roles.py` and `seed.sql` untouched |
| 5 | Admin approval and user management intact | Yes — `admin_bp` / `user_bp` untouched |
| 6 | Audit/security intact | Yes — audit, CSRF, limiter, CSP headers unchanged |
| 7 | CV functionality still works | Yes — same routes, same pipeline, same URLs; runs standalone via `cv_analysis.app:app` |
| 8 | No unexplained circular dependency | Yes — §D, one direction only |
| 9 | CV deps not required by the stakeholder service | Yes — `requirements.txt` / `requirements-cv.txt` |
| 10 | CV extractable later without rewriting auth | Yes — 5 documented seams, 4 of them one-line swaps |

## What was explicitly NOT done

* No PostgreSQL schema change, no migration, no data movement.
* No microservice, message queue, new API or new database.
* No RBAC/JWT/permission redesign; no role renamed, added or removed.
* No `mobile_super_admin` / `mobile_secondary_admin`.
* No endpoint removed and no endpoint made less protected — every CV route kept its
  `@require_auth` + `@require_permission` + rate limit decorators verbatim.
