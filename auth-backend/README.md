# Sentio Auth API

PostgreSQL + Flask JWT authentication (replaces AWS Cognito).

## Setup

1. Create a PostgreSQL database and set `DATABASE_URL` in `.env` (see `.env.example`).
2. Apply schema and migrations:

```bash
psql $DATABASE_URL -f db/schema.sql
psql $DATABASE_URL -f db/migrate_signup_flow.sql
psql $DATABASE_URL -f db/seed.sql
# Optional: granular RBAC permissions
python db/upgrade_rbac.py
```

3. Install and run:

```bash
pip install -r requirements.txt
python app.py
```

Default: `http://localhost:5000`

## Signup flow

1. `POST /api/auth/signup` — public; creates `pending` user (no password).
2. Admin opens Frontend `/admin`, assigns one of: Behaviour Analyst, Principal, Counsellor, Teacher.
3. `POST /api/admin/users/:id/approve` — activates user, emails temporary password.
4. User signs in at `/` and is routed to their role dashboard.

## Default admin (from seed)

- Email: `admin@sentiomind.com`
- Password: `admin123` (change after first login)

Configure SMTP in `.env` so approval emails are sent. Without SMTP, credentials are logged to the server console.
