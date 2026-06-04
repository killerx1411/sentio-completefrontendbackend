import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Edit2, Trash2, Shield } from "lucide-react";
import { useSession } from "../context/SessionContext";
import { getPrimaryRole, isSuperAdminUser } from "../utils/roleRoutes";
import {
  fetchUsers,
  fetchRoles,
  createUser,
  deleteUser,
} from "../services/adminApi";
import "./admin.css";

export default function UserManagement() {
  const { user: sessionUser } = useSession();
  const isSuperAdmin = isSuperAdminUser(sessionUser);
  const isNormalAdmin = getPrimaryRole(sessionUser) === "Normal Admin";
  const [activeTab, setActiveTab] = useState("users");
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalError, setModalError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "",
    status: "active",
    role_id: "",
    phone: "",
    department: "",
    employee_id: "",
  });

  const assignableRoles = roles.filter(
    (r) => isSuperAdmin || r.name !== "Super Admin"
  );

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [userList, roleList] = await Promise.all([fetchUsers(), fetchRoles()]);
      setUsers(userList || []);
      setRoles(roleList || []);
    } catch (err) {
      setError(err.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function openAddModal() {
    if (isNormalAdmin) return;
    setFormData({
      full_name: "",
      email: "",
      password: "",
      status: "active",
      role_id: assignableRoles[0]?.id?.toString() || "",
      phone: "",
      department: "",
      employee_id: "",
    });
    setModalError("");
    setIsAddModalOpen(true);
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setModalError("");
    setActionLoading(true);
    try {
      await createUser({
        full_name: formData.full_name,
        email: formData.email,
        password: formData.password,
        status: formData.status,
        role_id: formData.role_id ? parseInt(formData.role_id, 10) : null,
        phone: formData.phone || undefined,
        department: formData.department || undefined,
        employee_id: formData.employee_id || undefined,
      });
      setIsAddModalOpen(false);
      await load();
    } catch (err) {
      setModalError(err.message || "Failed to create user");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDelete(target) {
    if (isNormalAdmin) return;
    const roleName = target.roles?.[0]?.name;
    if (target.email === sessionUser?.email) return;
    if (roleName === "Super Admin" && !isSuperAdmin) return;
    if (!window.confirm(`Delete user ${target.full_name}?`)) return;

    setError("");
    try {
      await deleteUser(target.id);
      await load();
    } catch (err) {
      setError(err.message || "Failed to delete user");
    }
  }

  return (
    <div>
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">User management</h1>
          <p className="admin-page-sub">
            Manage accounts, statuses, and platform roles.
          </p>
        </div>
        {activeTab === "users" && !isNormalAdmin && (
          <button type="button" className="admin-btn primary" onClick={openAddModal}>
            <Plus size={16} />
            Add user
          </button>
        )}
      </div>

      <div className="admin-tabs">
        <button
          type="button"
          className={activeTab === "users" ? "active" : ""}
          onClick={() => setActiveTab("users")}
        >
          Users list
        </button>
        {isSuperAdmin && (
          <button
            type="button"
            className={activeTab === "roles" ? "active" : ""}
            onClick={() => setActiveTab("roles")}
          >
            <Shield size={16} style={{ verticalAlign: "middle", marginRight: 4 }} />
            Available roles
          </button>
        )}
      </div>

      {error && <div className="admin-banner error">{error}</div>}

      {loading ? (
        <div className="admin-card admin-empty">Loading…</div>
      ) : activeTab === "users" ? (
        <div className="admin-card admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Department</th>
                <th>Employee ID</th>
                <th>Role</th>
                <th>Status</th>
                {!isNormalAdmin && <th style={{ textAlign: "right" }}>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan={isNormalAdmin ? 6 : 7} className="admin-empty-cell">
                    No users found.
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const userRole = u.roles?.[0]?.name || "No role";
                  const isTargetSuperAdmin = userRole === "Super Admin";
                  const canDelete =
                    u.email !== sessionUser?.email &&
                    !(isTargetSuperAdmin && !isSuperAdmin);

                  return (
                    <tr key={u.id}>
                      <td>
                        {isNormalAdmin ? (
                          u.full_name
                        ) : (
                          <Link to={`/admin/users/${u.id}`} className="admin-link">
                            {u.full_name}
                          </Link>
                        )}
                      </td>
                      <td>{u.email}</td>
                      <td>{u.department || "—"}</td>
                      <td>{u.employee_id || "—"}</td>
                      <td>
                        <span className="admin-badge role">{userRole}</span>
                      </td>
                      <td>
                        <span
                          className={`admin-badge ${u.status === "active" ? "active" : "inactive"}`}
                        >
                          {u.status}
                        </span>
                      </td>
                      {!isNormalAdmin && (
                        <td style={{ textAlign: "right" }}>
                          <Link
                            to={`/admin/users/${u.id}`}
                            className="admin-icon-btn"
                            title="Edit user"
                          >
                            <Edit2 size={16} />
                          </Link>
                          <button
                            type="button"
                            className="admin-icon-btn danger"
                            disabled={!canDelete}
                            onClick={() => handleDelete(u)}
                            title="Delete user"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="admin-card admin-table-wrap">
          <h3 className="admin-section-title">System roles</h3>
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Role</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td style={{ fontWeight: 600, color: "#0f4c5c" }}>{r.name}</td>
                  <td>{r.description || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isAddModalOpen && !isNormalAdmin && (
        <div className="admin-modal-overlay">
          <div className="admin-card admin-modal">
            <h3 className="admin-section-title">Add new user</h3>
            {modalError && <div className="admin-banner error">{modalError}</div>}
            <form onSubmit={handleCreate}>
              <div className="admin-form-grid">
                <label>
                  Full name
                  <input name="full_name" value={formData.full_name} onChange={handleChange} required />
                </label>
                <label>
                  Email
                  <input type="email" name="email" value={formData.email} onChange={handleChange} required />
                </label>
                <label>
                  Password
                  <input type="password" name="password" value={formData.password} onChange={handleChange} required minLength={6} />
                </label>
                <label>
                  Phone
                  <input name="phone" value={formData.phone} onChange={handleChange} />
                </label>
                <label>
                  Department
                  <input name="department" value={formData.department} onChange={handleChange} />
                </label>
                <label>
                  Employee ID
                  <input name="employee_id" value={formData.employee_id} onChange={handleChange} />
                </label>
                <label>
                  Status
                  <select name="status" value={formData.status} onChange={handleChange}>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </label>
                <label>
                  System role
                  <select name="role_id" value={formData.role_id} onChange={handleChange}>
                    {assignableRoles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="admin-modal-actions">
                <button type="button" className="admin-btn" onClick={() => setIsAddModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="admin-btn primary" disabled={actionLoading}>
                  {actionLoading ? "Saving…" : "Create user"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
