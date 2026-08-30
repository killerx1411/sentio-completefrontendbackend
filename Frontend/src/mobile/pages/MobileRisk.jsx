import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import SimpleListPage from "../components/SimpleListPage";
import { fetchRiskFlags, fetchRiskThresholds } from "../../services/mobileAdminApi";
import { formatDateTime, formatValue } from "../format";
import "../mobile-admin.css";

const TIERS = [
  { value: "", label: "Any" },
  { value: "watch", label: "Watch" },
  { value: "elevated", label: "Elevated" },
  { value: "urgent", label: "Urgent" },
];

const REVIEW_STATUSES = [
  { value: "", label: "Any" },
  { value: "active", label: "Active" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
  { value: "dismissed", label: "Dismissed" },
];

const TIER_TONE = { urgent: "bad", elevated: "warn", watch: "muted" };

const COLUMNS = [
  {
    key: "created_at",
    label: "Raised",
    render: (row) => formatDateTime(row.created_at),
  },
  {
    key: "user_name",
    label: "User",
    render: (row) => (
      <div>
        <Link className="admin-link" to={`/admin/mobile/users/${row.user_id}`}>
          {row.user_name || row.user_id}
        </Link>
        <div className="mobile-muted">{row.user_email}</div>
      </div>
    ),
  },
  {
    key: "tier",
    label: "Tier",
    render: (row) => (
      <span className={`mobile-status ${TIER_TONE[row.tier] || "muted"}`}>{row.tier}</span>
    ),
  },
  {
    key: "review_status",
    label: "Review status",
    render: (row) => <span className="admin-badge role">{row.review_status}</span>,
  },
  { key: "scan_count", label: "Scans" },
  {
    key: "contributing_signals",
    label: "Signals",
    render: (row) => formatValue(row.contributing_signals),
  },
  {
    key: "acknowledged_at",
    label: "Acknowledged",
    render: (row) => formatDateTime(row.acknowledged_at),
  },
  {
    key: "resolved_at",
    label: "Resolved",
    render: (row) => formatDateTime(row.resolved_at),
  },
];

function Thresholds() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchRiskThresholds();
      setItems(data.items || []);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return null;

  return (
    <div className="admin-card">
      <h3 className="admin-section-title">Risk thresholds</h3>
      {!items ? (
        <p className="admin-empty">Loading…</p>
      ) : items.length === 0 ? (
        <p className="mobile-muted">No thresholds configured.</p>
      ) : (
        <ul className="mobile-breakdown">
          {items.map((item) => (
            <li key={item.id}>
              <span>
                {item.label}
                <span className="mobile-muted">
                  {" "}
                  · {item.status}
                  {item.is_active ? " · active" : ""}
                </span>
              </span>
              <span className="mobile-muted">
                {item.approved_at ? `approved ${formatDateTime(item.approved_at)}` : "—"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MobileRisk() {
  const [tier, setTier] = useState("");
  const [reviewStatus, setReviewStatus] = useState("");

  const params = useMemo(
    () => ({ tier: tier || undefined, review_status: reviewStatus || undefined }),
    [tier, reviewStatus]
  );

  return (
    <SimpleListPage
      title="Risk & clinical safety"
      subtitle="Risk flags are observed here, never clinically resolved: acknowledging or resolving a flag is a counsellor action in the mobile app."
      fetcher={fetchRiskFlags}
      params={params}
      columns={COLUMNS}
      filters={[
        { key: "tier", label: "Tier", options: TIERS },
        { key: "review_status", label: "Review status", options: REVIEW_STATUSES },
      ]}
      values={{ tier, review_status: reviewStatus }}
      onChange={(key, value) =>
        key === "tier" ? setTier(value) : setReviewStatus(value)
      }
      emptyLabel="No risk flags match these filters."
    >
      <Thresholds />
    </SimpleListPage>
  );
}
