/** Offset pagination over the `page` object every list endpoint returns. */

export default function Pagination({ page, onChange, busy }) {
  if (!page) return null;
  const { total = 0, limit = 25, offset = 0 } = page;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  const canPrev = offset > 0;
  const canNext = offset + limit < total;

  return (
    <div className="mobile-pagination">
      <span className="mobile-muted">
        {from}–{to} of {total}
      </span>
      <div className="mobile-pagination-actions">
        <button
          type="button"
          className="admin-btn"
          disabled={!canPrev || busy}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          Previous
        </button>
        <button
          type="button"
          className="admin-btn"
          disabled={!canNext || busy}
          onClick={() => onChange(offset + limit)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
