/** Canonical role names — must match auth_enabler.roles.name and Backend auth/constants/roles.py */

import { APP_B2B, APP_MOBILE } from "./applications";

export const ROLES = {
  SUPER_ADMIN: "Super Admin",
  SECONDARY_ADMIN: "Secondary Admin",
  NORMAL_ADMIN: "Normal Admin",
  PRINCIPAL: "Principal",
  PSYCHOLOGIST: "Psychologist",
  BEHAVIOUR_SCIENTIST: "Behaviour Scientist",
  CLASS_TEACHER: "Class Teacher",
  // Sentio Mobile Admin — first-class roles of the same authority, NOT aliases
  // of the B2B admin tier. Stored lower-case, exactly as ROLE_CONFIG keys them.
  MOBILE_SUPER_ADMIN: "mobile_super_admin",
  MOBILE_SECONDARY_ADMIN: "mobile_secondary_admin",
};

export const ROLE_DASHBOARD_PATH = {
  [ROLES.BEHAVIOUR_SCIENTIST]: "/BehaviourAnalyst",
  [ROLES.PRINCIPAL]: "/PrincipleDashboard",
  [ROLES.PSYCHOLOGIST]: "/SchoolCounsellorDashboard",
  [ROLES.CLASS_TEACHER]: "/TeacherDashboard",
  [ROLES.SUPER_ADMIN]: "/admin",
  [ROLES.SECONDARY_ADMIN]: "/admin",
  [ROLES.NORMAL_ADMIN]: "/admin",
  [ROLES.MOBILE_SUPER_ADMIN]: "/admin/mobile",
  [ROLES.MOBILE_SECONDARY_ADMIN]: "/admin/mobile",
  // Legacy / signup labels still returned on some records
  "Behaviour Analyst": "/BehaviourAnalyst",
  Counsellor: "/SchoolCounsellorDashboard",
  Counselor: "/SchoolCounsellorDashboard",
  Teacher: "/TeacherDashboard",
  Principle: "/PrincipleDashboard",
};

export const STAKEHOLDER_ROLES = [
  ROLES.PRINCIPAL,
  ROLES.PSYCHOLOGIST,
  ROLES.CLASS_TEACHER,
  ROLES.BEHAVIOUR_SCIENTIST,
];

export const ADMIN_ROLES = [
  ROLES.SUPER_ADMIN,
  ROLES.SECONDARY_ADMIN,
  ROLES.NORMAL_ADMIN,
];

/** Sentio Mobile Admin roles. Deliberately NOT part of ADMIN_ROLES: a Mobile
 *  Admin gains the Mobile section only, never B2B privileges. */
export const MOBILE_ADMIN_ROLES = [
  ROLES.MOBILE_SUPER_ADMIN,
  ROLES.MOBILE_SECONDARY_ADMIN,
];

/** Every role that may enter the /admin shell — the union, not a merge of
 *  privileges. What each may do inside is gated per route and per section. */
export const CONSOLE_ROLES = [...ADMIN_ROLES, ...MOBILE_ADMIN_ROLES];

/** Application a role may be issued a token for. Mirrors
 *  ROLE_CONFIG[role]["applications"] in Backend/auth/constants/roles.py; the
 *  auth backend enforces it, this is only used to pick which application the
 *  login form asks for. */
export const ROLE_APPLICATION = {
  [ROLES.MOBILE_SUPER_ADMIN]: APP_MOBILE,
  [ROLES.MOBILE_SECONDARY_ADMIN]: APP_MOBILE,
};

export function applicationForRole(roleName) {
  return ROLE_APPLICATION[roleName] || APP_B2B;
}

export const ROLE_ALIASES = {
  Principle: ROLES.PRINCIPAL,
  Counsellor: ROLES.PSYCHOLOGIST,
  Counselor: ROLES.PSYCHOLOGIST,
  Teacher: ROLES.CLASS_TEACHER,
  "Behaviour Analyst": ROLES.BEHAVIOUR_SCIENTIST,
};

export function normalizeRoleName(roleName) {
  if (!roleName) return roleName;
  const trimmed = roleName.trim();
  return ROLE_ALIASES[trimmed] || trimmed;
}

export function getPrimaryRole(user) {
  if (!user?.roles?.length) return null;
  return user.roles[0].name;
}

export function getDashboardPathForUser(user) {
  const role = getPrimaryRole(user);
  const normalized = normalizeRoleName(role);
  return ROLE_DASHBOARD_PATH[normalized] || ROLE_DASHBOARD_PATH[role] || "/";
}

export function isAdminUser(user) {
  const role = getPrimaryRole(user);
  return ADMIN_ROLES.includes(role);
}

export function isSuperAdminUser(user) {
  return user?.roles?.some((r) => r.name === ROLES.SUPER_ADMIN) ?? false;
}

/** True for a Sentio Mobile Admin. Never true for a B2B admin, and vice versa —
 *  the two role sets are disjoint in the authority. */
export function isMobileAdminUser(user) {
  return user?.roles?.some((r) => MOBILE_ADMIN_ROLES.includes(r.name)) ?? false;
}

export function isMobileSuperAdminUser(user) {
  return user?.roles?.some((r) => r.name === ROLES.MOBILE_SUPER_ADMIN) ?? false;
}

/** Display name for a raw role id (the Mobile ids are snake_case in the DB). */
export const ROLE_LABELS = {
  [ROLES.MOBILE_SUPER_ADMIN]: "Mobile Super Admin",
  [ROLES.MOBILE_SECONDARY_ADMIN]: "Mobile Secondary Admin",
};

export function roleLabel(roleName) {
  return ROLE_LABELS[roleName] || roleName || "";
}
