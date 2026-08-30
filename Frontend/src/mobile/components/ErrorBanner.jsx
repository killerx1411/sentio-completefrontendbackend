/**
 * Surfaces an error from the Mobile Admin API.
 *
 * A 403 is shown as an authorization failure with the backend's own message.
 * The backend is authoritative: if it refuses, the console says so rather than
 * pretending the action was unavailable.
 */

export default function ErrorBanner({ error, onRetry }) {
  if (!error) return null;

  const status = error.status;
  const isForbidden = status === 403;
  const title = isForbidden
    ? "Not authorized"
    : status === 404
      ? "Not found"
      : status === 503
        ? "Service unavailable"
        : "Request failed";

  return (
    <div className="admin-banner error" role="alert">
      <strong>{title}</strong>
      {status ? <span className="mobile-status-code"> ({status})</span> : null}
      <div>{error.message || "Something went wrong."}</div>
      {isForbidden && (
        <div className="mobile-muted" style={{ marginTop: "0.35rem" }}>
          Your Mobile Admin role does not permit this action.
        </div>
      )}
      {onRetry && (
        <button
          type="button"
          className="admin-btn"
          style={{ marginTop: "0.6rem" }}
          onClick={onRetry}
        >
          Try again
        </button>
      )}
    </div>
  );
}
