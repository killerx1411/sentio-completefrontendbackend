import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { getPrimaryRole, isSuperAdminUser } from "../utils/roleRoutes";
import icon from "../assets/icon.png";
import "./admin.css";

const NAV = [
  { to: "/admin", end: true, label: "Dashboard" },
  { to: "/admin/pending", label: "Pending signups" },
  { to: "/admin/users", label: "User management" },
  { to: "/admin/audit-logs", label: "Audit logs" },
];

export default function AdminLayout() {
  const { user, logout } = useSession();
  const navigate = useNavigate();
  const role = getPrimaryRole(user);
  const isSuper = isSuperAdminUser(user);

  async function handleLogout() {
    await logout();
    navigate("/", { replace: true });
  }

  return (
    <div className="admin-root">
      <aside className="admin-sidebar">
        <img src={icon} alt="Sentio Mind" style={{ width: 150, height: 50, objectFit: "contain", borderRadius: 10 }} />
        <h2>Admin</h2>
        <nav className="admin-nav">
          {NAV.filter((item) => (item.to === "/admin/pending" ? isSuper : true)).map(
            ({ to, end, label }) => (
            <NavLink key={to} to={to} end={end}>
              {label}
            </NavLink>
            )
          )}
        </nav>
        <div style={{ marginTop: "auto", fontSize: "0.85rem" }}>
          <div style={{ fontWeight: 600, color: "#0f4c5c" }}>{user?.full_name}</div>
          <div style={{ color: "#2ec4b6", fontSize: "0.75rem", fontWeight: 700 }}>{role}</div>
          <div style={{ color: "#64748b", marginBottom: "0.75rem" }}>{user?.email}</div>
          <button type="button" className="admin-btn" onClick={handleLogout} style={{ width: "100%" }}>
            Log out
          </button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
