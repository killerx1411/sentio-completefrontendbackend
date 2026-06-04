import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useSession } from "../context/SessionContext";
import { getPrimaryRole, isSuperAdminUser } from "../utils/roleRoutes";
import {
  fetchUserById,
  fetchRoles,
  updateUser,
  deleteUser,
} from "../services/adminApi";
import "./admin.css";

const PERM_GROUPS = [
  {
    title: "User management",
    keys: ["users.view", "users.create", "users.edit", "users.delete"],
  },
  {
    title: "Roles & security",
    keys: ["roles.manage", "audit.view"],
  },
  {
    title: "Platform tools",
    keys: ["students.manage", "reports.export", "ai.use"],
  },
];

export default function UserDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user: sessionUser } = useSession();
  const isSuperAdmin = isSuperAdminUser(sessionUser);
  const isNormalAdmin = getPrimaryRole(sessionUser) === "Normal Admin";

  const [activeTab, setActiveTab] = useState("general");
  const [user, setUser] = useState(null);
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    phone: "",
    department: "",
    employee_id: "",
    status: "active",
    role_id: "",
    mfa_enabled: false,
  });
  const [passwordFields, setPasswordFields] = useState({
    newPassword: "",
    confirmPassword: "",
  });

  const assignableRoles = roles.filter(
    (r) => isSuperAdmin || r.name !== "Super Admin"
  );
  const userRoleName = user?.roles?.[0]?.name || "No role";
  const isTargetSuperAdmin = userRoleName === "Super Admin";
  const cannotModify = isTargetSuperAdmin && !isSuperAdmin;
  const protectedEmail = user?.email === "admin@sentiomind.com";

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [detail, roleList] = await Promise.all([
        fetchUserById(id),
        fetchRoles(),
      ]);
      setRoles(roleList || []);
      const u = detail.user;
      setUser(u);
      setPermissions(detail.permissions || []);
      setAuditLogs(detail.audit_logs || []);
      const currentRoleId =
        u.roles?.[0]?.id?.toString() ||
        assignableRoles[0]?.id?.toString() ||
        "";
      setFormData({
        full_name: u.full_name || "",
        email: u.email || "",
        phone: u.phone || "",
        department: u.department || "",
        employee_id: u.employee_id || "",
        status: u.status || "active",
        role_id: currentRoleId,
        mfa_enabled: !!u.mfa_enabled,
      });
    } catch (err) {
      setError(err.message || "Failed to load user");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (isNormalAdmin) {
      navigate("/admin/users", { replace: true });
    }
  }, [isNormalAdmin, navigate]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function buildPayload(extra = {}) {
    return {
      full_name: formData.full_name,
      email: formData.email,
      status: formData.status,
      role_id: formData.role_id ? parseInt(formData.role_id, 10) : null,
      phone: formData.phone || undefined,
      department: formData.department || undefined,
      employee_id: formData.employee_id || undefined,
      mfa_enabled: formData.mfa_enabled,
      ...extra,
    };
  }

  async function handleSave(e) {
    e.preventDefault();
    if (isNormalAdmin) return;
    setError("");
    setSuccess("");
    setSaveLoading(true);
    try {
      const updated = await updateUser(id, buildPayload());
      setUser((prev) => ({ ...prev, ...updated }));
      setSuccess("Profile updated successfully.");
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setSaveLoading(false);
    }
  }

  async function handleToggleMfa() {
    if (isNormalAdmin) return;
    const next = !formData.mfa_enabled;
    setFormData((prev) => ({ ...prev, mfa_enabled: next }));
    try {
      await updateUser(id, buildPayload({ mfa_enabled: next }));
      setSuccess(`MFA ${next ? "enabled" : "disabled"}.`);
    } catch (err) {
      setFormData((prev) => ({ ...prev, mfa_enabled: !next }));
      setError(err.message || "MFA update failed");
    }
  }

  async function handlePasswordReset(e) {
    e.preventDefault();
    if (isNormalAdmin) return;
    setError("");
    setSuccess("");
    if (passwordFields.newPassword !== passwordFields.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (passwordFields.newPassword.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setSaveLoading(true);
    try {
      await updateUser(id, buildPayload({ password: passwordFields.newPassword }));
      setSuccess("Password reset successfully.");
      setPasswordFields({ newPassword: "", confirmPassword: "" });
    } catch (err) {
      setError(err.message || "Password reset failed");
    } finally {
      setSaveLoading(false);
    }
  }

  async function handleDelete() {
    if (isNormalAdmin) return;
    if (!window.confirm(`Permanently delete ${formData.full_name}?`)) return;
    try {
      await deleteUser(id);
      navigate("/admin/users");
    } catch (err) {
      setError(err.message || "Delete failed");
    }
  }

  if (loading) {
    return <div className="admin-card admin-empty">Loading user…</div>;
  }

  return (
    <div>
      <Link to="/admin/users" className="admin-back-link">
        <ArrowLeft size={16} />
        Back to users
      </Link>

      <h1 className="admin-page-title">User administration</h1>
      <p className="admin-page-sub">Manage profile, roles, and security.</p>

      {error && <div className="admin-banner error">{error}</div>}
      {success && <div className="admin-banner success">{success}</div>}
      {cannotModify && (
        <div className="admin-banner error">
          This Super Admin account cannot be modified by a standard Admin.
        </div>
      )}

      <div className="admin-detail-layout">
        <div className="admin-card admin-profile-card">
          <div className="admin-avatar">
            {(formData.full_name || "U")
              .split(" ")
              .map((n) => n[0])
              .join("")
              .slice(0, 2)
              .toUpperCase()}
          </div>
          <h2>{formData.full_name}</h2>
          <p className="admin-page-sub">{formData.email}</p>
          <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center", marginTop: "0.75rem" }}>
            <span className="admin-badge role">{userRoleName}</span>
            <span className={`admin-badge ${formData.status === "active" ? "active" : "inactive"}`}>
              {formData.status}
            </span>
          </div>
          <p className="admin-meta" style={{ marginTop: "1rem" }}>
            Joined {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
            <br />
            Last login:{" "}
            {user?.last_login ? new Date(user.last_login).toLocaleString() : "Never"}
          </p>
        </div>

        <div>
          <div className="admin-tabs">
            {[
              ["general", "General"],
              ["rbac", "Roles & permissions"],
              ["security", "Security"],
              ["audit", "Audit logs"],
            ].map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                className={activeTab === tab ? "active" : ""}
                onClick={() => {
                  setActiveTab(tab);
                  setSuccess("");
                  setError("");
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="admin-card">
            {activeTab === "general" && (
              <form onSubmit={handleSave}>
                <div className="admin-form-grid">
                  <label>
                    Full name
                    <input name="full_name" value={formData.full_name} onChange={handleChange} required disabled={cannotModify} />
                  </label>
                  <label>
                    Email
                    <input type="email" name="email" value={formData.email} onChange={handleChange} required disabled={protectedEmail || cannotModify} />
                  </label>
                  <label>
                    Phone
                    <input name="phone" value={formData.phone} onChange={handleChange} disabled={cannotModify} />
                  </label>
                  <label>
                    Department
                    <input name="department" value={formData.department} onChange={handleChange} disabled={cannotModify} />
                  </label>
                  <label>
                    Employee ID
                    <input name="employee_id" value={formData.employee_id} onChange={handleChange} disabled={cannotModify} />
                  </label>
                  <label>
                    Status
                    <select name="status" value={formData.status} onChange={handleChange} disabled={protectedEmail || cannotModify}>
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </label>
                </div>
                <div className="admin-modal-actions">
                  <button type="submit" className="admin-btn primary" disabled={saveLoading || cannotModify}>
                    {saveLoading ? "Saving…" : "Save profile"}
                  </button>
                </div>
              </form>
            )}

            {activeTab === "rbac" && (
              <form onSubmit={handleSave}>
                <label style={{ display: "block", maxWidth: 320, marginBottom: "1.5rem" }}>
                  Role assignment
                  <select
                    name="role_id"
                    value={formData.role_id}
                    onChange={handleChange}
                    disabled={protectedEmail || cannotModify}
                    style={{ marginTop: "0.35rem" }}
                  >
                    {assignableRoles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </label>

                {PERM_GROUPS.map((group) => {
                  const active = permissions.filter((p) => group.keys.includes(p.name));
                  return (
                    <div key={group.title} className="admin-perm-group">
                      <h4>{group.title}</h4>
                      {active.length === 0 ? (
                        <p className="admin-page-sub">No permissions in this module.</p>
                      ) : (
                        <div className="admin-perm-tags">
                          {active.map((p) => (
                            <span key={p.id} className="admin-perm-tag">
                              {p.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}

                <div className="admin-modal-actions">
                  <button type="submit" className="admin-btn primary" disabled={saveLoading || protectedEmail || cannotModify}>
                    {saveLoading ? "Saving…" : "Save role"}
                  </button>
                </div>
              </form>
            )}

            {activeTab === "security" && (
              <div>
                <h4 className="admin-section-title">Multi-factor authentication</h4>
                <label style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.5rem" }}>
                  <input
                    type="checkbox"
                    checked={formData.mfa_enabled}
                    onChange={handleToggleMfa}
                    disabled={protectedEmail || cannotModify}
                  />
                  Require MFA on login
                </label>

                <h4 className="admin-section-title">Reset password</h4>
                <form onSubmit={handlePasswordReset} style={{ maxWidth: 360 }}>
                  <label>
                    New password
                    <input
                      type="password"
                      value={passwordFields.newPassword}
                      onChange={(e) =>
                        setPasswordFields((p) => ({ ...p, newPassword: e.target.value }))
                      }
                      disabled={cannotModify}
                      required
                    />
                  </label>
                  <label>
                    Confirm password
                    <input
                      type="password"
                      value={passwordFields.confirmPassword}
                      onChange={(e) =>
                        setPasswordFields((p) => ({ ...p, confirmPassword: e.target.value }))
                      }
                      disabled={cannotModify}
                      required
                    />
                  </label>
                  <button type="submit" className="admin-btn primary" disabled={saveLoading || cannotModify}>
                    Reset password
                  </button>
                </form>

                <hr style={{ margin: "2rem 0", border: "none", borderTop: "1px solid #d5e3e8" }} />
                <h4 className="admin-section-title" style={{ color: "#b91c1c" }}>
                  Danger zone
                </h4>
                <button
                  type="button"
                  className="admin-btn danger"
                  onClick={handleDelete}
                  disabled={protectedEmail || cannotModify}
                >
                  Delete profile
                </button>
              </div>
            )}

            {activeTab === "audit" && (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Action</th>
                      <th>Module</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="admin-empty-cell">
                          No audit events for this user.
                        </td>
                      </tr>
                    ) : (
                      auditLogs.map((log) => (
                        <tr key={log.id}>
                          <td>{new Date(log.created_at).toLocaleString()}</td>
                          <td>{log.action}</td>
                          <td>{log.module}</td>
                          <td>{log.description}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
