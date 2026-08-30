import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchExperts } from "../../services/mobileAdminApi";
import useMobileList from "../useMobileList";
import RecordTable from "../components/RecordTable";
import Pagination from "../components/Pagination";
import ErrorBanner from "../components/ErrorBanner";
import StatusBadge from "../components/StatusBadge";
import { formatDateTime } from "../format";
import "../mobile-admin.css";

/** Review queues over `counsellor_profiles.status`, exactly as the Mobile
 *  backend stores it. "none" is the marker the API uses for an expert account
 *  with no profile row yet — signed up, never opened the onboarding wizard. */
const TABS = [
  {
    key: "pending",
    label: "Pending review",
    status: ["pending_review"],
    sort: { sort_by: "submitted_at", sort_dir: "desc" },
  },
  {
    key: "recent",
    label: "Recently submitted",
    status: ["pending_review", "active", "rejected", "inactive"],
    sort: { sort_by: "submitted_at", sort_dir: "desc" },
  },
  { key: "rejected", label: "Rejected", status: ["rejected"] },
  { key: "active", label: "Active", status: ["active"] },
  { key: "inactive", label: "Inactive", status: ["inactive"] },
  { key: "unsubmitted", label: "Not submitted", status: ["draft", "none"] },
  { key: "all", label: "All", status: null },
];

const CATEGORIES = [
  "therapist/counselor",
  "clinical psychiatrist",
  "clinical doctor",
  "behavioral analyst",
  "fitness coach",
  "nutritionist",
  "business mentor",
  "other",
];

const SORTS = [
  { value: "created_at", label: "Signed up" },
  { value: "submitted_at", label: "Last profile update" },
  { value: "full_name", label: "Name" },
  { value: "email", label: "Email" },
  { value: "status", label: "Status" },
  { value: "professional_category", label: "Category" },
];

