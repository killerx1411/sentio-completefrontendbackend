# Sentio Mind Frontend

Create React App (React 19 + React Router 7) single-page app. It is the **B2B console** served at
`https://product.sentiomind.in`: stakeholder dashboards (Principal, Psychologist, Class Teacher,
Behaviour Scientist), the B2B administration console, and the **Sentio Mobile Admin** section.

The frontend holds **no database credentials and no secrets**. It talks to two HTTP APIs and
nothing else:

| API | Env var | Production origin | What it serves |
|---|---|---|---|
| B2B auth authority (Flask) | `REACT_APP_AUTH_API_URL` | `https://b2bapi.sentiomind.in` | login, refresh, MFA, RBAC, users, audit |
| Analytics / CV API | `REACT_APP_API_URL` | `https://b2bapi.sentiomind.in` | reports, analysis, person profiles |
| Sentio Mobile backend (FastAPI) | `REACT_APP_MOBILE_ADMIN_API_URL` | `https://api.sentiomind.in` | everything under `/admin/mobile/*` |

> **CRA inlines every `REACT_APP_*` value into the JavaScript bundle at build time.** They are
> public — anyone can read them in devtools. Only origins belong in these files. Never an API key,
> a token, or a database URL.

---

## 1. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Node.js | 18 LTS or 20 LTS (CRA 5 does not build on Node 22+ without warnings) | `node -v` |
| npm | 9+ (ships with Node 18/20) | `npm -v` |
| Backend | `Backend/` running on `http://localhost:5000` — see [`../Backend/README.md`](../Backend/README.md) §9 | `curl http://localhost:5000/health` |
| Mobile backend | *(optional)* FastAPI on `http://localhost:8000`, only for `/admin/mobile/*` pages | `curl http://localhost:8000/health` |
| Firebase CLI | only for deploying | `npm i -g firebase-tools` |

Windows: run everything from **PowerShell**, not cmd.

---

## 2. Start it locally — exact steps

```powershell
cd Frontend

# 1. Install dependencies. Use `npm ci` (reproducible, honours package-lock.json).
npm ci

# 2. Nothing to configure for the default setup — .env.development is committed
#    and already points at localhost:5000 / localhost:8000.
#    Only if you need different ports:
copy .env.development.local.example .env.development.local
#    then edit .env.development.local (it is gitignored and overrides .env.development)

# 3. Start the dev server. Opens http://localhost:3000 automatically.
npm start
```

That is the whole local start. `npm start` compiles in watch mode and hot-reloads on save.

**Before the app is usable you also need the backend up and a user to log in as.** Order:

1. Start PostgreSQL and the Flask backend (`Backend/README.md` §9.1) → `http://localhost:5000`.
2. Confirm `curl http://localhost:5000/health` returns `{"status":"healthy"}`.
3. Create a local user — either sign up at `http://localhost:3000/signup` (local dev sets
   `ENABLE_OPEN_REGISTRATION=true`) or insert a Super Admin directly
   (`Backend/README.md` §9.4 "First admin user").
4. Start this app with `npm start` and sign in at `http://localhost:3000`.

### Which env file wins

CRA loads these in order; later entries override earlier ones:

| File | Loaded by | Committed? | Purpose |
|---|---|---|---|
| `.env` | every command | ignored by git | legacy/local scratch — avoid |
| `.env.development` | `npm start` | **yes** | localhost API origins — the default dev setup |
| `.env.development.local` | `npm start` | no (gitignored) | your machine-specific overrides |
| `.env.production` | `npm run build` | **yes** | production origins + `GENERATE_SOURCEMAP=false` |
| `.env.example` | nothing | **yes** | the documented template |

CRA reads env files **only at process start**. After editing any of them, stop `npm start`
(Ctrl+C) and start it again — a hot reload will not pick up the change.

---

## 3. Where things live

```
Frontend/
├── public/index.html            ← HTML shell
├── firebase.json                ← Hosting config: SPA rewrite, cache headers, CSP/HSTS
├── .env.development             ← npm start   → localhost:5000 / :8000
├── .env.production              ← npm run build → b2bapi./api.sentiomind.in
└── src/
    ├── index.js                 ← ReactDOM root
    ├── App.js                   ← the entire route table (createBrowserRouter)
    ├── config/env.js            ← the ONLY place process.env is read
    ├── constants/
    │   ├── roles.js             ← mirrors Backend auth/constants/roles.py
    │   └── applications.js      ← sentio-b2b / sentio-mobile token boundary
    ├── context/SessionContext.jsx  ← signed-in user, refresh loop, logout
    ├── components/ProtectedRoute.jsx ← per-route role gate
    ├── services/
    │   ├── authApi.js           ← login, refresh rotation, CSRF double-submit, MFA
    │   ├── adminApi.js          ← B2B admin/user/audit calls
    │   └── mobileAdminApi.js    ← Mobile backend /api/admin calls
    ├── utils/api.js             ← authenticated fetch against REACT_APP_API_URL
    ├── admin/                   ← B2B console pages (/admin/*)
    ├── mobile/                  ← Mobile Admin section (/admin/mobile/*)
    └── *.jsx                    ← per-role dashboards (see routes below)
```

### Routes and who may reach them

Defined in `src/App.js`; role names come from `src/constants/roles.js`.

| Path | Allowed roles |
|---|---|
| `/` | public (login) |
| `/signup`, `/reset-password` | public |
| `/BehaviourAnalyst` | Behaviour Scientist |
| `/PrincipleDashboard` | Principal |
| `/SchoolCounsellorDashboard` | Psychologist |
| `/TeacherDashboard` | Class Teacher |
| `/admin` | Super / Secondary / Normal Admin |
| `/admin/pending` | Super Admin only |
| `/admin/users`, `/admin/users/:id`, `/admin/audit-logs` | Super / Secondary / Normal Admin |
| `/admin/mobile/*` | `mobile_super_admin`, `mobile_secondary_admin` **only** |
| anything else | redirect to `/` |

