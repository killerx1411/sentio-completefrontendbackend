import { Fragment, useEffect, useState } from "react";
import { fetchAuditLogs } from "../services/adminApi";
import "./admin.css";

function formatDetails(details) {
  if (!details) return null;
  if (typeof details === "string") {
    try {
      return JSON.parse(details);
    } catch {
      return null;
    }
  }
  return details;
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    fetchAuditLogs()
      .then(setLogs)
      .catch((err) => setError(err.message || "Failed to load audit logs"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="admin-page-title">Audit logs</h1>
      <p className="admin-page-sub">Recent security and system activity (last 100).</p>

      {error && <div className="admin-banner error">{error}</div>}

      <div className="admin-card admin-table-wrap">
        {loading ? (
          <p className="admin-empty">Loading…</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>Action</th>
                <th>Module</th>
                <th>Description</th>
                <th>Severity</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="admin-empty-cell">
                    No logs found.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const details = formatDetails(log.details);
                  const isExpanded = expandedId === log.id;
                  return (
                    <Fragment key={log.id}>
                      <tr>
                        <td>{new Date(log.created_at).toLocaleString()}</td>
                        <td className="admin-audit-user">
                          {log.user_email || "System"}
                        </td>
                        <td>
                          <span className="admin-badge role">{log.action}</span>
                        </td>
                        <td>{log.module}</td>
                        <td>{log.description}</td>
                        <td>{log.severity || "INFO"}</td>
                        <td>
                          {details && (
                            <button
                              type="button"
                              className="admin-btn"
                              onClick={() =>
                                setExpandedId(isExpanded ? null : log.id)
                              }
                            >
                              {isExpanded ? "Hide" : "Details"}
                            </button>
                          )}
                        </td>
                      </tr>
                      {isExpanded && details && (
                        <tr key={`${log.id}-details`}>
                          <td colSpan={7} className="admin-audit-details">
                            {details.accepted_at && (
                              <div>
                                <strong>Accepted at:</strong> {details.accepted_at}
                              </div>
                            )}
                            {details.terms_version && (
                              <div>
                                <strong>Terms version:</strong> {details.terms_version}
                              </div>
                            )}
                            {details.registration_flow != null && (
                              <div>
                                <strong>Registration flow:</strong>{" "}
                                {details.registration_flow ? "Yes" : "No"}
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
