import { formatValue, humanize } from "../format";

/**
 * Table over rows returned by a Mobile Admin list endpoint.
 *
 * SECURITY: the API already curates its columns, but this component is the last
 * gate before rendering, so any key that looks like a credential, token or
 * secret is dropped even if a future endpoint starts returning one.
 */
const DENY = /(password|hash|secret|token|fcm|api[_-]?key|dispatch|credential|authorization|jwt|salt|otp)/i;

export function visibleColumns(columns) {
  return columns.filter((col) => !DENY.test(col.key));
}

export default function RecordTable({ columns, items, loading, emptyLabel = "Nothing to show." }) {
  const cols = visibleColumns(columns);

  return (
    <div className="admin-card admin-table-wrap">
      {loading ? (
        <p className="admin-empty">Loading…</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              {cols.map((col) => (
                <th key={col.key}>{col.label || humanize(col.key)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={cols.length} className="admin-empty-cell">
                  {emptyLabel}
                </td>
              </tr>
            ) : (
              items.map((item, index) => (
                <tr key={item.id || item.user_id || index}>
                  {cols.map((col) => (
                    <td key={col.key}>
                      {col.render ? col.render(item) : formatValue(item[col.key])}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
