/**

 * Client environment (CRA: REACT_APP_* only).

 */

// SECURITY: only REACT_APP_ variables are safe here — they are bundled into the client. Never put secrets here.



function env(key, fallback = "") {

  const value = process.env[key];

  return (typeof value === "string" ? value.trim() : "") || fallback;

}



/** Main SentioMind analytics API */

export const API_BASE = env("REACT_APP_API_URL");



/** JWT auth service (Flask / PostgreSQL) */

// Empty string = same-origin (production behind nginx /api/ proxy).
// Local dev: set REACT_APP_AUTH_API_URL=http://localhost:5000
const authApiUrl = env("REACT_APP_AUTH_API_URL", "");
export const AUTH_API_BASE = authApiUrl;



/** Sentio Mobile backend (FastAPI). Serves the Mobile Admin API at /api/admin
 *  and accepts ONLY access tokens minted for application "sentio-mobile".
 *  Empty string = same-origin (production behind the same nginx). */
const mobileAdminApiUrl = env("REACT_APP_MOBILE_ADMIN_API_URL", "");
export const MOBILE_ADMIN_API_BASE = mobileAdminApiUrl;



export function assertRequiredEnv() {
  // Empty AUTH_API_BASE is valid in production (same-origin /api/ via nginx).
}



assertRequiredEnv();

