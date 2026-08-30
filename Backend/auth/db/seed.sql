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
('Behaviour Scientist', 'Analytical role.'),
-- Sentio Mobile Admin roles. First-class roles of this one authority — NOT
-- aliases of the B2B admin tier.
('mobile_super_admin', 'Sentio Mobile Admin — full control of the Mobile application.'),
('mobile_secondary_admin', 'Sentio Mobile Admin — operational management, no admin management.')
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
('audit.read', 'Audit Logs', 'READ', 'View platform compliance and security logs'),
-- Sentio Mobile permission namespace (mobile.*), deliberately disjoint from the
-- B2B names so a Mobile role can never satisfy a B2B permission check.
('mobile.users.read', 'Mobile Users', 'READ', 'View Sentio Mobile end users'),
('mobile.users.write', 'Mobile Users', 'WRITE', 'Create and edit Sentio Mobile end users'),
('mobile.users.delete', 'Mobile Users', 'DELETE', 'Delete Sentio Mobile end users'),
('mobile.users.approve', 'Mobile Users', 'APPROVE', 'Approve Sentio Mobile end user registrations'),
('mobile.admins.manage', 'Mobile Admins', 'MANAGE', 'Manage Sentio Mobile administrators'),
('mobile.content.read', 'Mobile Content', 'READ', 'View Sentio Mobile content'),
('mobile.content.write', 'Mobile Content', 'WRITE', 'Create and edit Sentio Mobile content'),
('mobile.reports.read', 'Mobile Reports', 'READ', 'View Sentio Mobile reports and analytics'),
('mobile.settings.manage', 'Mobile Settings', 'MANAGE', 'Manage Sentio Mobile application settings'),
('mobile.audit.read', 'Mobile Audit', 'READ', 'View Sentio Mobile audit and security logs')
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

-- mobile_super_admin: full Mobile Admin control
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

-- mobile_secondary_admin: operations only, cannot manage admins or settings
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

-- 4. Admin users — NOT seeded with default passwords (SEC-003).
-- Create the first Super Admin through a secure channel after deployment:
--   • POST /api/auth/register (when ENABLE_OPEN_REGISTRATION=true), or
--   • python -m auth.db.upgrade_rbac (assigns roles to existing users), or
--   • your organization's secure admin bootstrap procedure.
-- Never commit known password hashes or credentials to version control.
