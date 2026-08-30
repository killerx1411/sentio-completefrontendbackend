-- Sentio Mind Auth Security Migrations
-- Safe to run on a live database (IF NOT EXISTS throughout)

-- 1. Login brute-force tracking
CREATE TABLE IF NOT EXISTS auth_enabler.login_attempts (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    ip_address TEXT,
    attempted_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_email_at
    ON auth_enabler.login_attempts (email, attempted_at);

-- 2. Revoked JWT access tokens (jti blocklist)
CREATE TABLE IF NOT EXISTS auth_enabler.revoked_tokens (
    jti TEXT PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires
    ON auth_enabler.revoked_tokens (expires_at);

-- 3. Session device fingerprint
ALTER TABLE auth_enabler.user_sessions
    ADD COLUMN IF NOT EXISTS device_fingerprint VARCHAR(64);

-- 4. Audit log severity + append-only enforcement
ALTER TABLE auth_enabler.audit_logs
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'INFO';

CREATE OR REPLACE FUNCTION auth_enabler.prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'audit_logs rows are append-only and cannot be deleted';
    END IF;

    -- Deleting a user fires the FK "ON DELETE SET NULL" on user_id /
    -- created_by / updated_by, which is an UPDATE on audit_logs. Allow that
    -- one shape of write (actor columns nulled, nothing else touched) so the
    -- log row outlives the actor; every other UPDATE stays blocked.
    IF (to_jsonb(NEW) - 'user_id' - 'created_by' - 'updated_by' - 'updated_at')
       = (to_jsonb(OLD) - 'user_id' - 'created_by' - 'updated_by' - 'updated_at')
       AND (NEW.user_id    IS NULL OR NEW.user_id    = OLD.user_id)
       AND (NEW.created_by IS NULL OR NEW.created_by = OLD.created_by)
       AND (NEW.updated_by IS NULL OR NEW.updated_by = OLD.updated_by)
    THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'audit_logs rows are append-only and cannot be modified';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_logs_append_only ON auth_enabler.audit_logs;
CREATE TRIGGER audit_logs_append_only
BEFORE UPDATE OR DELETE ON auth_enabler.audit_logs
FOR EACH ROW EXECUTE FUNCTION auth_enabler.prevent_audit_log_modification();

-- 5. Refresh token rotation families
CREATE TABLE IF NOT EXISTS auth_enabler.refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES auth_enabler.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    device_hash VARCHAR(64),
    family_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    replaced_by UUID REFERENCES auth_enabler.refresh_tokens(id)
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user
    ON auth_enabler.refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family
    ON auth_enabler.refresh_tokens (family_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash
    ON auth_enabler.refresh_tokens (token_hash);

ALTER TABLE auth_enabler.refresh_tokens
    ADD COLUMN IF NOT EXISTS remember BOOLEAN DEFAULT FALSE;

ALTER TABLE auth_enabler.users
    ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP NULL DEFAULT NULL;

ALTER TABLE auth_enabler.audit_logs
    ADD COLUMN IF NOT EXISTS details JSONB;
ALTER TABLE auth_enabler.audit_logs
    ADD COLUMN IF NOT EXISTS user_agent TEXT;

-- 6. MFA fields
ALTER TABLE auth_enabler.users
    ADD COLUMN IF NOT EXISTS mfa_secret TEXT;
ALTER TABLE auth_enabler.users
    ADD COLUMN IF NOT EXISTS mfa_recovery_codes TEXT[];
ALTER TABLE auth_enabler.users
    ADD COLUMN IF NOT EXISTS school_id INTEGER;
ALTER TABLE auth_enabler.users
    ADD COLUMN IF NOT EXISTS class_id INTEGER;

-- =========================================================================
-- 7. Multi-application support (Sentio Mobile Admin)
-- One authentication authority, many consumer applications. Tokens and
-- sessions are bound to the application they were issued for.
-- See auth/constants/applications.py and auth/constants/roles.py.
-- =========================================================================

ALTER TABLE auth_enabler.user_sessions
    ADD COLUMN IF NOT EXISTS application VARCHAR(64) NOT NULL DEFAULT 'sentio-b2b';
ALTER TABLE auth_enabler.refresh_tokens
    ADD COLUMN IF NOT EXISTS application VARCHAR(64) NOT NULL DEFAULT 'sentio-b2b';

CREATE INDEX IF NOT EXISTS idx_user_sessions_application
    ON auth_enabler.user_sessions (application);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_application
    ON auth_enabler.refresh_tokens (application);

-- Sentio Mobile Admin roles. These are FIRST-CLASS roles of this authority,
-- not aliases of 'Super Admin' / 'Secondary Admin' / 'Normal Admin'.
INSERT INTO auth_enabler.roles (name, description) VALUES
('mobile_super_admin', 'Sentio Mobile Admin — full control of the Mobile application.'),
('mobile_secondary_admin', 'Sentio Mobile Admin — operational management, no admin management.')
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;

-- Mobile permission namespace (mobile.*). Deliberately disjoint from the B2B
-- permission names so a Mobile role can never satisfy a B2B permission check.
INSERT INTO auth_enabler.permissions (name, module, action, description) VALUES
('mobile.users.read',      'Mobile Users',    'READ',    'View Sentio Mobile end users'),
('mobile.users.write',     'Mobile Users',    'WRITE',   'Create and edit Sentio Mobile end users'),
('mobile.users.delete',    'Mobile Users',    'DELETE',  'Delete Sentio Mobile end users'),
('mobile.users.approve',   'Mobile Users',    'APPROVE', 'Approve Sentio Mobile end user registrations'),
('mobile.admins.manage',   'Mobile Admins',   'MANAGE',  'Manage Sentio Mobile administrators'),
('mobile.content.read',    'Mobile Content',  'READ',    'View Sentio Mobile content'),
('mobile.content.write',   'Mobile Content',  'WRITE',   'Create and edit Sentio Mobile content'),
('mobile.reports.read',    'Mobile Reports',  'READ',    'View Sentio Mobile reports and analytics'),
('mobile.settings.manage', 'Mobile Settings', 'MANAGE',  'Manage Sentio Mobile application settings'),
('mobile.audit.read',      'Mobile Audit',    'READ',    'View Sentio Mobile audit and security logs')
ON CONFLICT (name) DO UPDATE SET
  module = EXCLUDED.module,
  action = EXCLUDED.action,
  description = EXCLUDED.description;

INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_enabler.roles r
JOIN auth_enabler.permissions p ON p.name IN (
  'mobile.users.read', 'mobile.users.write', 'mobile.users.delete', 'mobile.users.approve',
  'mobile.admins.manage', 'mobile.content.read', 'mobile.content.write',
  'mobile.reports.read', 'mobile.settings.manage', 'mobile.audit.read'
)
WHERE r.name = 'mobile_super_admin'
ON CONFLICT DO NOTHING;

INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_enabler.roles r
JOIN auth_enabler.permissions p ON p.name IN (
  'mobile.users.read', 'mobile.users.write',
  'mobile.content.read', 'mobile.content.write',
  'mobile.reports.read'
)
WHERE r.name = 'mobile_secondary_admin'
ON CONFLICT DO NOTHING;
