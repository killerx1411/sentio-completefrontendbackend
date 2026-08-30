import { useCallback, useEffect, useState } from "react";
import { fetchMobileHealth } from "../../services/mobileAdminApi";
import ErrorBanner from "../components/ErrorBanner";
import { formatDateTime } from "../format";
import "../mobile-admin.css";

export default function MobileHealth() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await fetchMobileHealth());
    } catch (err) {
      setReport(null);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const ok = report?.status === "ok";

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">System health</h1>
          <p className="admin-page-sub">
            Reported by the Mobile backend itself. Failures are shown, not swallowed.
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
        report && (
          <>
            <div className={`admin-banner ${ok ? "success" : "error"}`} role="status">
              <strong>Mobile backend: {report.status}</strong>
              <div>
                {report.app} · {report.env} · checked {formatDateTime(report.checked_at)}
              </div>
            </div>

            <div className="admin-card">
              <h3 className="admin-section-title">Database</h3>
              <div className="mobile-fields">
                <div className="mobile-field">
                  <span className="mobile-field-label">Reachable</span>
                  <span className="mobile-field-value">
                    {report.database?.reachable ? "Yes" : "No"}
                  </span>
                </div>
                {report.database?.error && (
                  <div className="mobile-field">
                    <span className="mobile-field-label">Error</span>
                    <span className="mobile-field-value mobile-status bad">
                      {report.database.error}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="admin-card">
              <h3 className="admin-section-title">Review queue</h3>
              <div className="mobile-fields">
                <div className="mobile-field">
                  <span className="mobile-field-label">Enabled</span>
                  <span className="mobile-field-value">
                    {report.review_queue?.enabled ? "Yes" : "No"}
                  </span>
                </div>
                <div className="mobile-field">
                  <span className="mobile-field-label">Pending review</span>
                  <span className="mobile-field-value">
                    {report.review_queue?.pending_review ?? 0}
                  </span>
                </div>
              </div>
              {!report.review_queue?.enabled && (
                <p className="mobile-muted">
                  COUNSELLOR_AUTO_APPROVE is ON in this environment, so submitted
                  applications never enter the queue.
                </p>
              )}
            </div>
          </>
        )
      )}
    </div>
  );
}
