export const ROLE_DASHBOARD_PATH = {
  "Behaviour Analyst": "/BehaviourAnalyst",
  Principal: "/PrincipleDashboard",
  Counsellor: "/SchoolCounsellorDashboard",
  Teacher: "/TeacherDashboard",
  // Canonical backend role names
  "Behaviour Scientist": "/BehaviourAnalyst",
  Psychologist: "/SchoolCounsellorDashboard",
  "Class Teacher": "/TeacherDashboard",
  "Super Admin": "/admin",
  "Secondary Admin": "/admin",
  "Normal Admin": "/admin",
};

export const STAKEHOLDER_ROLES = [
  "Behaviour Analyst",
  "Principal",
  "Counsellor",
  "Teacher",
  // Canonical backend role names
  "Behaviour Scientist",
  "Psychologist",
  "Class Teacher",
];

export function getPrimaryRole(user) {
  if (!user?.roles?.length) return null;
  return user.roles[0].name;
}

export function getDashboardPathForUser(user) {
  const role = getPrimaryRole(user);
  return ROLE_DASHBOARD_PATH[role] || "/";
}

export function isAdminUser(user) {
  const role = getPrimaryRole(user);
  return role === "Super Admin" || role === "Secondary Admin" || role === "Normal Admin";
}

export function isSuperAdminUser(user) {
  return user?.roles?.some((r) => r.name === "Super Admin") ?? false;
}
