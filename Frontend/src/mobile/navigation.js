/**
 * The Mobile section of the admin sidebar.
 *
 * Each entry declares the `mobile.*` permission its API requires. Navigation is
 * filtered by what `GET /api/admin/me` reported for this operator — so a Mobile
 * Secondary Admin does not see sections it cannot load. The Mobile backend
 * still authorizes every request; this only keeps the sidebar honest.
 */

export const MOBILE_NAV = [
  { to: "/admin/mobile", end: true, label: "Dashboard", permission: "mobile.users.read" },
  { to: "/admin/mobile/experts", label: "Counsellors / Experts", permission: "mobile.users.read" },
  { to: "/admin/mobile/users", label: "Users", permission: "mobile.users.read" },
  { to: "/admin/mobile/risk", label: "Risk & clinical safety", permission: "mobile.reports.read" },
  { to: "/admin/mobile/content", label: "Content & interventions", permission: "mobile.content.read" },
  { to: "/admin/mobile/exercises", label: "Exercises", permission: "mobile.content.read" },
  { to: "/admin/mobile/sessions", label: "Sessions", permission: "mobile.reports.read" },
  { to: "/admin/mobile/payments", label: "Payments", permission: "mobile.reports.read" },
  { to: "/admin/mobile/subscriptions", label: "Plans & subscriptions", permission: "mobile.reports.read" },
  // `/api/admin/admins` and `/api/admin/health` authorize on identity alone.
  { to: "/admin/mobile/admins", label: "Admins", permission: null },
  {
    to: "/admin/mobile/audit",
    label: "Audit & activity",
    // The admin audit log needs mobile.audit.read; app events need
    // mobile.reports.read. The page shows whichever tab the operator can read.
    anyPermission: ["mobile.audit.read", "mobile.reports.read"],
  },
  { to: "/admin/mobile/settings", label: "Settings", permission: "mobile.settings.manage" },
  { to: "/admin/mobile/health", label: "System health", permission: null },
];

export function visibleMobileNav(has) {
  return MOBILE_NAV.filter((item) => {
    if (item.anyPermission) return item.anyPermission.some((p) => has(p));
    return item.permission === null || has(item.permission);
  });
}
