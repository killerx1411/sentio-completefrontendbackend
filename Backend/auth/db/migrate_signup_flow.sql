-- Signup approval workflow: pending users, requested role, session revocation
ALTER TABLE auth_enabler.users
    ADD COLUMN IF NOT EXISTS requested_role VARCHAR(100),
    ADD COLUMN IF NOT EXISTS organization VARCHAR(255),
    ADD COLUMN IF NOT EXISTS signup_message TEXT,
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS approved_by INTEGER REFERENCES auth_enabler.users(id) ON DELETE SET NULL;

ALTER TABLE auth_enabler.user_sessions
    ADD COLUMN IF NOT EXISTS revoked BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_users_status ON auth_enabler.users (status);
CREATE INDEX IF NOT EXISTS idx_users_requested_role ON auth_enabler.users (requested_role);

-- Stakeholder + admin roles for Sentio Mind
INSERT INTO auth_enabler.roles (name, description) VALUES
('Behaviour Analyst', 'Behavioural analytics and supervision dashboard'),
('Principal', 'Institution leadership dashboard'),
('Counsellor', 'Student counselling dashboard'),
('Teacher', 'Classroom and teaching dashboard'),
('Admin', 'Platform administrator — approves signups and manages users')
ON CONFLICT (name) DO NOTHING;
