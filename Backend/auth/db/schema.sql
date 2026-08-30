-- Auth Enabler Service Schema Definition
-- PostgreSQL standard syntax (Compatible with version 12+)

CREATE SCHEMA IF NOT EXISTS auth_enabler;

-- 1. users
CREATE TABLE IF NOT EXISTS auth_enabler.users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    phone VARCHAR(20),
    department VARCHAR(100),
    employee_id VARCHAR(50),
    organization VARCHAR(255),
    signup_message TEXT,
    requested_role VARCHAR(100),
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    registration_status VARCHAR(50) DEFAULT 'PENDING',
    is_first_login BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    profile_image TEXT,
    created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for users.email since auth systems query this frequently
CREATE INDEX idx_users_email ON auth_enabler.users (email);
CREATE INDEX idx_users_created_by ON auth_enabler.users (created_by);
CREATE INDEX idx_users_updated_by ON auth_enabler.users (updated_by);

-- 2. roles
CREATE TABLE IF NOT EXISTS auth_enabler.roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_roles_created_by ON auth_enabler.roles (created_by);
CREATE INDEX idx_roles_updated_by ON auth_enabler.roles (updated_by);

-- 3. permissions
CREATE TABLE IF NOT EXISTS auth_enabler.permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    module VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_permissions_created_by ON auth_enabler.permissions (created_by);
CREATE INDEX idx_permissions_updated_by ON auth_enabler.permissions (updated_by);

-- 4. role_permissions
CREATE TABLE IF NOT EXISTS auth_enabler.role_permissions (
    role_id INTEGER REFERENCES auth_enabler.roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES auth_enabler.permissions(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

-- Indexes for role_permissions (often queried during authorization)
CREATE INDEX idx_role_permissions_role_id ON auth_enabler.role_permissions (role_id);
CREATE INDEX idx_role_permissions_permission_id ON auth_enabler.role_permissions (permission_id);
CREATE INDEX idx_role_permissions_created_by ON auth_enabler.role_permissions (created_by);
CREATE INDEX idx_role_permissions_updated_by ON auth_enabler.role_permissions (updated_by);

-- 5. user_roles
CREATE TABLE IF NOT EXISTS auth_enabler.user_roles (
    user_id INTEGER REFERENCES auth_enabler.users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES auth_enabler.roles(id) ON DELETE CASCADE,
    created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Index for user_roles (role_id lookup)
CREATE INDEX idx_user_roles_role_id ON auth_enabler.user_roles (role_id);
CREATE INDEX idx_user_roles_user_id ON auth_enabler.user_roles (user_id);
CREATE INDEX idx_user_roles_created_by ON auth_enabler.user_roles (created_by);
CREATE INDEX idx_user_roles_updated_by ON auth_enabler.user_roles (updated_by);

-- 6. user_sessions
CREATE TABLE IF NOT EXISTS auth_enabler.user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES auth_enabler.users(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL,
    device_info VARCHAR(255),
    ip_address VARCHAR(45),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    -- Consumer application this session was opened for
    -- (auth/constants/applications.py)
    application VARCHAR(64) NOT NULL DEFAULT 'sentio-b2b',
    created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for session lookup
CREATE INDEX idx_user_sessions_refresh_token ON auth_enabler.user_sessions (refresh_token);
CREATE INDEX idx_user_sessions_application ON auth_enabler.user_sessions (application);
CREATE INDEX idx_user_sessions_user_id ON auth_enabler.user_sessions (user_id);
CREATE INDEX idx_user_sessions_created_by ON auth_enabler.user_sessions (created_by);
CREATE INDEX idx_user_sessions_updated_by ON auth_enabler.user_sessions (updated_by);

-- 7. audit_logs
CREATE TABLE IF NOT EXISTS auth_enabler.audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL, -- Keeping log if user is deleted
    action VARCHAR(255) NOT NULL,
    module VARCHAR(100),
    description TEXT,
    ip_address VARCHAR(45),
    created_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for auditing performance
CREATE INDEX idx_audit_logs_user_id ON auth_enabler.audit_logs (user_id);
CREATE INDEX idx_audit_logs_action ON auth_enabler.audit_logs (action);
CREATE INDEX idx_audit_logs_created_by ON auth_enabler.audit_logs (created_by);
CREATE INDEX idx_audit_logs_updated_by ON auth_enabler.audit_logs (updated_by);

-- Function to automatically update the 'updated_at' timestamp
CREATE OR REPLACE FUNCTION auth_enabler.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to execute the function on users table updates
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON auth_enabler.users
FOR EACH ROW
EXECUTE FUNCTION auth_enabler.update_updated_at_column();

-- Trigger for roles table updates
CREATE TRIGGER update_roles_updated_at
BEFORE UPDATE ON auth_enabler.roles
FOR EACH ROW
EXECUTE FUNCTION auth_enabler.update_updated_at_column();

-- Trigger for permissions table updates
CREATE TRIGGER update_permissions_updated_at
BEFORE UPDATE ON auth_enabler.permissions
FOR EACH ROW
EXECUTE FUNCTION auth_enabler.update_updated_at_column();

-- Trigger for role_permissions table updates
CREATE TRIGGER update_role_permissions_updated_at
BEFORE UPDATE ON auth_enabler.role_permissions
FOR EACH ROW
EXECUTE FUNCTION auth_enabler.update_updated_at_column();

-- Trigger for user_roles table updates
CREATE TRIGGER update_user_roles_updated_at
BEFORE UPDATE ON auth_enabler.user_roles
FOR EACH ROW
EXECUTE FUNCTION auth_enabler.update_updated_at_column();

-- Trigger for user_sessions table updates
CREATE TRIGGER update_user_sessions_updated_at
BEFORE UPDATE ON auth_enabler.user_sessions
FOR EACH ROW
EXECUTE FUNCTION auth_enabler.update_updated_at_column();

-- Trigger for audit_logs table updates
CREATE TRIGGER update_audit_logs_updated_at
BEFORE UPDATE ON auth_enabler.audit_logs
FOR EACH ROW
EXECUTE FUNCTION auth_enabler.update_updated_at_column();

