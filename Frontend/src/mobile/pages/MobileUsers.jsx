import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMobileUsers } from "../../services/mobileAdminApi";
import useMobileList from "../useMobileList";
import RecordTable from "../components/RecordTable";
import Pagination from "../components/Pagination";
import ErrorBanner from "../components/ErrorBanner";
import { formatDateTime } from "../format";
import "../mobile-admin.css";

const TRISTATE = [
  { value: "", label: "Any" },
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

function tri(value) {
  return value === "" ? undefined : value === "true";
}

export default function MobileUsers() {
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [onboarded, setOnboarded] = useState("");
  const [sortDir, setSortDir] = useState("desc");

  const filters = useMemo(
    () => ({
      search: search || undefined,
      role: role || undefined,
      is_active: tri(active),
      onboarded: tri(onboarded),
      sort_dir: sortDir,
    }),
    [search, role, active, onboarded, sortDir]
  );

  const { items, page, loading, error, offset, setOffset, reload } = useMobileList(
    fetchMobileUsers,
    filters
  );

  const columns = [
    {
      key: "full_name",
      label: "User",
      render: (row) => (
        <div>
          <Link className="admin-link" to={`/admin/mobile/users/${row.id}`}>
            {row.full_name}
          </Link>
          <div className="mobile-muted">{row.email}</div>
        </div>
      ),
    },
    { key: "role", label: "Role" },
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
      key: "onboarded",
      label: "Onboarded",
      render: (row) => (row.onboarded ? "Yes" : "No"),
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
          <h1 className="admin-page-title">Mobile app users</h1>
          <p className="admin-page-sub">
            Every account in the Sentio mobile app — students and experts alike.
          </p>
        </div>
        <button type="button" className="admin-btn" onClick={reload} disabled={loading}>
          Refresh
        </button>
      </div>

      <ErrorBanner error={error} onRetry={reload} />

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
        </form>

        <label className="mobile-filter">
          <span>Role</span>
          <input
            className="mobile-input"
            type="text"
            placeholder="e.g. user, counsellor"
            value={role}
            onChange={(e) => setRole(e.target.value.trim())}
          />
        </label>

        <label className="mobile-filter">
          <span>Account enabled</span>
          <select
            className="mobile-input"
            value={active}
            onChange={(e) => setActive(e.target.value)}
          >
            {TRISTATE.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mobile-filter">
          <span>Onboarded</span>
          <select
            className="mobile-input"
            value={onboarded}
            onChange={(e) => setOnboarded(e.target.value)}
          >
            {TRISTATE.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mobile-filter">
          <span>Signed up</span>
          <select
            className="mobile-input"
            value={sortDir}
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
        emptyLabel="No users match these filters."
      />

      <Pagination page={{ ...page, offset }} onChange={setOffset} busy={loading} />
    </div>
  );
}
