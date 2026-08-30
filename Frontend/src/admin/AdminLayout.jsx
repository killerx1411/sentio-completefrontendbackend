import { useEffect, useRef, useState, useCallback } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import {
  ROLES,
  getPrimaryRole,
  isAdminUser,
  isMobileAdminUser,
  isSuperAdminUser,
  roleLabel,
} from "../utils/roleRoutes";
import { refreshSession } from "../services/authApi";
import { useMobileAdmin } from "../mobile/MobileAdminContext";
import { visibleMobileNav } from "../mobile/navigation";
import icon from "../assets/icon.png";
import "./admin.css";

const NAV = [
  { to: "/admin", end: true, label: "Dashboard" },
  { to: "/admin/pending", label: "Pending signups" },
  { to: "/admin/users", label: "User management" },
  { to: "/admin/audit-logs", label: "Audit logs" },
];

const INACTIVITY_WARNING_MS = 28 * 60 * 1000;
const INACTIVITY_LOGOUT_MS = 30 * 60 * 1000;
const ACTIVITY_DEBOUNCE_MS = 500;

function isUserDetailRoute(path) {
  return /^\/admin\/users\/[^/]+/.test(path);
}

export default function AdminLayout() {
  const { user, logout } = useSession();
  const navigate = useNavigate();
  const role = getPrimaryRole(user);
  const isSuper = isSuperAdminUser(user);
  const isNormalAdmin = role === ROLES.NORMAL_ADMIN;

  // The two administrations this console serves. A user holds one or the other:
  // the auth authority never issues a token that satisfies both, so these are
  // never true at the same time.
  const isB2bAdmin = isAdminUser(user);
  const isMobileAdmin = isMobileAdminUser(user);
  const { has: hasMobilePermission, identity: mobileIdentity } = useMobileAdmin();
  const mobileNav = isMobileAdmin ? visibleMobileNav(hasMobilePermission) : [];

  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false);
  const [refreshingSession, setRefreshingSession] = useState(false);
  const warningTimerRef = useRef(null);
  const logoutTimerRef = useRef(null);
  const debounceRef = useRef(null);

  const resetInactivityTimers = useCallback(() => {
    clearTimeout(warningTimerRef.current);
    clearTimeout(logoutTimerRef.current);
    setShowTimeoutWarning(false);

    warningTimerRef.current = setTimeout(() => {
      setShowTimeoutWarning(true);
    }, INACTIVITY_WARNING_MS);

    logoutTimerRef.current = setTimeout(async () => {
      await logout();
      navigate("/", { replace: true });
      window.history.replaceState(null, "", "/");
    }, INACTIVITY_LOGOUT_MS);
  }, [logout, navigate]);

  useEffect(() => {
    const onActivity = () => {
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(resetInactivityTimers, ACTIVITY_DEBOUNCE_MS);
    };

    const events = ["mousemove", "keydown", "click"];
    events.forEach((ev) => window.addEventListener(ev, onActivity));
    resetInactivityTimers();

    return () => {
      events.forEach((ev) => window.removeEventListener(ev, onActivity));
      clearTimeout(debounceRef.current);
      clearTimeout(warningTimerRef.current);
      clearTimeout(logoutTimerRef.current);
    };
  }, [resetInactivityTimers]);

  async function handleStayLoggedIn() {
    setRefreshingSession(true);
    try {
      await refreshSession();
      resetInactivityTimers();
    } catch {
      await logout();
      navigate("/", { replace: true });
      window.history.replaceState(null, "", "/");
    } finally {
      setRefreshingSession(false);
    }
  }

  async function handleLogoutNow() {
    await logout();
    navigate("/", { replace: true });
    window.history.replaceState(null, "", "/");
  }

  async function handleLogout() {
    await logout();
    navigate("/", { replace: true });
    window.history.replaceState(null, "", "/");
  }

  function handleNavClick(e, to) {
    if (isNormalAdmin && isUserDetailRoute(to)) {
      e.preventDefault();
    }
  }

  return (
    <div className="admin-root">
      <aside className="admin-sidebar">
        <img src={icon} alt="Sentio Mind" style={{ width: 150, height: 50, objectFit: "contain", borderRadius: 10 }} />
        <h2>Administration</h2>
        <nav className="admin-nav">
          {isB2bAdmin && (
            <>
              <div className="admin-nav-group">B2B</div>
              {NAV.filter((item) => {
                if (item.to === "/admin/pending") return isSuper;
                if (item.to === "/admin/audit-logs") return isSuper;
                return true;
              }).map(({ to, end, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={(e) => handleNavClick(e, to)}
                >
                  {label}
                </NavLink>
              ))}
            </>
          )}

          {isMobileAdmin && (
            <>
              <div className="admin-nav-group">Mobile</div>
              {mobileNav.length === 0 && !mobileIdentity ? (
                <span className="admin-nav-note">Loading sections…</span>
              ) : (
                mobileNav.map(({ to, end, label }) => (
                  <NavLink key={to} to={to} end={end}>
                    {label}
                  </NavLink>
                ))
              )}
            </>
          )}
        </nav>
        <div style={{ marginTop: "auto", fontSize: "0.85rem" }}>
          <div style={{ fontWeight: 600, color: "#0f4c5c" }}>{user?.full_name}</div>
          <div style={{ color: "#2ec4b6", fontSize: "0.75rem", fontWeight: 700 }}>{roleLabel(role)}</div>
          <div style={{ color: "#64748b", marginBottom: "0.75rem" }}>{user?.email}</div>
          <button type="button" className="admin-btn" onClick={handleLogout} style={{ width: "100%" }}>
            Log out
          </button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>

      {showTimeoutWarning && (
        <div className="admin-modal-overlay">
          <div className="admin-card admin-modal">
            <h3 className="admin-section-title">Session expiring</h3>
            <p className="admin-page-sub">
              Your session will expire in 2 minutes due to inactivity.
            </p>
            <div className="admin-modal-actions">
              <button
                type="button"
                className="admin-btn"
                onClick={handleLogoutNow}
                disabled={refreshingSession}
              >
                Log out now
              </button>
              <button
                type="button"
                className="admin-btn primary"
                onClick={handleStayLoggedIn}
                disabled={refreshingSession}
              >
                {refreshingSession ? "Refreshing…" : "Stay logged in"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
