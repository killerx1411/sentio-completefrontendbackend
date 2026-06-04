import { useEffect, useState } from "react";
import { Activity, Lock, Shield, Users } from "lucide-react";
import { useSession } from "../context/SessionContext";
import { fetchDashboardStats } from "../services/adminApi";
import "./admin.css";

const STAT_CARDS = [
  { key: "total_users", label: "Total Users", icon: Users, color: "#0f4c5c" },
  { key: "active_roles", label: "Active Roles", icon: Shield, color: "#2ec4b6" },
  { key: "total_permissions", label: "Permissions", icon: Lock, color: "#64748b" },
  { key: "recent_logins", label: "Recent Logins", icon: Activity, color: "#475569" },
];

export default function AdminHome() {
  const { user } = useSession();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboardStats()
      .then(setStats)
      .catch((err) => setError(err.message || "Failed to load stats"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="admin-page-title">Dashboard</h1>
      <p className="admin-page-sub">
        Welcome back, {user?.full_name}. Platform overview.
      </p>

      {error && <div className="admin-banner error">{error}</div>}

      <div className="admin-stats-grid">
        {STAT_CARDS.map(({ key, label, icon: Icon, color }) => (
          <div key={key} className="admin-card admin-stat-card">
            <div className="admin-stat-icon" style={{ backgroundColor: `${color}15`, color }}>
              <Icon size={22} />
            </div>
            <div>
              <p className="admin-stat-label">{label}</p>
              <p className="admin-stat-value">
                {loading ? "…" : stats?.[key] ?? 0}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="admin-card">
        <h3 className="admin-section-title">System status</h3>
        <p style={{ color: "#64748b", margin: 0 }}>
          Authentication and RBAC services are operational.
        </p>
      </div>
    </div>
  );
}
