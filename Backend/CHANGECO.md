# CHANGECO — DevOps change order

Scope: what DevOps must change, and nothing else. The application code change is
already merged; everything below it is configuration.

---

## 1. What changed in the code

- `auth/db_connection.py` — psycopg2 pool bounds are no longer hardcoded at
  `minconn=2, maxconn=10`. They now read `SENTIO_DB_POOL_MIN` and
  `SENTIO_DB_POOL_MAX`.
- Defaults are unchanged (`2` / `10`). **A deployment that sets neither variable
  behaves exactly as before.** No action required on existing environments.
- Bad values (non-integer, or `< 1`) log a warning and fall back to the default.
  An inverted pair (`MIN > MAX`) is clamped to `MAX`, also with a warning.
- Documented in `README.md` (env var table), `.env.example` and
  `.env.production.example`.

---

## 2. Why it matters — the connection arithmetic

- `gunicorn_config.py` sets `preload_app = False`. Every gunicorn **worker
  process** builds its own pool. Pool size is per worker, not per container.
- Connections held by one Cloud Run instance = `GUNICORN_WORKERS × SENTIO_DB_POOL_MAX`.
- A revision rollout runs the old and new revisions concurrently, so the total
  **briefly doubles**.
- Cloud SQL sets `max_connections` from instance memory, and ~3 are reserved for
  the superuser and the Cloud SQL agent:

  | Tier | RAM | `max_connections` | Usable |
  |---|---|---|---|
  | `db-f1-micro` | 0.6 GB | ~25 | ~22 |
  | `db-g1-small` | 1.7 GB | ~50 | ~47 |
  | `db-custom-2-7680` | 7.5 GB | ~400 | ~397 |

- Exceeding it surfaces as `FATAL: sorry, too many clients already` — a failed
  login, not a graceful slowdown.

**Rule to apply:**

```
GUNICORN_WORKERS × SENTIO_DB_POOL_MAX × MAX_INSTANCES × 2  <  usable max_connections
                                                        ^ rollout overlap
```

---

## 3. Settings to apply, by environment

### 3.1 Existing production (`db-custom-2-7680`, `b2bapi.sentiomind.in`)

- **No change required.** Do not set the new variables; the defaults are what
  the service already runs.
- Optional safety margin: at `4 workers × 10 conns × 10 instances × 2` a fully
  scaled-out rollout would want 800 connections against ~397 usable. If
  `--max-instances=10` is real, set `SENTIO_DB_POOL_MAX=8` and cap
  `--max-instances=5`, or raise the tier.

### 3.2 New small / pilot deployment (`db-f1-micro`, admin users only)

Add to the env file:

- `SENTIO_DB_POOL_MIN=1`
- `SENTIO_DB_POOL_MAX=4`
- `GUNICORN_WORKERS=2`
- `GUNICORN_THREADS=4`

And on the Cloud Run service:

- `--max-instances=1`

Worst case: `2 × 4 × 1 × 2 = 16` connections against ~22 usable. Fits.

---

## 4. Cloud SQL — creating the small instance

```bash
gcloud sql instances create sentio-b2b-pg \
  --database-version=POSTGRES_16 \
  --region="$REGION" \
  --edition=ENTERPRISE \
  --tier=db-f1-micro \
  --availability-type=ZONAL \
  --storage-size=10GB --storage-auto-increase \
  --ssl-mode=ENCRYPTED_ONLY \
  --backup-start-time=18:30

gcloud sql databases create sentio_b2b --instance=sentio-b2b-pg
gcloud sql users create sentio_app --instance=sentio-b2b-pg --prompt-for-password
```

- `--edition=ENTERPRISE` is **mandatory**. Shared-core tiers do not exist on
  Enterprise Plus, which is the default on new instances — omit the flag and
  creation fails.
