// SECURITY: access tokens are stored in memory only (not localStorage/sessionStorage). Refresh tokens should be in httpOnly cookies set by the server

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import {
  login as apiLogin,
  logout as apiLogout,
  refreshSession,
  fetchCurrentUser,
  verifyMfaLogin,
  setAccessToken,
  subscribeAccessToken,
  getApplication,
} from "../services/authApi";
import { getDashboardPathForUser } from "../utils/roleRoutes";

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);
  // Which registered application this session was opened for ("sentio-b2b" or
  // "sentio-mobile"). The auth backend binds the token and the refresh family
  // to it; we only mirror it so the console can render the right section.
  const [application, setApplicationState] = useState(getApplication());

  const loadUser = useCallback(async () => {
    const profile = await fetchCurrentUser();
    setUser(profile);
    return profile;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function restore() {
      try {
        await refreshSession();
        if (!cancelled) setApplicationState(getApplication());
        if (!cancelled) await loadUser();
      } catch {
        setAccessToken(null);
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setInitializing(false);
      }
    }

    restore();
    const unsub = subscribeAccessToken((token) => {
      if (!token) setUser(null);
    });

    return () => {
      cancelled = true;
      unsub();
    };
  }, [loadUser]);

  const loginWithCredentials = useCallback(
    async (email, password, remember = false) => {
      const result = await apiLogin(email, password, remember);
      if (result.mfa_required) {
        return {
          mfaRequired: true,
          pendingToken: result.pending_token,
        };
      }
      setApplicationState(getApplication());
      setUser(result.user);
      return {
        user: result.user,
        dashboardPath: getDashboardPathForUser(result.user),
      };
    },
    []
  );

  const completeMfaLogin = useCallback(async (pendingToken, totpCode) => {
    const result = await verifyMfaLogin(pendingToken, totpCode);
    setApplicationState(getApplication());
    setUser(result.user);
    return {
      user: result.user,
      dashboardPath: getDashboardPathForUser(result.user),
    };
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setApplicationState(getApplication());
    setUser(null);
  }, []);

  const isAuthenticated = !!user;

  return (
    <SessionContext.Provider
      value={{
        user,
        application,
        isAuthenticated,
        initializing,
        loginWithCredentials,
        completeMfaLogin,
        logout,
        refreshUser: loadUser,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return ctx;
}
