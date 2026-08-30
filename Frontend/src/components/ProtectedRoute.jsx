// SECURITY: ProtectedRoute must never render children until initializing is false and isAuthenticated is confirmed.

import { Navigate, useLocation } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { getDashboardPathForUser } from "../utils/roleRoutes";

function LoadingScreen() {
  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#111",
        color: "#fff",
        fontFamily: "sans-serif",
      }}
    >
      Loading…
    </div>
  );
}

export default function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, initializing, user } = useSession();
  const location = useLocation();

  if (initializing) return <LoadingScreen />;

  if (!isAuthenticated) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  if (allowedRoles?.length) {
    const userRoleNames = (user?.roles || []).map((r) => r.name);
    const hasAllowedRole = userRoleNames.some((name) => allowedRoles.includes(name));
    if (!hasAllowedRole) {
      return <Navigate to={getDashboardPathForUser(user)} replace />;
    }
  }

  return children;
}
