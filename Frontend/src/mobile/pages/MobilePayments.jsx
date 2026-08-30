import { useMemo, useState } from "react";
import SimpleListPage from "../components/SimpleListPage";
import { fetchPayments } from "../../services/mobileAdminApi";
import { formatDateTime, formatMoney } from "../format";
import "../mobile-admin.css";

const STATUSES = [
  { value: "", label: "Any" },
  { value: "pending", label: "Pending" },
  { value: "authorized", label: "Authorized" },
  { value: "captured", label: "Captured" },
  { value: "reconciled", label: "Reconciled" },
  { value: "failed", label: "Failed" },
  { value: "refunded", label: "Refunded" },
];

const COLUMNS = [
  {
    key: "created_at",
    label: "Created",
    render: (row) => formatDateTime(row.created_at),
  },
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
  { key: "plan", label: "Plan" },
  { key: "billing_cycle", label: "Cycle" },
  {
    key: "amount_cents",
    label: "Amount",
    render: (row) => formatMoney(row.amount_cents, row.currency),
  },
  {
    key: "refunded_amount_cents",
    label: "Refunded",
    render: (row) =>
      row.refunded_amount_cents
        ? formatMoney(row.refunded_amount_cents, row.currency)
        : "—",
  },
  {
    key: "status",
    label: "Status",
    render: (row) => <span className="admin-badge role">{row.status}</span>,
  },
  { key: "provider", label: "Provider" },
  {
    key: "failure_reason",
    label: "Failure",
    render: (row) =>
      row.failure_reason ? (
        <span className="mobile-status bad">{row.failure_reason}</span>
      ) : (
        "—"
      ),
  },
];

export default function MobilePayments() {
  const [status, setStatus] = useState("");
  const params = useMemo(() => ({ status: status || undefined }), [status]);

  return (
    <SimpleListPage
      title="Payments"
      subtitle="Payment records from the mobile app's billing module. Read-only."
      fetcher={fetchPayments}
      params={params}
      columns={COLUMNS}
      filters={[{ key: "status", label: "Status", options: STATUSES }]}
      values={{ status }}
      onChange={(_, value) => setStatus(value)}
      emptyLabel="No payments match this filter."
    />
  );
}