const TRISTATE = [
  { value: "", label: "Any" },
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

function tri(value) {
  return value === "" ? undefined : value === "true";
}

export default function MobileExperts() {
  const [tabKey, setTabKey] = useState("pending");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [category, setCategory] = useState("");
  const [accountActive, setAccountActive] = useState("");
  const [questionnaire, setQuestionnaire] = useState("");
  const [documents, setDocuments] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");

  const tab = TABS.find((t) => t.key === tabKey) || TABS[0];

  const filters = useMemo(
    () => ({
      status: tab.status,
      search: search || undefined,
      professional_category: category || undefined,
      is_active: tri(accountActive),
      questionnaire_submitted: tri(questionnaire),
      has_documents: tri(documents),
      sort_by: tab.sort?.sort_by || sortBy,
      sort_dir: tab.sort?.sort_dir || sortDir,
    }),
    [tab, search, category, accountActive, questionnaire, documents, sortBy, sortDir]
  );

  const { items, page, data, loading, error, offset, setOffset, reload } =
    useMobileList(fetchExperts, filters);

  const counts = data?.counts_by_status || {};

  const columns = [
    {
      key: "full_name",
      label: "Expert",
      render: (row) => (
        <div>
          <Link className="admin-link" to={`/admin/mobile/experts/${row.user_id}`}>
            {row.full_name}
          </Link>
          <div className="mobile-muted">{row.email}</div>
        </div>
      ),
    },
    {
      key: "professional_category",
      label: "Category",
      render: (row) =>
        row.professional_category || <span className="mobile-muted">—</span>,
    },
    {
      key: "status",
      label: "Profile status",
      render: (row) => <StatusBadge value={row.has_profile ? row.status : "none"} />,
    },
    {
      key: "questionnaire_submitted",
      label: "Questionnaire",
      render: (row) =>
        row.questionnaire_submitted ? (
          <span className="mobile-status ok">Submitted</span>
        ) : (
          <span className="mobile-muted">Not submitted</span>
        ),
    },
    {
      key: "documents_provided",
      label: "Documents",
      render: (row) => (
        <div>
          <span className={row.documents_provided ? "" : "mobile-muted"}>
            {row.documents_provided} provided
          </span>
          {row.has_documents && (
            <div>
              <StatusBadge value={row.document_status} />
            </div>
          )}
        </div>
      ),
    },
    {
      key: "is_active",
      label: "Account",
      render: (row) => (
        <span className={`admin-badge ${row.is_active ? "active" : "inactive"}`}>
          {row.is_active ? "enabled" : "disabled"}
        </span>
      ),
    },
    {
      key: "is_listed_in_directory",
      label: "Visible to students",
      render: (row) => (
        <div>
          <span className={row.is_listed_in_directory ? "mobile-status ok" : "mobile-muted"}>
            {row.is_listed_in_directory ? "Listed" : "Not listed"}
          </span>
          {row.is_listed_in_directory && !row.is_bookable && (
            <div className="mobile-muted">no bookable slot</div>
          )}
        </div>
      ),
    },
    {
      key: "created_at",
      label: "Signed up",
      render: (row) => formatDateTime(row.created_at),
    },
  ];

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Counsellors / Experts</h1>
          <p className="admin-page-sub">
            Applications submitted from the Sentio mobile app, read from the Mobile
            backend.
          </p>
        </div>
        <button type="button" className="admin-btn" onClick={reload} disabled={loading}>
          Refresh
        </button>
      </div>

      <ErrorBanner error={error} onRetry={reload} />

      <div className="admin-tabs">
        {TABS.map((t) => {
          const badge =
            t.status?.length === 1 && counts[t.status[0]] !== undefined
              ? ` (${counts[t.status[0]]})`
              : "";
          return (
            <button
              key={t.key}
              type="button"
              className={t.key === tabKey ? "active" : ""}
              onClick={() => setTabKey(t.key)}
            >
              {t.label}
              {badge}
            </button>
          );
        })}
      </div>

      <div className="admin-card mobile-filters">
        <form
          className="mobile-filter-search"
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(searchInput.trim());
          }}
        >
          <input
            className="mobile-input"
            type="search"
            placeholder="Search name or email"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button type="submit" className="admin-btn">
            Search
          </button>
          {search && (
            <button
              type="button"
              className="admin-btn"
              onClick={() => {
                setSearch("");
                setSearchInput("");
              }}
            >
              Clear
            </button>
          )}
        </form>

        <label className="mobile-filter">
          <span>Category</span>
          <select
            className="mobile-input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">Any</option>
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>

        <label className="mobile-filter">
          <span>Account enabled</span>
          <select
            className="mobile-input"
            value={accountActive}
            onChange={(e) => setAccountActive(e.target.value)}
          >
            {TRISTATE.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mobile-filter">
          <span>Questionnaire</span>
          <select
            className="mobile-input"
            value={questionnaire}
            onChange={(e) => setQuestionnaire(e.target.value)}
          >
            {TRISTATE.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mobile-filter">
          <span>Documents</span>
          <select
            className="mobile-input"
            value={documents}
            onChange={(e) => setDocuments(e.target.value)}
          >
            {TRISTATE.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mobile-filter">
          <span>Sort by</span>
          <select
            className="mobile-input"
            value={tab.sort?.sort_by || sortBy}
            disabled={Boolean(tab.sort)}
            onChange={(e) => setSortBy(e.target.value)}
          >
            {SORTS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mobile-filter">
          <span>Direction</span>
          <select
            className="mobile-input"
            value={tab.sort?.sort_dir || sortDir}
            disabled={Boolean(tab.sort)}
            onChange={(e) => setSortDir(e.target.value)}
          >
            <option value="desc">Newest first</option>
            <option value="asc">Oldest first</option>
          </select>
        </label>
      </div>

      <RecordTable
        columns={columns}
        items={items}
        loading={loading}
        emptyLabel="No expert applications match these filters."
      />

      <Pagination page={{ ...page, offset }} onChange={setOffset} busy={loading} />
    </div>
  );
}