B2B admin roles and Mobile Admin roles are **disjoint**. A B2B admin cannot open
`/admin/mobile/*`, and a Mobile admin cannot open the B2B user pages. The backends enforce the
same split by token application (`sentio-b2b` vs `sentio-mobile`), so the UI gate is defence in
depth, not the control.

### How a session works

- The **access token lives in memory only** (`services/authApi.js`) — never `localStorage`, so an
  XSS cannot read it back after reload.
- The **refresh token is an HttpOnly cookie** on `Path=/api/auth`, set by the backend. JavaScript
  cannot read it.
- A readable `sentio_csrf` cookie is echoed back in a header on state-changing calls
  (double-submit CSRF).
- On page load, and every ~15 minutes, `authApi` calls the refresh endpoint to rotate the access
  token. Reusing a rotated refresh token revokes the whole family server-side.

This is why local dev **must** hit the backend over a consistent origin: mixing `localhost` and
`127.0.0.1` gives you two cookie jars and the session will appear to drop.

---

## 4. Tests

```powershell
cd Frontend
npm test                # interactive watch mode (CRA/Jest)
npm test -- --watchAll=false   # single run, for CI
```

`src/services/authApi.test.js` covers the token/refresh logic; `src/App.test.js` is the smoke test.

---

## 5. Production build

```powershell
cd Frontend
npm ci
npm run build           # reads .env.production, writes ./build
```

The build must be produced **with `.env.production` present** — that file supplies the
`b2bapi.sentiomind.in` / `api.sentiomind.in` origins. A build made without it produces a bundle
that calls relative `/api/...` paths on the static host and 404s.

Verify the bundle before deploying:

```powershell
# should print the two production origins, and NOTHING containing localhost
Select-String -Path build\static\js\main.*.js -Pattern "b2bapi\.sentiomind\.in|api\.sentiomind\.in" | Select-Object -First 2
Select-String -Path build\static\js\main.*.js -Pattern "localhost"      # expect no matches
```

`GENERATE_SOURCEMAP=false` is set on purpose: source maps republish the full readable frontend
source, including the shape of every admin API call.

---

## 6. Deploy (Firebase Hosting)

Full production procedure, DNS and GoDaddy steps live in
[`../DEPLOYMENT_PRODUCTION.md`](../DEPLOYMENT_PRODUCTION.md) §10–§13. The short form:

```bash
cd Frontend
firebase login                       # first time only
firebase use --add <gcp-project-id>  # first time only, writes .firebaserc

npm ci
npm run build
firebase deploy --only hosting --project <gcp-project-id>
```

Rollback:

```bash
firebase hosting:releases:list
firebase hosting:rollback
```

`firebase.json` is part of the security posture, not just build config:

- **SPA rewrite** `**` → `/index.html` — without it, refreshing `/admin/mobile/experts` asks the
  static host for a file that does not exist and returns 404.
- `/static/**` cached `immutable` for a year (filenames are content-hashed); `index.html` is
  `no-store`, so a deploy never leaves a browser pinned to a bundle whose assets are gone.
- HSTS, `X-Frame-Options: DENY`, `nosniff`, Referrer-Policy, Permissions-Policy.
- CSP with `connect-src` listing **exactly** `https://b2bapi.sentiomind.in` and
  `https://api.sentiomind.in`. **Adding or changing an API origin means editing that header too**,
  or the browser silently blocks the call.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `REACT_APP_API_URL is not configured` | env file missing or app started before it existed | check `.env.development` exists, restart `npm start` |
| Login returns CORS error | backend `ALLOWED_ORIGINS` does not list your dev origin | set `ALLOWED_ORIGINS=http://localhost:3000` in `Backend/.env.local`, restart backend |
| Logged out on every refresh | origin mismatch (`localhost` vs `127.0.0.1`) splits the cookie jar | use one origin consistently |
| 401 immediately after login | backend clock skew or `JWT_SECRET_KEY` changed between requests | restart backend, log in again |
| `/admin/mobile/*` pages show 503 | Mobile backend `MOBILE_ADMIN_JWT_SECRET` unset | see `DEPLOYMENT_PRODUCTION.md` §15 |
| `/admin/mobile/*` 404 after refresh in production | Firebase SPA rewrite missing | confirm the `rewrites` block in `firebase.json` deployed |
| Blocked request in devtools console, "violates CSP" | new API origin not in `connect-src` | add it to the CSP header in `firebase.json` and redeploy |
| `npm ci` fails on integrity | Node version mismatch | use Node 18 or 20 LTS |
| Blank page in production, no errors | built without `.env.production` | rebuild and re-verify §5 |

---

## 8. Conventions

- `process.env` is read **only** in `src/config/env.js`. Everywhere else imports `API_BASE`,
  `AUTH_API_BASE`, `MOBILE_ADMIN_API_BASE` from there.
- Role names are strings that must match `Backend/auth/constants/roles.py` and
  `auth_enabler.roles.name` exactly. Change one, change all three.
- New protected page → add the route in `src/App.js` wrapped in `<ProtectedRoute allowedRoles={…}>`,
  and confirm the backend enforces the same permission. A UI gate alone is not authorization.
- Mobile Admin pages call the Mobile backend through `services/mobileAdminApi.js` only — this
  frontend never touches the Mobile database.
- Never put a secret in a `REACT_APP_*` variable.
