import { authFetch } from "./authApi";

export async function fetchDashboardStats() {
  const data = await authFetch("/api/dashboard/stats");
  return data.data;
}

export async function fetchUsers() {
  const data = await authFetch("/api/users");
  return data.data;
}

export async function fetchUserById(userId) {
  const data = await authFetch(`/api/users/${userId}`);
  return data.data;
}

export async function createUser(payload) {
  const data = await authFetch("/api/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data.data;
}

export async function updateUser(userId, payload) {
  const data = await authFetch(`/api/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  return data.data;
}

export async function deleteUser(userId) {
  return authFetch(`/api/users/${userId}`, { method: "DELETE" });
}

export async function fetchRoles() {
  const data = await authFetch("/api/roles");
  return data.data;
}

export async function fetchAuditLogs() {
  const data = await authFetch("/api/audit-logs");
  return data.data;
}
