import { useState } from "react";
import { Link } from "react-router-dom";
import { fetchMobileAudit, fetchMobileEvents } from "../../services/mobileAdminApi";
import { useMobileAdmin } from "../MobileAdminContext";
import useMobileList from "../useMobileList";
import RecordTable from "../components/RecordTable";
import Pagination from "../components/Pagination";
import ErrorBanner from "../components/ErrorBanner";
import { DASH, formatDateTime, formatValue } from "../format";
import "../mobile-admin.css";

const AUDIT_COLUMNS = [
  {
    key: "created_at",
    label: "When",
    render: (row) => formatDateTime(row.created_at),
  },
  {
    key: "actor_subject",
    label: "Admin",
    render: (row) => (
      <div>
        {row.actor_email || row.actor_subject}
        <div className="mobile-muted">{row.actor_role}</div>
      </div>
    ),
  },
  {
    key: "action",
    label: "Action",
    render: (row) => <span className="admin-badge role">{row.action}</span>,
  },
  {
    key: "target_id",
    label: "Target",
    render: (row) =>
      row.target_id ? (
        <Link className="admin-link" to={`/admin/mobile/experts/${row.target_id}`}>
          {row.target_type}
        </Link>
      ) : (
        row.target_type || DASH
      ),
  },
  {
    key: "to_value",
    label: "Change",
    render: (row) =>
      row.from_value || row.to_value ? (
        <span>
          {row.from_value || DASH} → <strong>{row.to_value || DASH}</strong>
        </span>
      ) : (
        DASH
      ),
  },
  {
    key: "reason",
    label: "Reason",
    render: (row) => row.reason || DASH,
  },
];

const EVENT_COLUMNS = [
  {
    key: "created_at",
    label: "When",
    render: (row) => formatDateTime(row.created_at),
  },
  {
    key: "event_type",
    label: "Event",
    render: (row) => <span className="admin-badge role">{row.event_type}</span>,
  },
  {
    key: "user_id",
    label: "User",
    render: (row) =>
      row.user_id ? (
        <Link className="admin-link" to={`/admin/mobile/users/${row.user_id}`}>
          {row.user_id}
        </Link>
      ) : (
        DASH
      ),
  },
  {
    key: "payload",
    label: "Payload",
    render: (row) => <code className="mobile-code">{formatValue(row.payload)}</code>,
  },
];

export default function MobileAudit() {
  const { can } = useMobileAdmin();
  const canReadAudit = can("audit.read");

  const [tabKey, setTabKey] = useState(canReadAudit ? "audit" : "events");
  const [action, setAction] = useState("");
  const [actionInput, setActionInput] = useState("");
  const [eventType, setEventType] = useState("");
  const [eventTypeInput, setEventTypeInput] = useState("");

  const isAudit = tabKey === "audit";

  const { items, page, loading, error, offset, setOffset, reload } = useMobileList(
    isAudit ? fetchMobileAudit : fetchMobileEvents,
    isAudit
      ? { _tab: "audit", action: action || undefined }
      : { _tab: "events", event_type: eventType || undefined },
    { limit: 50 }
  );

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Audit & activity</h1>
          <p className="admin-page-sub">
            Admin actions taken through this console, and app-side events from the
            Mobile backend.
          </p>
        </div>
        <button type="button" className="admin-btn" onClick={reload} disabled={loading}>
          Refresh
        </button>
      </div>

      <div className="admin-tabs">
        <button
          type="button"
          className={isAudit ? "active" : ""}
          onClick={() => setTabKey("audit")}
        >
          Admin actions
        </button>
        <button
          type="button"
          className={!isAudit ? "active" : ""}
          onClick={() => setTabKey("events")}
        >
          App events
        </button>
      </div>

      {isAudit && !canReadAudit && (
        <div className="admin-banner error" role="alert">
          <strong>Not authorized</strong>
          <div>
            The admin audit log requires <code>mobile.audit.read</code>, which a Mobile
            Secondary Admin does not hold. Your own actions on an application are still
            visible in that expert&apos;s review history.
          </div>
        </div>
      )}

      <ErrorBanner error={error} onRetry={reload} />

      <div className="admin-card mobile-filters">
        <form
          className="mobile-filter-search"
          onSubmit={(e) => {
            e.preventDefault();
            if (isAudit) setAction(actionInput.trim());
            else setEventType(eventTypeInput.trim());
          }}
        >
          <input
            className="mobile-input"
            type="search"
            placeholder={isAudit ? "Filter by action" : "Filter by event type"}
            value={isAudit ? actionInput : eventTypeInput}
            onChange={(e) =>
              isAudit ? setActionInput(e.target.value) : setEventTypeInput(e.target.value)
            }
          />
          <button type="submit" className="admin-btn">
            Filter
          </button>
        </form>
      </div>

      <RecordTable
        columns={isAudit ? AUDIT_COLUMNS : EVENT_COLUMNS}
        items={items}
        loading={loading}
        emptyLabel={isAudit ? "No admin actions recorded." : "No events recorded."}
      />

      <Pagination page={{ ...page, offset }} onChange={setOffset} busy={loading} />
    </div>
  );
}