- `--availability-type=ZONAL` — `db-f1-micro` cannot do REGIONAL HA.
- `--ssl-mode=ENCRYPTED_ONLY` replaces the deprecated `--require-ssl`. It is
  required because `auth/config.py` rejects any `SENTIO_DB_SSLMODE` outside
  `require` / `verify-ca` / `verify-full` in production.
- `db-f1-micro` carries **no Cloud SQL SLA**, no HA and no read replica.
  Acceptable for admin-only pilot traffic; not for customer load.

---

## 5. Cloud Run deployment

```bash
gcloud run deploy b2b-auth \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --service-account="$RUN_SA" \
  --port=8080 \
  --cpu=1 --memory=512Mi \
  --min-instances=0 --max-instances=1 \
  --concurrency=80 --timeout=120s \
  --add-cloudsql-instances="${PROJECT_ID}:${REGION}:sentio-b2b-pg" \
  --env-vars-file=env.yaml \
  --set-secrets="JWT_SECRET_KEY=b2b-jwt-secret-key:latest,MFA_ENCRYPTION_KEY=b2b-mfa-encryption-key:latest,SENTIO_DB_URL=b2b-db-url:latest,RATELIMIT_STORAGE_URI=b2b-ratelimit-uri:latest,SMTP_PASSWORD=b2b-smtp-password:latest"
```

- **Do not set `PORT`.** Cloud Run injects `8080`; `gunicorn_config.py` binds
  `0.0.0.0:$PORT`. Overriding it breaks the startup probe.
- **Use `--env-vars-file`, not `--set-env-vars`.** `ALLOWED_ORIGINS` and
  `AUTH_AUTHORITY_APPLICATIONS` are comma-separated values, and `--set-env-vars`
  treats a comma as a variable separator. If the flag must be inline, use the
  alternate-delimiter form: `--set-env-vars="^##^A=1##B=2"`.
- `--add-cloudsql-instances` gives a Unix socket at
  `/cloudsql/PROJECT:REGION:INSTANCE`. No VPC connector, no public IP, no
  authorized-networks rule. `SENTIO_DB_URL` then takes the form:

  ```
  postgresql://sentio_app:PASSWORD@/sentio_b2b?host=/cloudsql/PROJECT:REGION:INSTANCE
  ```

  libpq ignores `sslmode` on a Unix socket, so `SENTIO_DB_SSLMODE=require`
  satisfies the config check without breaking the connection.
- `--min-instances=0` saves roughly $13/mo. Cost: a 3-5 s cold start on the
  first login after idle, because the app validates config, pings Redis and
  opens the DB pool at import time. Use `--min-instances=1` if that is not
  acceptable.

---

## 6. `env.yaml`

```yaml
FLASK_ENV: "production"
FRONTEND_URL: "https://product.sentiomind.in"
ALLOWED_ORIGINS: "https://product.sentiomind.in"
SERVICE_APPLICATIONS: "sentio-b2b"
SENTIO_DB_SSLMODE: "require"
SENTIO_DB_POOL_MIN: "1"
SENTIO_DB_POOL_MAX: "4"
GUNICORN_WORKERS: "2"
GUNICORN_THREADS: "4"
TRUSTED_PROXY_COUNT: "1"
PREFERRED_URL_SCHEME: "https"
STRICT_PASSWORD_BREACH_CHECK: "true"
ENABLE_OPEN_REGISTRATION: "false"
SMTP_HOST: "smtp.example.com"
SMTP_PORT: "587"
SMTP_USER: "no-reply@sentiomind.in"
SMTP_FROM: "no-reply@sentiomind.in"
```

- **Leave `AUTH_AUTHORITY_APPLICATIONS` unset.** It defaults to every registered
  application. This service is the single auth authority and must be able to
  mint and introspect `sentio-mobile` tokens for the Mobile Admin pages, while
  `SERVICE_APPLICATIONS=sentio-b2b` keeps its own business routes B2B-only.
  Setting the authority dial to `sentio-b2b` would make the service reject the
  Mobile tokens it had just issued.

---

## 7. Secrets

Create five. **`REDIS_URL` is no longer one of them.**

