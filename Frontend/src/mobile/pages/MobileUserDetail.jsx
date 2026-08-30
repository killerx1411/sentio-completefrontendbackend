import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchMobileUser, setUserActive } from "../../services/mobileAdminApi";
import { useMobileAdmin } from "../MobileAdminContext";
import ErrorBanner from "../components/ErrorBanner";
import StatusBadge from "../components/StatusBadge";
import ActionDialog from "../components/ActionDialog";
import { DASH, formatDate, formatDateTime, formatList, humanize } from "../format";
import "../mobile-admin.css";

function Field({ label, children }) {
  return (
    <div className="mobile-field">
      <span className="mobile-field-label">{label}</span>
      <span className="mobile-field-value">{children ?? DASH}</span>
    </div>
  );
}

export default function MobileUserDetail() {
  const { userId } = useParams();
  const { can } = useMobileAdmin();

  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState("");
  const [dialog, setDialog] = useState(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDetail(await fetchMobileUser(userId));
    } catch (err) {
      setDetail(null);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    load();
  }, [load]);

  async function runAction(reason) {
    setBusy(true);
    setActionError(null);
    try {
      await setUserActive(userId, dialog.isActive, reason);
      setNotice(dialog.isActive ? "Account re-enabled." : "Account disabled.");
      setDialog(null);
      await load();
    } catch (err) {
      setActionError(err);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div>
        <Link className="admin-back-link" to="/admin/mobile/users">
          ← Back to users
        </Link>
        <p className="admin-empty">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Link className="admin-back-link" to="/admin/mobile/users">
          ← Back to users
        </Link>
        <ErrorBanner error={error} onRetry={load} />
      </div>
    );
  }

  if (!detail) return null;

  const { user, profile, subscription, sessions_count, open_risk_flags, is_expert, expert_status } =
    detail;

  return (
    <div>
      <Link className="admin-back-link" to="/admin/mobile/users">
        ← Back to users
      </Link>

      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">{user.full_name}</h1>
          <p className="admin-page-sub">{user.email}</p>
        </div>
        <button type="button" className="admin-btn" onClick={load}>
          Refresh
        </button>
      </div>

      {notice && (
        <div className="admin-banner success" role="status">
          {notice}
        </div>
      )}

      <div className="mobile-summary">
        <span className={`admin-badge ${user.is_active ? "active" : "inactive"}`}>
          account {user.is_active ? "enabled" : "disabled"}
        </span>
        <span className="admin-badge role">{user.role}</span>
        {is_expert && <StatusBadge value={expert_status || "none"} />}
      </div>

      <div className="admin-detail-layout">
        <div>
          <div className="admin-card">
            <h3 className="admin-section-title">Profile</h3>
            {!profile ? (
              <p className="mobile-muted">This user has not completed a profile.</p>
            ) : (
              <div className="mobile-fields">
                <Field label="Age">{profile.age}</Field>
                <Field label="Gender">{profile.gender}</Field>
                <Field label="City">{profile.city}</Field>
                <Field label="Country">{profile.country}</Field>
                <Field label="School / workplace">{profile.school_or_workplace}</Field>
                <Field label="Grade / year">{profile.grade_or_year}</Field>
                <Field label="Languages">{formatList(profile.languages)}</Field>
                <Field label="Timezone">{profile.timezone}</Field>
              </div>
            )}
          </div>

          <div className="admin-card">
            <h3 className="admin-section-title">Subscription</h3>
            {!subscription ? (
              <p className="mobile-muted">No live subscription.</p>
            ) : (
              <div className="mobile-fields">
                {Object.entries(subscription)
                  .filter(([key]) => key !== "id")
                  .map(([key, value]) => (
                    <Field key={key} label={humanize(key)}>
                      {key.includes("period") || key.includes("_at")
                        ? formatDate(value)
                        : typeof value === "boolean"
                          ? value
                            ? "Yes"
                            : "No"
                          : String(value ?? DASH)}
                    </Field>
                  ))}
              </div>
            )}
          </div>
        </div>

        <div>
          <div className="admin-card">
            <h3 className="admin-section-title">Account</h3>
            <div className="mobile-fields one-col">
              <Field label="User ID">
                <code className="mobile-code">{user.id}</code>
              </Field>
              <Field label="Onboarded">{user.onboarded ? "Yes" : "No"}</Field>
              <Field label="Sessions">{sessions_count}</Field>
              <Field label="Open risk flags">{open_risk_flags}</Field>
              <Field label="Signed up">{formatDateTime(user.created_at)}</Field>
              <Field label="Last updated">{formatDateTime(user.updated_at)}</Field>
            </div>

            <div className="mobile-actions">
              {user.is_active
                ? can("users.disable") && (
                    <button
                      type="button"
                      className="admin-btn danger-outline"
                      onClick={() => {
                        setActionError(null);
                        setDialog({
                          isActive: false,
                          title: "Disable this account",
                          description:
                            "The user can no longer sign in to the mobile app. Recorded in the audit log.",
                          confirmLabel: "Disable account",
                          tone: "danger",
                          reasonRequired: true,
                        });
                      }}
                    >
                      Disable account
                    </button>
                  )
                : can("users.enable") && (
                    <button
                      type="button"
                      className="admin-btn primary"
                      onClick={() => {
                        setActionError(null);
                        setDialog({
                          isActive: true,
                          title: "Re-enable this account",
                          description:
                            "Reverses a moderation decision. Super Admin only; the backend enforces it.",
                          confirmLabel: "Re-enable account",
                          tone: "primary",
                        });
                      }}
                    >
                      Re-enable account
                    </button>
                  )}
            </div>

            {!user.is_active && !can("users.enable") && (
              <p className="mobile-muted">
                Re-enabling a disabled account is a Mobile Super Admin action.
              </p>
            )}
          </div>

          {is_expert && (
            <div className="admin-card">
              <h3 className="admin-section-title">Expert application</h3>
              <p className="admin-page-sub">
                This account also has a counsellor profile.
              </p>
              <Link className="admin-btn" to={`/admin/mobile/experts/${user.id}`}>
                Open review dossier
              </Link>
            </div>
          )}
        </div>
      </div>

      <ActionDialog
        open={Boolean(dialog)}
        title={dialog?.title || ""}
        description={dialog?.description}
        confirmLabel={dialog?.confirmLabel}
        tone={dialog?.tone || "primary"}
        reasonRequired={dialog?.reasonRequired}
        busy={busy}
        error={actionError}
        onConfirm={runAction}
        onCancel={() => {
          setDialog(null);
          setActionError(null);
        }}
      />
    </div>
  );
}
