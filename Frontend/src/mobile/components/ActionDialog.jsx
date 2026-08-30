import { useEffect, useState } from "react";

/**
 * Confirmation modal for a Mobile Admin write, reusing the existing B2B admin
 * modal styling. The reason is passed straight through to the API, which
 * records it on the append-only admin audit row.
 */
export default function ActionDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  tone = "primary",
  reasonLabel = "Reason (recorded in the audit log)",
  reasonRequired = false,
  busy,
  error,
  onConfirm,
  onCancel,
}) {
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (open) setReason("");
  }, [open]);

  if (!open) return null;

  const blocked = busy || (reasonRequired && !reason.trim());

  return (
    <div className="admin-modal-overlay">
      <div className="admin-card admin-modal">
        <h3 className="admin-section-title">{title}</h3>
        {description && <p className="admin-page-sub">{description}</p>}

        {error && (
          <div className="admin-banner error" role="alert">
            {error.message || "Action failed."}
          </div>
        )}

        <div className="admin-form-grid">
          <label htmlFor="mobile-action-reason">
            {reasonLabel}
            {reasonRequired ? " *" : ""}
          </label>
          <textarea
            id="mobile-action-reason"
            className="mobile-textarea"
            rows={3}
            maxLength={2000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>

        <div className="admin-modal-actions">
          <button type="button" className="admin-btn" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className={`admin-btn ${tone}`}
            onClick={() => onConfirm(reason.trim())}
            disabled={blocked}
          >
            {busy ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
