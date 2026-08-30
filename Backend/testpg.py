"""Manual Postgres connectivity smoke test. Reads credentials from env only —
never hardcode database passwords in source (see SENTIO_DB_URL in .env)."""
import os

import psycopg2

from auth.env_loader import load_env

load_env()

db_url = os.environ.get("SENTIO_DB_URL")
if not db_url:
    raise SystemExit("SENTIO_DB_URL is not set (check .env / .env.local)")

conn = psycopg2.connect(db_url)
print("CONNECTED")
conn.close()