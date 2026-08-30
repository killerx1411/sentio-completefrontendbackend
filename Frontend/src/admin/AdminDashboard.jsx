import { useEffect, useState } from "react";
import {
  approveUser,
  fetchPendingUsers,
  rejectPendingUser,
} from "../services/authApi";
import { STAKEHOLDER_ROLES } from "../utils/roleRoutes";
import "./admin.css";

export default function AdminDashboard() {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedRoles, setSelectedRoles] = useState({});
  const [busyId, setBusyId] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchPendingUsers();
      const list = data || [];
      setPending(list);
      const defaults = {};
      list.forEach((u) => {
        defaults[u.id] =
          u.requested_role && STAKEHOLDER_ROLES.includes(u.requested_role)
            ? u.requested_role
            : STAKEHOLDER_ROLES[0];
      });
      setSelectedRoles(defaults);
    } catch (err) {
      setError(err.message || "Failed to load pending signups");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleApprove(userId) {
    const role = selectedRoles[userId];
    if (!role) {
      setError("Select a role before approving.");
      return;
    }
    if (!STAKEHOLDER_ROLES.includes(role)) {
      setError("Invalid role selected.");
      return;
    }
    setBusyId(userId);
    setError("");
    setSuccess("");
    try {
      const result = await approveUser(userId, role);
      setSuccess(result.message || `Approved as ${role}. Credentials emailed.`);
      await load();
    } catch (err) {
      setError(err.message || "Approval failed");
    } finally {
      setBusyId(null);
    }
  }

  function requestReject(user) {
    setRejectTarget(user);
  }

  async function handleReject(userId) {
    setBusyId(userId);
    setError("");
    setSuccess("");
    try {
      const result = await rejectPendingUser(userId);
      setSuccess(result.message || "Signup rejected.");
      await load();
    } catch (err) {
      setError(err.message || "Rejection failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <h1 className="admin-page-title">Pending signups</h1>
      <p className="admin-page-sub">
        Review new registrations, choose a stakeholder role, then approve or reject.
        Approved users receive login credentials by email.
      </p>

      {success && <div className="admin-banner success">{success}</div>}
      {error && <div className="admin-banner error">{error}</div>}

      {loading ? (
        <div className="admin-card admin-empty">Loading…</div>
      ) : pending.length === 0 ? (
        <div className="admin-card admin-empty">No pending signups.</div>
      ) : (
        pending.map((u) => (
          <div key={u.id} className="admin-card">
            <h3>{u.full_name}</h3>
            <div className="admin-meta">
              <div>
                <strong>Email:</strong> {u.email}
              </div>
              {u.phone && (
                <div>
                  <strong>Phone:</strong> {u.phone}
                </div>
              )}
              {u.organization && (
                <div>
                  <strong>Organization:</strong> {u.organization}
                </div>
              )}
              {u.signup_message && (
                <div>
                  <strong>Message:</strong> {u.signup_message}
                </div>
              )}
              {u.requested_role && (
                <div>
                  <strong>Requested role:</strong> {u.requested_role}
                </div>
              )}
              <div>
                <strong>Submitted:</strong>{" "}
                {u.created_at ? new Date(u.created_at).toLocaleString() : "—"}
              </div>
            </div>

            <div className="admin-approve-row">
              <label className="admin-role-select-label">
                Assign role
                <select
                  className="admin-role-select"
                  value={selectedRoles[u.id] || STAKEHOLDER_ROLES[0]}
                  disabled={busyId === u.id}
                  onChange={(e) =>
                    setSelectedRoles((prev) => ({
                      ...prev,
                      [u.id]: e.target.value,
                    }))
                  }
                >
                  {STAKEHOLDER_ROLES.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </select>
              </label>
              <div className="admin-approve-actions">
                <button
                  type="button"
                  className="admin-btn primary"
                  disabled={busyId === u.id}
                  onClick={() => handleApprove(u.id)}
                >
                  {busyId === u.id ? "Processing…" : "Approve"}
                </button>
                <button
                  type="button"
                  className="admin-btn danger-outline"
                  disabled={busyId === u.id}
                  onClick={() => requestReject(u)}
                >
                  Reject
                </button>
              </div>
            </div>
          </div>
        ))
      )}

      {rejectTarget && (
        <div className="admin-modal-overlay">
          <div className="admin-card admin-modal">
            <h3 className="admin-section-title">Reject signup</h3>
            <p className="admin-page-sub">
              Reject the signup request for <strong>{rejectTarget.full_name}</strong> (
              {rejectTarget.email})?
            </p>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="admin-btn"
                onClick={() => setRejectTarget(null)}
                disabled={busyId === rejectTarget.id}
              >
                Cancel
              </button>
              <button
                type="button"
                className="admin-btn danger"
                onClick={async () => {
                  const id = rejectTarget.id;
                  setRejectTarget(null);
                  await handleReject(id);
                }}
                disabled={busyId === rejectTarget.id}
              >
                {busyId === rejectTarget.id ? "Processing…" : "Reject signup"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
