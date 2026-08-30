import { useCallback, useEffect, useState } from "react";
import { fetchMobileSettings } from "../../services/mobileAdminApi";
import ErrorBanner from "../components/ErrorBanner";
import { formatValue } from "../format";
import "../mobile-admin.css";

/** Defence in depth: the endpoint returns a curated set, but nothing whose key
 *  looks like a credential is ever rendered here. */
const DENY = /(secret|password|token|key|credential|dsn|url_with|dispatch)/i;

export default function MobileSettings() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchMobileSettings());
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const entries = Object.entries(data?.values || {}).filter(([key]) => !DENY.test(key));

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Settings</h1>
          <p className="admin-page-sub">
            Process configuration of the Mobile backend, read-only. Changing one of
            these is a deploy, not a console action.
          </p>
        </div>
        <button type="button" className="admin-btn" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>

      <ErrorBanner error={error} onRetry={load} />

      {loading ? (
        <p className="admin-empty">Loading…</p>
      ) : (
        data && (
          <>
            <div
              className={`admin-banner ${data.review_queue_enabled ? "success" : "error"}`}
              role="status"
            >
              <strong>
                {data.review_queue_enabled
                  ? "The counsellor review queue is enabled."
                  : "The counsellor review queue is disabled."}
              </strong>
              <div>
                {data.review_queue_enabled
                  ? "A submitted application waits in pending_review until an admin acts on it."
                  : "COUNSELLOR_AUTO_APPROVE is ON, so a submitted application is published straight to active and never reaches this console."}
              </div>
            </div>

            <div className="admin-card admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Setting</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map(([key, value]) => (
                    <tr key={key}>
                      <td>
                        <code className="mobile-code">{key}</code>
                      </td>
                      <td>{formatValue(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="admin-card">
              <h3 className="admin-section-title">Notes from the backend</h3>
              <ul className="mobile-notes">
                {(data.notes || []).map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          </>
        )
      )}
    </div>
  );
}