| Secret | Contents |
|---|---|
| `b2b-jwt-secret-key` | ≥ 32 chars. Shared with the Mobile backend — rotating it requires updating both services together. |
| `b2b-mfa-encryption-key` | 64-char hex |
| `b2b-db-url` | the Unix-socket DSN from §5 |
| `b2b-ratelimit-uri` | `rediss://default:TOKEN@HOST:6379` |
| `b2b-smtp-password` | app password for `no-reply@sentiomind.in` |

- **Remove `REDIS_URL` from `--set-secrets` and delete the `b2b-redis-url`
  secret.** Nothing in the application reads it. It was built for CSRF storage;
  CSRF is now a stateless HMAC (`auth/middleware/csrf.py`) and the helper that
  consumed it has no remaining callers.
- Grant the runtime service account `roles/secretmanager.secretAccessor` on each
  secret, and `roles/cloudsql.client` on the project.

---

## 8. Redis

- Only `RATELIMIT_STORAGE_URI` is used. It **must** be `redis://` or `rediss://`
  and must not point at localhost — the app refuses to start otherwise, and
  refuses to start if the endpoint does not answer `PING`.
- **Use the Upstash free tier.** Public TLS endpoint, no Serverless VPC
  connector, $0. Rate-limit traffic for an admin-only console is a handful of
  commands per login.
- Do not provision Memorystore for this deployment: ~$35/mo plus a VPC connector
  that bills ~$10-25/mo even while idle.
- Do not "fix" a Redis outage by switching to `memory://`. Counters would be
  per-worker and per-instance, silently multiplying every configured limit
  (login `10/minute`, MFA verify `5/minute`, password reset `5/minute;10/hour`)
  by workers × instances.

---

## 9. Post-deploy verification

```bash
SERVICE_URL=$(gcloud run services describe b2b-auth --region="$REGION" --format='value(status.url)')

curl -fsS "$SERVICE_URL/health"
curl -fsS "$SERVICE_URL/health/ready"
```

- `/health` must return `{"status":"healthy",...}`. It deliberately does **not**
  touch Postgres or Redis, so never wire a dependency check to it — a Redis blip
  would otherwise make Cloud Run tear down every healthy instance.
- `/health/ready` must return
  `{"status":"ready","checks":{"database":"ok","rate_limit_store":"ok"}}`.
  A `503` with `"unavailable"` names the broken dependency. Use this one for
  uptime checks, never for the container probe.
- Confirm the pool setting took effect — at idle the connection count should sit
  near `GUNICORN_WORKERS × SENTIO_DB_POOL_MIN`. Cloud SQL console →
  Monitoring → "PostgreSQL connections".

---

## 10. What to watch after go-live

- **`FATAL: sorry, too many clients already`** in Cloud Run logs → the §2
  arithmetic is violated. Lower `SENTIO_DB_POOL_MAX` or `--max-instances` first;
  raising the Cloud SQL `max_connections` flag on a 0.6 GB instance risks OOM.
- **`Slow query (N.NNs): ...`** warnings → logged above 5 s by
  `auth/db_connection.py`. Usually audit-table growth. Note `statement_timeout`
  is 30 s, so a slow report **errors out** rather than merely crawling.
- **`RuntimeError: Redis unavailable for rate limiting`** at startup → the
  rate-limit endpoint is unreachable from Cloud Run. Check the URI and the
  Upstash database status. A failed revision receives no traffic; the previous
  revision keeps serving.
- **`RuntimeError: RATELIMIT_STORAGE_URI must be ...`** → the secret resolved
  empty or to `memory://`.
- **Upgrade trigger:** sustained CPU on the shared-core tier, or connection
  pressure `SENTIO_DB_POOL_MAX` can no longer absorb. Path is `db-f1-micro` →
  `db-g1-small` → `db-custom-2-7680` with `--availability-type=REGIONAL` and
  `--min-instances=1`. A tier change is an in-place restart, not a migration.
