import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  fetchExpert,
  setDocumentVerdict,
  setExpertStatus,
} from "../../services/mobileAdminApi";
import { useMobileAdmin } from "../MobileAdminContext";
import ErrorBanner from "../components/ErrorBanner";
import StatusBadge from "../components/StatusBadge";
import SafeLink from "../components/SafeLink";
import ActionDialog from "../components/ActionDialog";
import { DASH, formatDateTime, formatList, humanize } from "../format";
import { formatWeeklyAvailability } from "../availability";
import "../mobile-admin.css";

/** Status transitions offered on this page.
 *
 *  `capability` is what `GET /api/admin/me` says this operator may do, and
 *  `allowed_transitions` on the dossier is what the backend will accept for
 *  this profile's current status. A control appears only when both agree — and
 *  the backend re-authorizes the transition anyway, so a control that slipped
 *  through would still be refused with a 403 this page displays. */
const TRANSITIONS = [
  {
    status: "active",
    capability: "experts.approve",
    label: "Approve & publish",
    tone: "primary",
    title: "Approve this expert",
    description:
      "Publishing lists the expert in the student-facing directory and grants access to students' clinical data. Super Admin only.",
  },
  {
    status: "rejected",
    capability: "experts.reject",
    label: "Reject",
    tone: "danger",
    title: "Reject this application",
    description: "The expert stays unlisted. The reason is recorded in the audit log.",
    reasonRequired: true,
  },
  {
    status: "pending_review",
    capability: "experts.reopen",
    label: "Move to pending review",
    tone: "",
    title: "Return to the review queue",
    description: "Puts the application back in front of reviewers.",
  },
  {
    status: "inactive",
    capability: "experts.suspend",
    label: "Suspend (unlist)",
    tone: "danger-outline",
    title: "Suspend this expert",
    description:
      "Removes the expert from the directory without rejecting the application. Super Admin only.",
    reasonRequired: true,
  },
];

/** `[field on ExpertDocuments, what the reviewer is looking at, why it matters]` */
const DOCUMENT_FIELDS = [
  ["government_id_url", "Government ID", "Identity"],
  ["degree_certificate_url", "Degree certificate", "Qualification"],
  ["license_certificate_url", "License certificate", "Licensure"],
  ["experience_certificate_url", "Experience certificate", "Experience"],
];

/** The audit action the Mobile backend writes for a document verdict. */
const DOCUMENT_VERDICT_ACTION = "expert.document_verdict";

function Field({ label, children }) {
  return (
    <div className="mobile-field">
      <span className="mobile-field-label">{label}</span>
      <span className="mobile-field-value">{children ?? DASH}</span>
    </div>
  );
}

/** The bio is free text the expert typed in the app: it arrives with its own
 *  newlines and can run to several paragraphs. Blank lines split paragraphs;
 *  single newlines survive through `white-space: pre-line` in the stylesheet.
 *  Nothing is truncated — a reviewer reads the whole thing. */
