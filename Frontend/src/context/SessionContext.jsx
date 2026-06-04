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
  setAccessToken,
  subscribeAccessToken,
} from "../services/authApi";
import { getDashboardPathForUser } from "../utils/roleRoutes";

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);

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
      setUser(result.user);
      return {
        user: result.user,
        dashboardPath: getDashboardPathForUser(result.user),
      };
    },
    []
  );

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const isAuthenticated = !!user;

  return (
    <SessionContext.Provider
      value={{
        user,
        isAuthenticated,
        initializing,
        loginWithCredentials,
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
