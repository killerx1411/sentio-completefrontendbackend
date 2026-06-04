-- =========================================================================
-- Phase 1.5: Seed Data for Auth Enabler Service
-- Run this script after schema.sql to populate the database with initial
-- roles, permissions, and an admin user.
-- =========================================================================

-- 1. Seed Roles (standardized to match constants/roles.py)
INSERT INTO auth_enabler.roles (name, description) VALUES
('Super Admin', 'Full control. Only approval authority.'),
('Secondary Admin', 'Operational management. No approvals.'),
('Normal Admin', 'Read-only/support monitoring.'),
('Principal', 'School principal with read-only access.'),
('Psychologist', 'School psychologist with read-only access.'),
('Class Teacher', 'Classroom teacher with student management access.'),
('Behaviour Scientist', 'Analytical role.')
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;

-- 2. Seed Permissions (standardized to match constants/roles.py)
INSERT INTO auth_enabler.permissions (name, module, action, description) VALUES
('users.read', 'Users', 'READ', 'View list of users and detail profiles'),
('users.write', 'Users', 'CREATE', 'Create and edit user profiles'),
('users.delete', 'Users', 'DELETE', 'Permanently delete user profiles'),
('users.approve', 'Users', 'APPROVE', 'Approve or reject pending user registrations'),
('roles.assign', 'Roles', 'ASSIGN', 'Assign roles to user profiles'),
('permissions.manage', 'Permissions', 'ALL', 'Manage permissions and RBAC policies'),
('reports.read', 'Reports', 'READ', 'View platform reports and analytics'),
('reports.write', 'Reports', 'WRITE', 'Create and edit reports and analytics exports'),
('observations.write', 'Observations', 'WRITE', 'Write student observations'),
('audit.read', 'Audit Logs', 'READ', 'View platform compliance and security logs')
ON CONFLICT (name) DO UPDATE SET
  module = EXCLUDED.module,
  action = EXCLUDED.action,
  description = EXCLUDED.description;

-- 3. Map Permissions to Roles (mirror constants/roles.py)
-- Super Admin: everything
INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_enabler.roles r
JOIN auth_enabler.permissions p ON p.name IN (
  'users.read', 'users.write', 'users.delete', 'users.approve',
  'roles.assign', 'permissions.manage', 'reports.read', 'reports.write', 'observations.write', 'audit.read'
)
WHERE r.name = 'Super Admin'
ON CONFLICT DO NOTHING;

-- Secondary Admin: operational management, no approvals
INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_enabler.roles r
JOIN auth_enabler.permissions p ON p.name IN ('users.read', 'users.write', 'reports.read')
WHERE r.name = 'Secondary Admin'
ON CONFLICT DO NOTHING;

-- Normal Admin: read-only/support monitoring
INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_enabler.roles r
JOIN auth_enabler.permissions p ON p.name IN ('users.read', 'reports.read')
WHERE r.name = 'Normal Admin'
ON CONFLICT DO NOTHING;

-- Behaviour Scientist
INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_enabler.roles r
JOIN auth_enabler.permissions p ON p.name IN ('reports.read')
WHERE r.name = 'Behaviour Scientist'
ON CONFLICT DO NOTHING;

-- Principal, Psychologist: reports.read
INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_enabler.roles r
JOIN auth_enabler.permissions p ON p.name IN ('reports.read')
WHERE r.name IN ('Principal', 'Psychologist')
ON CONFLICT DO NOTHING;

-- Class Teacher: reports.read + observations.write
INSERT INTO auth_enabler.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_enabler.roles r
JOIN auth_enabler.permissions p ON p.name IN ('reports.read', 'observations.write')
WHERE r.name = 'Class Teacher'
ON CONFLICT DO NOTHING;

-- 4. Create Default Admin Users
-- Note: The password_hash below is a placeholder valid bcrypt string for "admin123".
-- If this hash fails during login, use the POST /api/auth/register endpoint to create a new user.
-- Passwords:
-- - superadmin@sentiomind.com / SuperAdmin@123
-- - normaladmin@sentiomind.com / NormalAdmin@123
-- - secondaryadmin@sentiomind.com / SecondaryAdmin@123
INSERT INTO auth_enabler.users (full_name, email, password_hash, status, registration_status, is_first_login)
VALUES(
    'System Administrator', 
    'admin@sentiomind.com', 
    '$2b$12$SBgQvcwDpt3rrSFdAs1LLe6t3PMPS6yH4TMpC5MDPYB9qZOtmOHUC', 
    'active',
    'APPROVED',
    FALSE
),
    (
        'Super Administrator',
        'superadmin@sentiomind.com',
        '$2b$12$/mD8Y/QyVMidlERkp5rICudeogAdL5ad6wFipR5qGxQ0LHsdavRwy',
        'active',
        'APPROVED',
        FALSE
    ),
    (
        'Secondary Administrator',
        'secondaryadmin@sentiomind.com',
        '$2b$12$XFSHC0YCzyYYwUCoSFRk1u0nvbz.abREECwmZSNWB6IAOI3E7szTa',
        'active',
        'APPROVED',
        FALSE
    ),
    (
        'Normal Administrator',
        'normaladmin@sentiomind.com',
        '$2b$12$8kUhqu42JkgsiLoEmPYN7OGS4gKWlziZ0n3xrJwd45M0S0DNqXxFi',
        'active',
        'APPROVED',
        FALSE
    )
ON CONFLICT (email) DO NOTHING;

-- 5. Assign Admin Roles
INSERT INTO auth_enabler.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM auth_enabler.users u, auth_enabler.roles r
WHERE u.email = 'admin@sentiomind.com' AND r.name = 'Secondary Admin'
ON CONFLICT DO NOTHING;

INSERT INTO auth_enabler.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM auth_enabler.users u, auth_enabler.roles r
WHERE u.email = 'superadmin@sentiomind.com' AND r.name = 'Super Admin'
ON CONFLICT DO NOTHING;

INSERT INTO auth_enabler.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM auth_enabler.users u, auth_enabler.roles r
WHERE u.email = 'secondaryadmin@sentiomind.com' AND r.name = 'Secondary Admin'
ON CONFLICT DO NOTHING;

INSERT INTO auth_enabler.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM auth_enabler.users u, auth_enabler.roles r
WHERE u.email = 'normaladmin@sentiomind.com' AND r.name = 'Normal Admin'
ON CONFLICT DO NOTHING;