function Bio({ text }) {
  const paragraphs = String(text)
    .replace(/\r\n?/g, "\n")
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  if (paragraphs.length === 0) return null;

  return (
    <div className="mobile-bio">
      <span className="mobile-field-label">Bio</span>
      <div className="mobile-bio-body">
        {/* Paragraphs have no id of their own; position is the only key here. */}
        {paragraphs.map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      </div>
    </div>
  );
}

/** The published week, read out of the free-form `availability_schedule` JSON.
 *  Every day is listed so "Not available" is a stated fact rather than a gap. */
function Availability({ schedule, durationMinutes }) {
  const week = formatWeeklyAvailability(schedule, durationMinutes);
  if (!week.hasSchedule) {
    return <p className="mobile-muted">No availability published.</p>;
  }

  return (
    <div className="mobile-availability">
      {week.timezone && (
        <p className="mobile-availability-tz">Times shown in {week.timezone}</p>
      )}
      <ul className="mobile-week">
        {week.days.map((day) => (
          <li key={day.key} className={`mobile-week-day${day.ranges.length ? "" : " off"}`}>
            <span className="mobile-week-name">{day.label}</span>
            <span className="mobile-week-slots">
              {day.ranges.length ? (
                day.ranges.map((range) => (
                  <span key={range} className="mobile-slot">
                    {range}
                  </span>
                ))
              ) : (
                <span className="mobile-muted">Not available</span>
              )}
            </span>
          </li>
        ))}
      </ul>
      {week.extras.length > 0 && (
        <div className="mobile-week-extras">
          <span className="mobile-field-label">Other entries on this schedule</span>
          <ul className="mobile-week">
            {week.extras.map((extra) => (
              <li key={extra.key} className="mobile-week-day">
                <span className="mobile-week-name">{humanize(extra.label)}</span>
                <span className="mobile-week-slots">
                  {extra.ranges.map((range) => (
                    <span key={range} className="mobile-slot">
                      {range}
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function MobileExpertDetail() {
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
      setDetail(await fetchExpert(userId));
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
      if (dialog.kind === "status") {
        const result = await setExpertStatus(userId, dialog.status, reason);
        setNotice(
          `Status changed from ${result.previous_status} to ${result.status}.` +
            (result.is_listed_in_directory
              ? " The expert is now listed in the student directory."
              : "")
        );
      } else {
        await setDocumentVerdict(userId, dialog.status, reason);
        setNotice(`Documents recorded as ${dialog.status.replace(/_/g, " ")}.`);
      }
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
        <Link className="admin-back-link" to="/admin/mobile/experts">
          ← Back to experts
        </Link>
        <p className="admin-empty">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Link className="admin-back-link" to="/admin/mobile/experts">
          ← Back to experts
        </Link>
        <ErrorBanner error={error} onRetry={load} />
      </div>
    );
  }

  if (!detail) return null;

  const {
    user,
    profile,
    documents,
    questionnaire,
    checklist,
    allowed_transitions: allowedTransitions = [],
    is_listed_in_directory: listed,
    is_bookable: bookable,
    caseload = {},
    review_history: history = [],
  } = detail;

  const availableActions = TRANSITIONS.filter(
    (t) => allowedTransitions.includes(t.status) && can(t.capability)
  );

  const providedDocuments = documents
    ? DOCUMENT_FIELDS.filter(([key]) => Boolean(documents[key])).length
    : 0;

  // Why the documents were turned down: the remarks stored on the row, falling
  // back to the reason on the most recent verdict in the audit log. Only shown
  // when the backend actually says "rejected" — never inferred.
  const lastDocumentVerdict = history.find(
    (entry) => entry.action === DOCUMENT_VERDICT_ACTION
  );
  const rejectionReason =
    documents && documents.status === "rejected"
      ? documents.remarks || lastDocumentVerdict?.reason || null
      : null;

  // Secondary Admins hold neither capability; say so plainly instead of
  // silently rendering a shorter row of buttons.
  const lacksSuperActions = !can("experts.approve") || !can("experts.suspend");

  return (
    <div>
      <Link className="admin-back-link" to="/admin/mobile/experts">
        ← Back to experts
      </Link>

      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">{user.full_name}</h1>
          <p className="admin-page-sub">
            {user.email} · signed up {formatDateTime(user.created_at)}
          </p>
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
        <StatusBadge value={profile ? profile.status : "none"} />
        <span className={`admin-badge ${user.is_active ? "active" : "inactive"}`}>
          account {user.is_active ? "enabled" : "disabled"}
        </span>
        <span className={listed ? "mobile-status ok" : "mobile-status muted"}>
          {listed ? "Listed in directory" : "Not listed"}
        </span>
        <span className={bookable ? "mobile-status ok" : "mobile-status muted"}>
          {bookable ? "Bookable" : "No bookable slot"}
        </span>
      </div>

      {/* ── Review actions ───────────────────────────────────────────── */}
      <div className="admin-card">
        <h3 className="admin-section-title">Review decision</h3>

        {checklist && (
          <>
            <p className="admin-page-sub">
              {checklist.ready_for_approval
                ? "The application meets every check the backend requires before approval."
                : "The backend reports blocking gaps in this application."}
            </p>
            <ul className="mobile-checklist">
              {checklist.items.map((item) => (
                <li key={item.key} className={item.ok ? "ok" : "bad"}>
                  <span className="mobile-check-mark">{item.ok ? "✓" : "✕"}</span>
                  <span>
                    <strong>{item.label}</strong>
                    <span className="mobile-muted"> — {item.detail}</span>
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="mobile-actions">
          {availableActions.length === 0 ? (
            <p className="mobile-muted">
              No review action is available to your role for this application.
            </p>
          ) : (
            availableActions.map((action) => (
              <button
                key={action.status}
                type="button"
                className={`admin-btn ${action.tone}`}
                onClick={() => {
                  setActionError(null);
                  setDialog({ kind: "status", ...action });
                }}
              >
                {action.label}
              </button>
            ))
          )}
        </div>

        {lacksSuperActions && (
          <p className="mobile-muted" style={{ marginTop: "0.75rem" }}>
            Approving and suspending an expert are Super Admin actions. The Mobile
            backend enforces this regardless of what this page shows.
          </p>
        )}
      </div>

      {/* Documents carry the review, so they take the wide column on desktop and
          come first in the DOM — which is also the mobile stacking order. */}
      <div className="mobile-expert-layout">
        <div className="mobile-expert-docs">
          <div className="admin-card">
            <h3 className="admin-section-title">Documents</h3>
            {!documents ? (
              <p className="mobile-muted">No documents submitted.</p>
            ) : (
              <>
                <div className="mobile-summary">
                  <StatusBadge value={documents.status} />
                  <span
                    className={
                      documents.verification_recorded
                        ? "mobile-status ok"
                        : "mobile-status warn"
                    }
                  >
                    {documents.verification_recorded
                      ? "Verdict recorded"
                      : "No verdict recorded yet"}
                  </span>
                  <span className="mobile-muted">
                    {providedDocuments} of {DOCUMENT_FIELDS.length} submitted
                  </span>
                </div>

                {rejectionReason && (
                  <div className="mobile-rejection">
                    <span className="mobile-field-label">Rejection reason</span>
                    <p>{rejectionReason}</p>
                  </div>
                )}

                <p className="mobile-muted mobile-doc-note">
                  Links are supplied by the expert and point at third-party storage.
                  They are never fetched by any Sentio server; opening one leaves this
                  console.
                </p>

                <ul className="mobile-doc-list">
                  {DOCUMENT_FIELDS.map(([key, label, category]) => {
                    const url = documents[key];
                    return (
                      <li key={key} className={`mobile-doc${url ? "" : " missing"}`}>
                        <div className="mobile-doc-head">
                          <span className="mobile-doc-name">{label}</span>
                          <span className="mobile-doc-category">{category}</span>
                          <span
                            className={url ? "mobile-status ok" : "mobile-status muted"}
                          >
                            {url ? "Submitted" : "Not submitted"}
                          </span>
                        </div>
                        <div className="mobile-doc-meta">
                          <Field label="Verification">
                            <StatusBadge value={documents.status} />
                          </Field>
                          <Field label="Uploaded">
                            {formatDateTime(documents.created_at)}
                          </Field>
                          <Field label="Last updated">
                            {formatDateTime(documents.updated_at)}
                          </Field>
                        </div>
                        <div className="mobile-doc-actions">
                          <SafeLink url={url} label="Preview / download" />
                        </div>
                      </li>
                    );
                  })}
                </ul>

                {/* Stated once rather than repeated per row as if each file had its
                    own audit trail: the API keeps one status and one pair of
                    timestamps for the whole submission. */}
                <p className="mobile-muted mobile-doc-note">
                  Upload date and verification status are recorded once for the whole
                  submission — the Mobile API keeps no per-document timestamp or verdict.
                </p>

                {documents.remarks && documents.remarks !== rejectionReason && (
                  <div className="mobile-fields one-col">
                    <Field label="Remarks">{documents.remarks}</Field>
                  </div>
                )}

                {can("documents.record_verdict") && (
                  <div className="mobile-actions">
                    <button
                      type="button"
                      className="admin-btn primary"
                      onClick={() => {
                        setActionError(null);
                        setDialog({
                          kind: "document",
                          status: "verified",
                          title: "Record documents as verified",
                          description:
                            "States that you checked these documents. Recorded in the audit log.",
                          confirmLabelOverride: "Mark verified",
                          tone: "primary",
                          reasonLabel: "Remarks (recorded in the audit log)",
                        });
                      }}
                    >
                      Mark verified
                    </button>
                    <button
                      type="button"
                      className="admin-btn danger-outline"
                      onClick={() => {
                        setActionError(null);
                        setDialog({
                          kind: "document",
                          status: "rejected",
                          title: "Record documents as rejected",
                          description: "The expert must resubmit their documents.",
                          confirmLabelOverride: "Mark rejected",
                          tone: "danger",
                          reasonLabel: "Remarks (recorded in the audit log)",
                          reasonRequired: true,
                        });
                      }}
                    >
                      Mark rejected
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <div className="mobile-expert-info">
          {/* ── Basic information ──────────────────────────────────── */}
          <div className="admin-card">
            <h3 className="admin-section-title">Basic information</h3>
            {!profile ? (
              <p className="mobile-muted">
                This expert has not created a profile yet — nothing has been submitted
                for review.
              </p>
            ) : (
              <div className="mobile-fields one-col">
                <Field label="Professional category">
                  {profile.professional_category}
                </Field>
                <Field label="Title">{profile.title}</Field>
                <Field label="Contact number">{profile.contact_number}</Field>
                <Field label="Languages">{formatList(profile.languages)}</Field>
                <Field label="Profile photo">
                  <SafeLink url={profile.profile_photo_url} label="Open photo" />
                </Field>
                <Field label="Profile created">{formatDateTime(profile.created_at)}</Field>
                <Field label="Profile updated">{formatDateTime(profile.updated_at)}</Field>
              </div>
            )}
          </div>

          {/* ── Bio ────────────────────────────────────────────────── */}
          {profile && (
            <div className="admin-card">
              <h3 className="admin-section-title">Bio</h3>
              {profile.bio ? (
                <Bio text={profile.bio} />
              ) : (
                <p className="mobile-muted">No bio written.</p>
              )}
            </div>
          )}

          {/* ── Availability ───────────────────────────────────────── */}
          {profile && (
            <div className="admin-card">
              <h3 className="admin-section-title">Availability</h3>
              <Availability
                schedule={profile.availability_schedule}
                durationMinutes={profile.session_duration_minutes}
              />
            </div>
          )}

          {/* ── Professional information ───────────────────────────── */}
          {profile && (
            <div className="admin-card">
              <h3 className="admin-section-title">Professional information</h3>
              <div className="mobile-fields one-col">
                <Field label="Highest degree">{profile.highest_degree}</Field>
                <Field label="Years of experience">{profile.years_of_experience}</Field>
                <Field label="License number">{profile.license_number}</Field>
                <Field label="Certifications">{formatList(profile.certifications)}</Field>
                <Field label="Areas of expertise">
                  {formatList(profile.areas_of_expertise)}
                </Field>
                <Field label="Scope of practice (concerns)">
                  {formatList(profile.concern_categories)}
                </Field>
                <Field label="Session modes">{formatList(profile.session_modes)}</Field>
                <Field label="Session duration">
                  {profile.session_duration_minutes
                    ? `${profile.session_duration_minutes} min`
                    : null}
                </Field>
                <Field label="Consultation fee">
                  {profile.consultation_fee === null ||
                  profile.consultation_fee === undefined
                    ? null
                    : profile.consultation_fee}
                </Field>
              </div>
            </div>
          )}

          {/* ── Questionnaire ──────────────────────────────────────── */}
          <div className="admin-card">
            <h3 className="admin-section-title">Questionnaire</h3>
            {!questionnaire ? (
              <p className="mobile-muted">No questionnaire row for this expert.</p>
            ) : (
              <>
                <p className="admin-page-sub">
                  {questionnaire.professional_category} ·{" "}
                  {questionnaire.submitted ? "submitted" : "not submitted"} ·{" "}
                  {formatDateTime(questionnaire.updated_at || questionnaire.created_at)}
                </p>
                <dl className="mobile-qa">
                  {questionnaire.answers.map((qa) => (
                    <div key={qa.id} className="mobile-qa-item">
                      <dt>{qa.question}</dt>
                      <dd>{qa.answer || <span className="mobile-muted">No answer</span>}</dd>
                    </div>
                  ))}
                </dl>
                {Object.keys(questionnaire.unmatched_answers || {}).length > 0 && (
                  <div className="mobile-unmatched">
                    <span className="mobile-field-label">
                      Answers with no matching question
                    </span>
                    <p className="mobile-muted">
                      Stored on the row but outside the current question bank — shown
                      rather than dropped.
                    </p>
                    <dl className="mobile-qa">
                      {Object.entries(questionnaire.unmatched_answers).map(([key, value]) => (
                        <div key={key} className="mobile-qa-item">
                          <dt>{key}</dt>
                          <dd>{typeof value === "string" ? value : JSON.stringify(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
              </>
            )}
          </div>

          {/* ── Account ────────────────────────────────────────────── */}
          <div className="admin-card">
            <h3 className="admin-section-title">Account</h3>
            <div className="mobile-fields one-col">
              <Field label="User ID">
                <code className="mobile-code">{user.id}</code>
              </Field>
              <Field label="Role">{user.role}</Field>
              <Field label="Onboarded">{user.onboarded ? "Yes" : "No"}</Field>
              <Field label="Account state">
                {user.is_active ? "Enabled" : "Disabled"}
              </Field>
              <Field label="Last updated">{formatDateTime(user.updated_at)}</Field>
            </div>
          </div>

          {/* ── Caseload ───────────────────────────────────────────── */}
          <div className="admin-card">
            <h3 className="admin-section-title">Caseload</h3>
            {Object.keys(caseload).length === 0 ? (
              <p className="mobile-muted">No sessions recorded.</p>
            ) : (
              <div className="mobile-fields one-col">
                {Object.entries(caseload).map(([key, value]) => (
                  <Field key={key} label={humanize(key)}>
                    {value}
                  </Field>
                ))}
              </div>
            )}
          </div>

          {/* ── Review history ─────────────────────────────────────── */}
          <div className="admin-card">
            <h3 className="admin-section-title">Review history</h3>
            {history.length === 0 ? (
              <p className="mobile-muted">
                No admin action has been taken on this application yet.
              </p>
            ) : (
              <ol className="mobile-history">
                {history.map((entry) => (
                  <li key={entry.id}>
                    <div className="mobile-history-head">
                      <span className="admin-badge role">{entry.action}</span>
                      <span className="mobile-muted">{formatDateTime(entry.created_at)}</span>
                    </div>
                    <div>
                      {entry.from_value || entry.to_value ? (
                        <span>
                          {entry.from_value || DASH} → <strong>{entry.to_value || DASH}</strong>
                        </span>
                      ) : null}
                    </div>
                    <div className="mobile-muted">
                      {entry.actor_email || entry.actor_subject} · {entry.actor_role}
                    </div>
                    {entry.reason && <div className="mobile-reason">{entry.reason}</div>}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </div>

      <ActionDialog
        open={Boolean(dialog)}
        title={dialog?.title || ""}
        description={dialog?.description}
        confirmLabel={dialog?.confirmLabelOverride || dialog?.label || "Confirm"}
        tone={dialog?.tone || "primary"}
        reasonLabel={dialog?.reasonLabel}
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
