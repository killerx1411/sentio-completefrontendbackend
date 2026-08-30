import { useMemo, useState } from "react";
import SimpleListPage from "../components/SimpleListPage";
import { fetchSubscriptions } from "../../services/mobileAdminApi";
import { formatDate, formatDateTime } from "../format";
import "../mobile-admin.css";

const STATUSES = [
  { value: "", label: "Any" },
  { value: "active", label: "Active" },
  { value: "trialing", label: "Trialing" },
  { value: "past_due", label: "Past due" },
  { value: "cancelled", label: "Cancelled" },
  { value: "incomplete", label: "Incomplete" },
];

const COLUMNS = [
  {
    key: "user_name",
    label: "User",
    render: (row) => (
      <div>
        {row.user_name || "—"}
        <div className="mobile-muted">{row.user_email}</div>
      </div>
    ),
  },
  {
    key: "plan",
    label: "Plan",
    render: (row) => (
      <div>
        {row.plan}
        <div className="mobile-muted">{row.plan_key}</div>
      </div>
    ),
  },
  {
    key: "status",
    label: "Status",
    render: (row) => <span className="admin-badge role">{row.status}</span>,
  },
  { key: "billing_cycle", label: "Cycle" },
  {
    key: "current_period_end",
    label: "Period ends",
    render: (row) => formatDate(row.current_period_end),
  },
  {
    key: "is_auto_renew",
    label: "Auto renew",
    render: (row) => (row.is_auto_renew ? "Yes" : "No"),
  },
  {
    key: "grace_period_end",
    label: "Grace ends",
    render: (row) => formatDate(row.grace_period_end),
  },
  {
    key: "cancelled_at",
    label: "Cancelled",
    render: (row) => formatDateTime(row.cancelled_at),
  },
];

export default function MobileSubscriptions() {
  const [status, setStatus] = useState("");
  const params = useMemo(() => ({ status: status || undefined }), [status]);

  return (
    <SimpleListPage
      title="Plans & subscriptions"
      subtitle="Live subscription records for mobile app users. Read-only."
      fetcher={fetchSubscriptions}
      params={params}
      columns={COLUMNS}
      filters={[{ key: "status", label: "Status", options: STATUSES }]}
      values={{ status }}
      onChange={(_, value) => setStatus(value)}
      emptyLabel="No subscriptions match this filter."
    />
  );
}
