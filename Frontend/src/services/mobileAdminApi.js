/**
 * Sentio Mobile Admin API client.
 *
 * Talks to the Mobile backend (FastAPI) at `/api/admin`. That backend is a
 * resource server for the ONE authentication authority: it accepts only access
 * tokens minted for application "sentio-mobile" and re-checks every permission
 * server-side. This module therefore performs no authentication of its own —
 * it forwards the in-memory access token the session already holds.
 *
 * The B2B frontend never talks to PostgreSQL. Every value on the Mobile pages
 * comes from these endpoints.
 */

import { MOBILE_ADMIN_API_BASE } from "../config/env";
import { getAccessToken, refreshSession, setAccessToken } from "./authApi";

const PREFIX = "/api/admin";

function buildUrl(path, params) {
  const base = MOBILE_ADMIN_API_BASE.replace(/\/$/, "");
  const route = path.startsWith("/") ? path : `/${path}`;
  const url = `${base}${PREFIX}${route}`;
  const query = toQueryString(params);
  return query ? `${url}?${query}` : url;
}

/** Drops null/undefined/"" and expands arrays into repeated keys (FastAPI's
 *  `Query(default=None)` list style, used by the expert status filter). */
function toQueryString(params) {
  if (!params) return "";
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    if (Array.isArray(value)) {
      value.forEach((v) => {
        if (v !== null && v !== undefined && v !== "") search.append(key, v);
      });
      return;
    }
    search.append(key, value);
  });
  return search.toString();
}

export class MobileAdminError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = "MobileAdminError";
    this.status = status;
    this.code = code;
    this.isForbidden = status === 403;
    this.isUnauthorized = status === 401;
  }
}

function messageFrom(payload, response) {
  // AppException -> {"error": {"code", "message"}}
  const err = payload?.error;
  if (err && typeof err === "object") {
    return [err.message || response.statusText, err.code];
  }
  // Bare HTTPException / FastAPI validation -> {"detail": ... }
  const detail = payload?.detail;
  if (typeof detail === "string") return [detail, undefined];
  if (Array.isArray(detail) && detail.length) {
    return [detail.map((d) => d.msg || "Invalid input").join("; "), "validation_error"];
  }
  if (detail && typeof detail === "object") {
    return [detail.message || response.statusText, detail.code];
  }
  return [response.statusText || "Request failed", undefined];
}

async function parse(response) {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const [message, code] = messageFrom(payload, response);
    throw new MobileAdminError(message, response.status, code);
  }
  return payload;
}

async function request(path, { params, method = "GET", body } = {}, allowRetry = true) {
  const token = getAccessToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (body !== undefined) headers.set("Content-Type", "application/json");

  const response = await fetch(buildUrl(path, params), {
    method,
    headers,
    // No cookies cross this boundary: the Mobile backend authorizes from the
    // bearer token only. The refresh cookie stays with the auth authority.
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  // The access token lives ~15 min in memory. Rotate it through the authority
  // and replay once, exactly as authFetch does for the B2B API.
  if (response.status === 401 && allowRetry && token) {
    try {
      await refreshSession();
    } catch {
      setAccessToken(null);
      return parse(response);
    }
    return request(path, { params, method, body }, false);
  }

  return parse(response);
}

/* ── Identity ───────────────────────────────────────────────────────────── */

/** Who the Mobile backend thinks we are, and what it will let us do.
 *  `capabilities` is rendered from; the backend re-checks each on the action. */
export function fetchMobileIdentity() {
  return request("/me");
}

/* ── Experts ────────────────────────────────────────────────────────────── */

export function fetchExperts(params) {
  return request("/experts", { params });
}

export function fetchExpertStats() {
  return request("/experts/stats");
}

export function fetchExpert(userId) {
  return request(`/experts/${userId}`);
}

export function setExpertStatus(userId, status, reason) {
  return request(`/experts/${userId}/status`, {
    method: "POST",
    body: { status, reason: reason || null },
  });
}

export function setDocumentVerdict(userId, status, remarks) {
  return request(`/experts/${userId}/documents/status`, {
    method: "POST",
    body: { status, remarks: remarks || null },
  });
}

/* ── Users ──────────────────────────────────────────────────────────────── */

export function fetchMobileUsers(params) {
  return request("/users", { params });
}

export function fetchMobileUser(userId) {
  return request(`/users/${userId}`);
}

export function setUserActive(userId, isActive, reason) {
  return request(`/users/${userId}/active`, {
    method: "POST",
    body: { is_active: isActive, reason: reason || null },
  });
}

/* ── Operational read surfaces ──────────────────────────────────────────── */

export function fetchSessions(params) {
  return request("/sessions", { params });
}

export function fetchPayments(params) {
  return request("/payments", { params });
}

export function fetchSubscriptions(params) {
  return request("/subscriptions", { params });
}

export function fetchRiskFlags(params) {
  return request("/risk/flags", { params });
}

export function fetchRiskThresholds() {
  return request("/risk/thresholds");
}

export function fetchExercises(params) {
  return request("/exercises", { params });
}

export function fetchNutrition(params) {
  return request("/content/nutrition", { params });
}

export function fetchInterventionRules(params) {
  return request("/content/intervention-rules", { params });
}

/* ── Audit, admins, settings, health, dashboard ─────────────────────────── */

export function fetchMobileAudit(params) {
  return request("/audit", { params });
}

export function fetchMobileEvents(params) {
  return request("/events", { params });
}

export function fetchMobileAdmins() {
  return request("/admins");
}

export function fetchMobileSettings() {
  return request("/settings");
}

export function fetchMobileHealth() {
  return request("/health");
}

export function fetchMobileDashboard() {
  return request("/dashboard");
}
