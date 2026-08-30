/**
 * Registered consumer applications of the ONE authentication authority.
 *
 * Mirror of Backend/auth/constants/applications.py. An application is a token
 * audience boundary: login mints one access token bound to exactly one of
 * these, and a resource server only accepts tokens minted for itself.
 *
 * This file adds no authentication of its own — it only names the boundary the
 * auth backend already enforces.
 */

export const APP_B2B = "sentio-b2b";
export const APP_MOBILE = "sentio-mobile";

export const APPLICATIONS = {
  [APP_B2B]: { label: "Sentio B2B / Stakeholder platform" },
  [APP_MOBILE]: { label: "Sentio Mobile Admin" },
};

export const DEFAULT_APPLICATION = APP_B2B;

export function applicationLabel(application) {
  return APPLICATIONS[application]?.label || application || "";
}
