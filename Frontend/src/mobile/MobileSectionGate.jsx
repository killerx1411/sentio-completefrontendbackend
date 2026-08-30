import { Outlet } from "react-router-dom";
import { useMobileAdmin } from "./MobileAdminContext";
import ErrorBanner from "./components/ErrorBanner";
import "./mobile-admin.css";

/**
 * Wraps every Mobile Admin page.
 *
 * Route access is already gated on the Mobile Admin roles; this gate waits for
 * the Mobile backend's own answer about the operator (`GET /api/admin/me`) and
 * surfaces it if that backend refuses. It is the second, authoritative opinion:
 * the console never renders a Mobile page on the strength of a role name alone.
 */
export default function MobileSectionGate() {
  const { identity, loading, error, reload } = useMobileAdmin();

  if (loading) {
    return <p className="admin-empty">Loading Mobile Admin…</p>;
  }

  if (error) {
    return (
      <div>
        <h1 className="admin-page-title">Mobile administration</h1>
        <p className="admin-page-sub">
          The Mobile backend did not accept this session.
        </p>
        <ErrorBanner error={error} onRetry={reload} />
      </div>
    );
  }

  if (!identity) {
    return (
      <div>
        <h1 className="admin-page-title">Mobile administration</h1>
        <div className="admin-banner error" role="alert">
          The Mobile backend returned no identity for this session.
        </div>
      </div>
    );
  }

  return <Outlet />;
}
