/** Status pill for counsellor_profiles.status / counsellor_documents.status.
 *  Reports exactly what the backend stored — never a friendlier guess. */

const TONE = {
  active: "ok",
  verified: "ok",
  pending_review: "warn",
  pending_verification: "warn",
  draft: "muted",
  none: "muted",
  rejected: "bad",
  inactive: "bad",
};

const LABEL = {
  pending_review: "Pending review",
  pending_verification: "Pending verification",
  none: "No profile",
};

export default function StatusBadge({ value, fallback = "—" }) {
  if (!value) return <span className="mobile-muted">{fallback}</span>;
  const tone = TONE[value] || "muted";
  return (
    <span className={`mobile-status ${tone}`}>
      {LABEL[value] || value.replace(/_/g, " ")}
    </span>
  );
}
