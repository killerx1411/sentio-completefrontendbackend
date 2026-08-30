-- Password reset tokens (hashed) and request rate limiting
CREATE TABLE IF NOT EXISTS auth_enabler.password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_enabler.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_password_reset_token_hash
    ON auth_enabler.password_reset_tokens (token_hash);

CREATE INDEX IF NOT EXISTS idx_password_reset_user_id
    ON auth_enabler.password_reset_tokens (user_id);

CREATE TABLE IF NOT EXISTS auth_enabler.password_reset_requests (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    requested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_password_reset_requests_email_at
    ON auth_enabler.password_reset_requests (email, requested_at);
