/**
 * Client environment (CRA: REACT_APP_* only).
 * Never put server secrets here.
 */

function env(key, fallback = "") {
  const value = process.env[key];
  return (typeof value === "string" ? value.trim() : "") || fallback;
}

/** Main SentioMind analytics API */
export const API_BASE = env("REACT_APP_API_URL");

/** JWT auth service (Flask / PostgreSQL) */
export const AUTH_API_BASE = env("REACT_APP_AUTH_API_URL", "http://localhost:5000");

export function assertRequiredEnv() {
  const missing = [];
  if (!AUTH_API_BASE) missing.push("REACT_APP_AUTH_API_URL");
  if (missing.length && process.env.NODE_ENV === "production") {
    console.error(
      `[SentioMind] Missing: ${missing.join(", ")}. Copy Frontend/.env.example to Frontend/.env`
    );
  }
}

assertRequiredEnv();
