import { useMemo, useState } from "react";
import SimpleListPage from "../components/SimpleListPage";
import { fetchSessions } from "../../services/mobileAdminApi";
import { formatDateTime, formatMoney } from "../format";
import "../mobile-admin.css";

const STATUSES = [
  { value: "", label: "Any" },
  { value: "pending_payment", label: "Pending payment" },
  { value: "confirmed", label: "Confirmed" },
  { value: "payment_failed", label: "Payment failed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "completed", label: "Completed" },
];

const COLUMNS = [
  {
    key: "scheduled_start",
    label: "Scheduled",
    render: (row) => formatDateTime(row.scheduled_start),
  },
  {
    key: "student_name",
    label: "Student",
    render: (row) => (
      <div>
        {row.student_name}
        <div className="mobile-muted">{row.student_email}</div>
      </div>
    ),
  },
  {
    key: "counsellor_name",
    label: "Counsellor",
    render: (row) => (
      <div>
        {row.counsellor_name}
        <div className="mobile-muted">{row.counsellor_email}</div>
      </div>
    ),
  },
  { key: "session_mode", label: "Mode" },
  {
    key: "duration_minutes",
    label: "Duration",
    render: (row) => (row.duration_minutes ? `${row.duration_minutes} min` : "—"),
  },
  {
    key: "status",
    label: "Status",
    render: (row) => <span className="admin-badge role">{row.status}</span>,
  },
  { key: "payment_status", label: "Payment" },
  {
    key: "amount_cents",
    label: "Amount",
    render: (row) => formatMoney(row.amount_cents, row.currency),
  },
];

export default function MobileSessions() {
  const [status, setStatus] = useState("");
  const params = useMemo(() => ({ status: status || undefined }), [status]);

  return (
    <SimpleListPage
      title="Sessions"
      subtitle="Counsellor sessions booked in the mobile app. Read-only."
      fetcher={fetchSessions}
      params={params}
      columns={COLUMNS}
      filters={[{ key: "status", label: "Status", options: STATUSES }]}
      values={{ status }}
      onChange={(_, value) => setStatus(value)}
      emptyLabel="No sessions match this filter."
    />
  );
}
