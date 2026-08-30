/**
 * The Mobile Admin section's authorization view.
 *
 * `GET /api/admin/me` on the Mobile backend is the ONE source of what this
 * operator may do: it derives a capability map from the `mobile.*` permissions
 * on the access token the central authority minted. We render from that.
 *
 * SECURITY: this is presentation only. Every capability is re-checked by the
 * Mobile backend on the actual request, and a 403 from there is surfaced —
 * hiding a control is never the control.
 *
 * The provider wraps the whole /admin shell so the sidebar can filter the
 * Mobile section by permission, but it only calls the Mobile backend when the
 * signed-in user is actually a Mobile Admin. A B2B admin's session holds a
 * "sentio-b2b" token, which that backend would (correctly) reject.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useSession } from "../context/SessionContext";
import { isMobileAdminUser, ROLES } from "../utils/roleRoutes";
import { fetchMobileIdentity } from "../services/mobileAdminApi";

const MobileAdminContext = createContext(null);

export function MobileAdminProvider({ children }) {
  const { user } = useSession();
  const enabled = isMobileAdminUser(user);

  const [identity, setIdentity] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setIdentity(null);
      setError(null);
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchMobileIdentity()
      .then((data) => {
        if (!cancelled) setIdentity(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setIdentity(null);
          setError(err);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, reloadKey]);

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  /** A capability the Mobile backend advertised (e.g. "experts.approve"). */
  const can = useCallback(
    (capability) => Boolean(identity?.capabilities?.[capability]),
    [identity]
  );

  /** A raw `mobile.*` permission carried by the access token. */
  const has = useCallback(
    (permission) => Boolean(identity?.permissions?.includes(permission)),
    [identity]
  );

  return (
    <MobileAdminContext.Provider
      value={{
        enabled,
        identity,
        loading,
        error,
        reload,
        can,
        has,
        isSuperAdmin: identity?.role === ROLES.MOBILE_SUPER_ADMIN,
      }}
    >
      {children}
    </MobileAdminContext.Provider>
  );
}

export function useMobileAdmin() {
  const ctx = useContext(MobileAdminContext);
  if (!ctx) {
    throw new Error("useMobileAdmin must be used within MobileAdminProvider");
  }
  return ctx;
}
