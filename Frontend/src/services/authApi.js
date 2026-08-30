import { AUTH_API_BASE } from "../config/env";
import { APP_B2B, APP_MOBILE, DEFAULT_APPLICATION } from "../constants/applications";



let accessToken = null;

// The application this session was opened for. The auth backend binds the
// access token AND the refresh-token family to it; rotation can never move a
// session across the boundary. Kept here so the console knows which product
// the signed-in operator is administering.
let currentApplication = DEFAULT_APPLICATION;

const tokenListeners = [];

let refreshPromise = null;



function getCsrfToken() {

  const match = document.cookie

    .split("; ")

    .find((row) => row.startsWith("sentio_csrf="));

  if (!match) return "";

  const value = match.slice("sentio_csrf=".length);

  try {

    return decodeURIComponent(value);

  } catch {

    return value;

  }

}



export function setAccessToken(token) {

  accessToken = token || null;

  tokenListeners.forEach((fn) => fn(accessToken));

}



export function getAccessToken() {

  return accessToken;

}





export function getApplication() {
  return currentApplication;
}

function setApplication(application) {
  if (application) currentApplication = application;
}

export function subscribeAccessToken(listener) {

  tokenListeners.push(listener);

  return () => {

    const idx = tokenListeners.indexOf(listener);

    if (idx >= 0) tokenListeners.splice(idx, 1);

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



export async function authFetch(path, options = {}, allowRetry = true) {

  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && options.body) {

    headers.set("Content-Type", "application/json");

  }

  if (accessToken && !headers.has("Authorization")) {

    headers.set("Authorization", `Bearer ${accessToken}`);

  }

  const csrf = getCsrfToken();

  if (csrf && !headers.has("X-CSRF-Token")) {

    headers.set("X-CSRF-Token", csrf);

  }



  const response = await fetch(buildUrl(path), {

    ...options,

    headers,

    credentials: "include",

  });



  // The access token lives ~15 min in memory. On expiry, rotate it via the
  // refresh cookie and replay the call once instead of surfacing a 401.

  // Never re-enter on the refresh call itself: refreshSession() is single-flight
  // and awaiting its own in-flight promise would deadlock.

  const retryable =
    headers.has("Authorization") && !path.startsWith("/api/auth/refresh");

  if (response.status === 401 && allowRetry && retryable) {

    try {

      await refreshSession();

    } catch {

      setAccessToken(null);

      return parseJson(response);

    }

    return authFetch(path, options, false);

  }



  return parseJson(response);

}



/**
 * Log in against the ONE authentication authority.
 *
 * The authority mints a token bound to exactly ONE application, and a role is
 * only entitled to the applications it declares: B2B roles -> "sentio-b2b",
 * Mobile Admin roles -> "sentio-mobile". Neither can log into the other's
 * application (403 from the backend).
 *
 * There is one login system and one endpoint. Because the caller cannot know
 * which application an email belongs to before authenticating, we ask for the
 * default (B2B) and, only if the authority refuses that application, ask again
 * for "sentio-mobile". The account-state refusals (pending / rejected /
 * suspended / disabled / no role) are checked BEFORE entitlement in the
 * backend, so a retry surfaces exactly the same message — the negotiation can
 * only ever turn an entitlement 403 into a successful Mobile Admin login.
 *
 * Pass `application` explicitly to skip the negotiation.
 */
export async function login(email, password, remember = false, application = null) {
  const attempt = async (app) => {
    const data = await authFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, remember, application: app }),
    });
    setApplication(data.data?.application || app);
    if (data.data?.access_token) {
      setAccessToken(data.data.access_token);
    }
    return data.data;
  };

  if (application) {
    return attempt(application);
  }

  try {
    return await attempt(APP_B2B);
  } catch (err) {
    if (err?.status !== 403) throw err;
    return attempt(APP_MOBILE);
  }
}



export async function signup(payload) {

  const data = await authFetch("/api/auth/signup", {

    method: "POST",

    body: JSON.stringify(payload),

  });

  return data;

}



export async function refreshSession() {

  if (refreshPromise) {

    return refreshPromise;

  }

  refreshPromise = (async () => {

    try {

      const data = await authFetch("/api/auth/refresh", { method: "POST", body: "{}" });

      setApplication(data.data?.application);

      if (data.data?.access_token) {

        setAccessToken(data.data.access_token);

      }

      return data.data;

    } finally {

      refreshPromise = null;

    }

  })();

  return refreshPromise;

}



export async function verifyMfaLogin(pendingToken, totpCode) {

  const res = await fetch(buildUrl("/api/auth/mfa/verify"), {

    method: "POST",

    headers: { "Content-Type": "application/json" },

    credentials: "include",

    body: JSON.stringify({ pending_token: pendingToken, totp_code: totpCode }),

  });

  const data = await parseJson(res);

  setApplication(data.data?.application);

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

    currentApplication = DEFAULT_APPLICATION;

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



export async function requestPasswordReset(email) {

  const res = await fetch(buildUrl("/api/auth/forgot-password"), {

    method: "POST",

    headers: { "Content-Type": "application/json" },

    body: JSON.stringify({ email }),

    credentials: "include",

  });

  if (res.status >= 500) {

    throw new Error("Server error");

  }

  return res.json().catch(() => ({}));

}



export async function resetPassword(token, newPassword) {

  const res = await fetch(buildUrl("/api/auth/reset-password"), {

    method: "POST",

    headers: { "Content-Type": "application/json" },

    body: JSON.stringify({ token, new_password: newPassword }),

    credentials: "include",

  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {

    throw new Error(data.message || data.error || "Reset failed.");

  }

  return data;

}

