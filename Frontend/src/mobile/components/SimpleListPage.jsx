import useMobileList from "../useMobileList";
import RecordTable from "./RecordTable";
import Pagination from "./Pagination";
import ErrorBanner from "./ErrorBanner";

/**
 * A read-only Mobile Admin list: header, optional filter selects, table,
 * pagination. Used by the operational surfaces that the Mobile Admin API
 * exposes for reading only.
 *
 * `filters` is an array of { key, label, options: [{value,label}] } and
 * `values` / `onChange` keep them controlled by the caller, so a page can put
 * its own state (or none at all) behind them.
 */
export default function SimpleListPage({
  title,
  subtitle,
  fetcher,
  params,
  columns,
  filters = [],
  values = {},
  onChange,
  emptyLabel,
  limit = 25,
  children,
}) {
  const { items, page, loading, error, offset, setOffset, reload } = useMobileList(
    fetcher,
    params,
    { limit }
  );

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">{title}</h1>
          {subtitle && <p className="admin-page-sub">{subtitle}</p>}
        </div>
        <button type="button" className="admin-btn" onClick={reload} disabled={loading}>
          Refresh
        </button>
      </div>

      <ErrorBanner error={error} onRetry={reload} />

      {children}

      {filters.length > 0 && (
        <div className="admin-card mobile-filters">
          {filters.map((filter) => (
            <label key={filter.key} className="mobile-filter">
              <span>{filter.label}</span>
              <select
                className="mobile-input"
                value={values[filter.key] ?? ""}
                onChange={(e) => onChange(filter.key, e.target.value)}
              >
                {filter.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      )}

      <RecordTable
        columns={columns}
        items={items}
        loading={loading}
        emptyLabel={emptyLabel}
      />

      <Pagination page={{ ...page, offset }} onChange={setOffset} busy={loading} />
    </div>
  );
}
