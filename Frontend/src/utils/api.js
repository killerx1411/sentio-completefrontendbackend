import { API_BASE } from "../config/env";
import { getAuthToken } from "./authToken";

function buildUrl(path) {
  if (!API_BASE) {
    throw new Error("REACT_APP_API_URL is not configured");
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const base = API_BASE.replace(/\/$/, "");
  const route = path.startsWith("/") ? path : `/${path}`;
  return `${base}${route}`;
}

/**
 * Authenticated fetch to the SentioMind API.
 * Attaches Bearer token when a Cognito or OIDC session exists.
 */
export async function apiFetch(path, options = {}) {
  const token = await getAuthToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(buildUrl(path), {
    ...options,
    headers,
  });

  return response;
}
