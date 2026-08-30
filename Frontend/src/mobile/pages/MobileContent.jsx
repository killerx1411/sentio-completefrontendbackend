import { useState } from "react";
import { fetchInterventionRules, fetchNutrition } from "../../services/mobileAdminApi";
import useMobileList from "../useMobileList";
import RecordTable from "../components/RecordTable";
import Pagination from "../components/Pagination";
import ErrorBanner from "../components/ErrorBanner";
import SafeLink from "../components/SafeLink";
import { formatDateTime } from "../format";
import "../mobile-admin.css";

const NUTRITION_COLUMNS = [
  {
    key: "title",
    label: "Item",
    render: (row) => (
      <div>
        {row.title}
        <div className="mobile-muted">{row.slug}</div>
      </div>
    ),
  },
  { key: "content_type", label: "Type" },
  {
    key: "description",
    label: "Description",
    render: (row) => row.description || "—",
  },
  {
    key: "is_premium",
    label: "Premium",
    render: (row) => (row.is_premium ? "Yes" : "No"),
  },
  {
    key: "is_active",
    label: "State",
    render: (row) => (
      <span className={`admin-badge ${row.is_active ? "active" : "inactive"}`}>
        {row.is_active ? "active" : "inactive"}
      </span>
    ),
  },
  {
    key: "media_url",
    label: "Media",
    render: (row) => <SafeLink url={row.media_url} label="Open" />,
  },
];

const RULE_COLUMNS = [
  { key: "rule_id", label: "Rule" },
  { key: "category", label: "Category" },
  { key: "rule_class", label: "Class" },
  { key: "version", label: "Version" },
  {
    key: "status",
    label: "Status",
    render: (row) => <span className="admin-badge role">{row.status}</span>,
  },
  {
    key: "is_active",
    label: "Active",
    render: (row) => (row.is_active ? "Yes" : "No"),
  },
  {
    key: "approved_at",
    label: "Approved",
    render: (row) => formatDateTime(row.approved_at),
  },
];

const TABS = [
  {
    key: "nutrition",
    label: "Nutrition",
    fetcher: fetchNutrition,
    columns: NUTRITION_COLUMNS,
    limit: 50,
    empty: "No nutrition content.",
  },
  {
    key: "rules",
    label: "Intervention rules",
    fetcher: fetchInterventionRules,
    columns: RULE_COLUMNS,
    limit: 100,
    empty: "No intervention rules.",
  },
];

export default function MobileContent() {
  const [tabKey, setTabKey] = useState("nutrition");
  const tab = TABS.find((t) => t.key === tabKey) || TABS[0];

  const { items, page, loading, error, offset, setOffset, reload } = useMobileList(
    tab.fetcher,
    { _tab: tab.key },
    { limit: tab.limit }
  );

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Content & interventions</h1>
          <p className="admin-page-sub">
            The nutrition library and the intervention rule set the mobile app runs on.
            Read-only in this console.
          </p>
        </div>
        <button type="button" className="admin-btn" onClick={reload} disabled={loading}>
          Refresh
        </button>
      </div>

      <ErrorBanner error={error} onRetry={reload} />

      <div className="admin-tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={t.key === tabKey ? "active" : ""}
            onClick={() => setTabKey(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <RecordTable
        columns={tab.columns}
        items={items}
        loading={loading}
        emptyLabel={tab.empty}
      />

      <Pagination page={{ ...page, offset }} onChange={setOffset} busy={loading} />
    </div>
  );
}
