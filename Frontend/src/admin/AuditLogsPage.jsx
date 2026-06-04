import { useEffect, useState } from "react";
import { fetchAuditLogs } from "../services/adminApi";
import "./admin.css";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="admin-empty-cell">
                    No logs found.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id}>
                    <td>{new Date(log.created_at).toLocaleString()}</td>
                    <td style={{ fontWeight: 500, color: "#0f4c5c" }}>
                      {log.user_email || "System"}
                    </td>
                    <td>
                      <span className="admin-badge role">{log.action}</span>
                    </td>
                    <td>{log.module}</td>
                    <td>{log.description}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
