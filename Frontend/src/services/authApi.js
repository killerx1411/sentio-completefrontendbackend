import { AUTH_API_BASE } from "../config/env";

let accessToken = null;
let onTokenChange = null;

export function setAccessToken(token) {
  accessToken = token || null;
  if (onTokenChange) onTokenChange(accessToken);
}

export function getAccessToken() {
  return accessToken;
}

export function subscribeAccessToken(listener) {
  onTokenChange = listener;
  return () => {
    if (onTokenChange === listener) onTokenChange = null;
  };
}

function buildUrl(path) {
  const base = AUTH_API_BASE.replace(/\/$/, "");
  const route = path.startsWith("/") ? path : `/${path}`;
  return `${base}${route}`;
}

async function parseJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = new Error(data.message || response.statusText || "Request failed");
    err.status = response.status;
    err.data = data;
    throw err;
  }
  return data;
}

export async function authFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(buildUrl(path), {
    ...options,
    headers,
    credentials: "include",
  });

  return parseJson(response);
}

export async function login(email, password, remember = false) {
  const data = await authFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password, remember }),
  });
  if (data.data?.access_token) {
    setAccessToken(data.data.access_token);
  }
  return data.data;
}

export async function signup(payload) {
  const data = await authFetch("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return data;
}

export async function refreshSession() {
  const data = await authFetch("/api/auth/refresh", { method: "POST", body: "{}" });
  if (data.data?.access_token) {
    setAccessToken(data.data.access_token);
  }
  return data.data;
}

export async function logout() {
  try {
    await authFetch("/api/auth/logout", { method: "POST", body: "{}" });
  } finally {
    setAccessToken(null);
  }
}

export async function fetchCurrentUser() {
  const data = await authFetch("/api/auth/me");
  return data.data;
}

export async function fetchPendingUsers() {
  const data = await authFetch("/api/admin/pending-users");
  return data.data;
}

export async function approveUser(userId, role) {
  return authFetch(`/api/admin/users/${userId}/approve`, {
    method: "POST",
    body: JSON.stringify({ role }),
  });
}

export async function rejectPendingUser(userId, reason) {
  return authFetch(`/api/admin/users/${userId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || undefined }),
  });
}
