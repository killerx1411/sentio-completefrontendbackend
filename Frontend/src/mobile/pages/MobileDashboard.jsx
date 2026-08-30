import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ClipboardList, ShieldAlert, Users } from "lucide-react";
import { fetchMobileDashboard, fetchExpertStats } from "../../services/mobileAdminApi";
import { useMobileAdmin } from "../MobileAdminContext";
import ErrorBanner from "../components/ErrorBanner";
import { humanize } from "../format";
import "../mobile-admin.css";

function Breakdown({ title, counts, emptyLabel = "Nothing recorded." }) {
  const entries = Object.entries(counts || {});
  return (
    <div className="admin-card">
      <h3 className="admin-section-title">{title}</h3>
      {entries.length === 0 ? (
        <p className="mobile-muted">{emptyLabel}</p>
      ) : (
        <ul className="mobile-breakdown">
          {entries.map(([key, value]) => (
            <li key={key}>
              <span>{humanize(key)}</span>
              <strong>{value}</strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MobileDashboard() {
  const { identity } = useMobileAdmin();
  const [counts, setCounts] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, expertStats] = await Promise.all([
        fetchMobileDashboard(),
        fetchExpertStats(),
      ]);
      setCounts(dashboard);
      setStats(expertStats);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const cards = [
    {
      key: "awaiting",
      label: "Awaiting review",
      value: counts?.experts_awaiting_review,
      icon: ClipboardList,
      color: "#0f4c5c",
      to: "/admin/mobile/experts",
    },
    {
      key: "experts",
      label: "Experts",
      value: counts?.experts_total,
      icon: Activity,
      color: "#2ec4b6",
      to: "/admin/mobile/experts",
    },
    {
      key: "users",
      label: "App users",
      value: counts?.users_total,
      icon: Users,
      color: "#475569",
      to: "/admin/mobile/users",
    },
    {
      key: "risk",
      label: "Open risk flags",
      value: Object.values(counts?.open_risk_flags_by_tier || {}).reduce(
        (sum, n) => sum + n,
        0
      ),
      icon: ShieldAlert,
      color: "#b91c1c",
      to: "/admin/mobile/risk",
    },
  ];

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Mobile dashboard</h1>
          <p className="admin-page-sub">
            Signed in as {identity?.email || identity?.subject} ·{" "}
            {identity?.role === "mobile_super_admin"
              ? "Mobile Super Admin"
              : "Mobile Secondary Admin"}
          </p>
        </div>
        <button type="button" className="admin-btn" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>

      <ErrorBanner error={error} onRetry={load} />

      {stats && !stats.review_queue_enabled && (
        <div className="admin-banner error" role="alert">
          <strong>The review queue is disabled.</strong>
          <div>
            COUNSELLOR_AUTO_APPROVE is ON in the Mobile backend, so a submitted
            application is published straight to <code>active</code> and never reaches
            this queue. See Settings.
          </div>
        </div>
      )}

      <div className="admin-stats-grid">
        {cards.map(({ key, label, value, icon: Icon, color, to }) => (
          <Link key={key} to={to} className="admin-card admin-stat-card mobile-stat-link">
            <div
              className="admin-stat-icon"
              style={{ backgroundColor: `${color}15`, color }}
            >
              <Icon size={22} />
            </div>
            <div>
              <p className="admin-stat-label">{label}</p>
              <p className="admin-stat-value">{loading ? "…" : (value ?? 0)}</p>
            </div>
          </Link>
        ))}
      </div>

      <div className="mobile-grid-2">
        <Breakdown title="Experts by status" counts={counts?.experts_by_status} />
        <Breakdown title="Users by role" counts={counts?.users_by_role} />
        <Breakdown title="Sessions by status" counts={counts?.sessions_by_status} />
        <Breakdown
          title="Open risk flags by tier"
          counts={counts?.open_risk_flags_by_tier}
          emptyLabel="No open risk flags."
        />
        <Breakdown
          title="Subscriptions by status"
          counts={counts?.subscriptions_by_status}
        />
        <Breakdown
          title="Last 7 days"
          counts={
            counts
              ? {
                  new_signups: counts.recent_signups_7d,
                  applications_submitted: counts.recent_submissions_7d,
                  active_users: counts.users_active,
                }
              : null
          }
        />
      </div>
    </div>
  );
}
