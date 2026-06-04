import { getAccessToken } from "../services/authApi";

/** Bearer token for authenticated API calls (in-memory JWT access token). */
export async function getAuthToken() {
  return getAccessToken();
}
