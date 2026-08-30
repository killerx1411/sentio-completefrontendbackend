import { useCallback, useEffect, useState } from "react";
import { fetchMobileAdmins } from "../../services/mobileAdminApi";
import ErrorBanner from "../components/ErrorBanner";
import { DASH } from "../format";
import { roleLabel } from "../../utils/roleRoutes";
import "../mobile-admin.css";

export default function MobileAdmins() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchMobileAdmins());
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Mobile admins</h1>
          <p className="admin-page-sub">
            Mobile Admin accounts live in the central authentication authority, not in
            the Mobile database.
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
            <div className="admin-card">
              <h3 className="admin-section-title">How these accounts are granted</h3>
              <p style={{ color: "#64748b", marginTop: 0 }}>{data.grant_process}</p>
              <div className="mobile-fields">
                <div className="mobile-field">
                  <span className="mobile-field-label">Authentication authority</span>
                  <span className="mobile-field-value">
                    {data.authority_base_url || DASH}
                  </span>
                </div>
                <div className="mobile-field">
                  <span className="mobile-field-label">Application</span>
                  <span className="mobile-field-value">{data.application}</span>
                </div>
                <div className="mobile-field">
                  <span className="mobile-field-label">Roles</span>
                  <span className="mobile-field-value">
                    {(data.roles || []).map((role) => (
                      <span key={role} className="admin-badge role" style={{ marginRight: 6 }}>
                        {roleLabel(role)}
                      </span>
                    ))}
                  </span>
                </div>
              </div>
            </div>

            <div className="admin-card">
              <h3 className="admin-section-title">Your Mobile Admin identity</h3>
              <div className="mobile-fields">
                <div className="mobile-field">
                  <span className="mobile-field-label">Email</span>
                  <span className="mobile-field-value">
                    {data.current_admin?.email || DASH}
                  </span>
                </div>
                <div className="mobile-field">
                  <span className="mobile-field-label">Role</span>
                  <span className="mobile-field-value">
                    {roleLabel(data.current_admin?.role)}
                  </span>
                </div>
                <div className="mobile-field">
                  <span className="mobile-field-label">Subject</span>
                  <span className="mobile-field-value">
                    <code className="mobile-code">{data.current_admin?.subject}</code>
                  </span>
                </div>
              </div>

              <div style={{ marginTop: "1rem" }}>
                <span className="mobile-field-label">Permissions</span>
                <div className="admin-perm-tags">
                  {(data.current_admin?.permissions || []).map((permission) => (
                    <span key={permission} className="admin-perm-tag">
                      {permission}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </>
        )
      )}
    </div>
  );
}
