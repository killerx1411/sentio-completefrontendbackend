import { useMemo, useState } from "react";
import SimpleListPage from "../components/SimpleListPage";
import { fetchExercises } from "../../services/mobileAdminApi";
import SafeLink from "../components/SafeLink";
import "../mobile-admin.css";

const COLUMNS = [
  {
    key: "title",
    label: "Exercise",
    render: (row) => (
      <div>
        {row.title}
        <div className="mobile-muted">{row.slug}</div>
      </div>
    ),
  },
  { key: "content_type", label: "Type" },
  {
    key: "duration_seconds",
    label: "Duration",
    render: (row) =>
      row.duration_seconds ? `${Math.round(row.duration_seconds / 60)} min` : "—",
  },
  { key: "difficulty_level", label: "Difficulty" },
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

export default function MobileExercises() {
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const params = useMemo(() => ({ search: search || undefined }), [search]);

  return (
    <SimpleListPage
      title="Exercises"
      subtitle="The exercise library served to the mobile app. Read-only in this console."
      fetcher={fetchExercises}
      params={params}
      columns={COLUMNS}
      limit={50}
      emptyLabel="No exercises match this search."
    >
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
            placeholder="Search title or slug"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button type="submit" className="admin-btn">
            Search
          </button>
        </form>
      </div>
    </SimpleListPage>
  );
}
