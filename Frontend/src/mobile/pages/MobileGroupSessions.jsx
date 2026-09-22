import { useCallback, useEffect, useMemo, useState } from "react";
import ActionDialog from "../components/ActionDialog";
import ErrorBanner from "../components/ErrorBanner";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import { useMobileAdmin } from "../MobileAdminContext";
import { formatDateTime } from "../format";
import {
  approveGroupSession,
  cancelGroupSession,
  fetchGroupSessionRegistrations,
  fetchGroupSessions,
  rejectGroupSession,
  requestGroupSessionChanges,
  setGroupSessionMeetingLink,
} from "../../services/mobileAdminApi";
import "../mobile-admin.css";

/**
 * The group-session review queue.
 *
 * A counsellor proposes a session in the mobile app; nothing reaches a user
 * until it is approved here. Approving is a super admin's call and the backend
 * enforces that — this page only avoids offering a button that would 403.
 *
 * The meet link is the thing the whole feature turns on: 24 hours before the
 * start, the backend mails it to everyone holding a confirmed place. A session
 * approved without one is flagged in this table, because nothing will go out.
 */

const STATUSES = [
  { value: "", label: "Any" },
  { value: "pending_review", label: "Awaiting review" },
  { value: "changes_requested", label: "Changes requested" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "cancelled", label: "Cancelled" },
  { value: "completed", label: "Completed" },
];

const PAGE_SIZE = 25;

export default function MobileGroupSessions() {
  const { has, isSuperAdmin } = useMobileAdmin();
  const [status, setStatus] = useState("pending_review");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);

  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [dialog, setDialog] = useState(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);

  const [expanded, setExpanded] = useState(null);
  const [roster, setRoster] = useState({ items: [], total: 0 });

  const canWrite = has("mobile.content.write");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGroupSessions({
        status: status || undefined,
        search: search.trim() || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setRows(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [status, search, offset]);

  useEffect(() => {
    load();
  }, [load]);

  const openRoster = useCallback(
    async (sessionId) => {
      if (expanded === sessionId) {
        setExpanded(null);
        return;
      }
      setExpanded(sessionId);
      setRoster({ items: [], total: 0 });
      try {
        const data = await fetchGroupSessionRegistrations(sessionId, { limit: 100 });
        setRoster({ items: data.items || [], total: data.total || 0 });
      } catch (err) {
        setActionError(err);
      }
    },
    [expanded]
  );

  const runAction = useCallback(
    async (fn) => {
      setBusy(true);
      setActionError(null);
      try {
        await fn();
        setDialog(null);
        await load();
      } catch (err) {
        setActionError(err);
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  const dialogProps = useMemo(() => {
    if (!dialog) return null;
    const { kind, row } = dialog;
    if (kind === "approve") {
      return {
        title: `Approve “${row.title}”?`,
        description: row.meeting_url
          ? "The waitlist opens immediately. The link goes out to everyone confirmed 24 hours before the start."
          : "This session has no meeting link yet. It will be approved, but nothing can be sent until a link is added — the counsellor can supply one, or you can set it here.",
        confirmLabel: "Approve and publish",
        tone: "primary",
        reasonLabel: "Note to the counsellor (recorded in the audit log)",
        reasonRequired: false,
        onConfirm: (note) =>
          runAction(() => approveGroupSession(row.id, { note: note || null })),
      };
    }
    if (kind === "reject") {
      return {
        title: `Decline “${row.title}”?`,
        description: "The counsellor is emailed your reason. They cannot resubmit this request.",
        confirmLabel: "Decline",
        tone: "danger",
        reasonRequired: true,
        onConfirm: (reason) => runAction(() => rejectGroupSession(row.id, reason)),
      };
    }
    if (kind === "changes") {
      return {
        title: `Send “${row.title}” back?`,
        description: "The counsellor can edit and resubmit. Say what needs to change.",
        confirmLabel: "Request changes",
        tone: "primary",
        reasonRequired: true,
        onConfirm: (reason) => runAction(() => requestGroupSessionChanges(row.id, reason)),
      };
    }
    if (kind === "cancel") {
      return {
        title: `Cancel “${row.title}”?`,
        description: `${row.confirmed_count + row.waitlisted_count} people will be emailed. This cannot be undone.`,
        confirmLabel: "Cancel the session",
        tone: "danger",
        reasonRequired: true,
        onConfirm: (reason) => runAction(() => cancelGroupSession(row.id, reason)),
      };
    }
    return null;
  }, [dialog, runAction]);

  return (
    <div className="admin-page">
      <header className="admin-page-head">
        <h2 className="admin-page-title">Group sessions</h2>
        <p className="admin-page-sub">
          Counsellors propose these in the app. Nothing is visible to users until it is
          approved here, and the meeting link is mailed to everyone confirmed 24 hours
          before the start.
        </p>
      </header>

      {error && <ErrorBanner error={error} onRetry={load} />}

      <div className="admin-card">
        <div className="admin-filter-row">
          <label htmlFor="gs-status">Status</label>
          <select
            id="gs-status"
            value={status}
            onChange={(e) => {
              setOffset(0);
              setStatus(e.target.value);
            }}
          >
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>

          <label htmlFor="gs-search">Title</label>
          <input
            id="gs-search"
            type="search"
            value={search}
            placeholder="Search titles…"
            onChange={(e) => {
              setOffset(0);
              setSearch(e.target.value);
            }}
          />
        </div>

        {loading ? (
          <p className="mobile-muted">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="mobile-muted">No group sessions match this filter.</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Host</th>
                <th>Starts</th>
                <th>Places</th>
                <th>Link</th>
                <th>Status</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <GroupSessionRow
                  key={row.id}
                  row={row}
                  canWrite={canWrite}
                  isSuperAdmin={isSuperAdmin}
                  expanded={expanded === row.id}
                  roster={roster}
                  onToggleRoster={() => openRoster(row.id)}
                  onAction={(kind) => {
                    setActionError(null);
                    setDialog({ kind, row });
                  }}
                  onLinkSaved={load}
                  onLinkError={setActionError}
                />
              ))}
            </tbody>
          </table>
        )}

        <Pagination
          page={{ total, limit: PAGE_SIZE, offset }}
          busy={loading}
          onChange={setOffset}
        />
      </div>

      {dialogProps && (
        <ActionDialog
          open
          busy={busy}
          error={actionError}
          onCancel={() => setDialog(null)}
          {...dialogProps}
        />
      )}
    </div>
  );
}

function GroupSessionRow({
  row,
  canWrite,
  isSuperAdmin,
  expanded,
  roster,
  onToggleRoster,
  onAction,
  onLinkSaved,
  onLinkError,
}) {
  const [editingLink, setEditingLink] = useState(false);
  const [url, setUrl] = useState(row.meeting_url || "");
  const [passcode, setPasscode] = useState(row.meeting_passcode || "");
  const [saving, setSaving] = useState(false);

  const reviewable = row.status === "pending_review" || row.status === "changes_requested";
  const cancellable = row.status === "approved";
  const missingLink = row.status === "approved" && !row.meeting_url;

  const saveLink = async () => {
    setSaving(true);
    try {
      await setGroupSessionMeetingLink(row.id, {
        meeting_url: url.trim(),
        meeting_passcode: passcode.trim() || null,
        meeting_provider: null,
      });
      setEditingLink(false);
      await onLinkSaved();
    } catch (err) {
      onLinkError(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <tr>
        <td>
          <strong>{row.title}</strong>
          <div className="mobile-muted">
            {row.duration_minutes} min
            {row.topic ? ` · ${row.topic}` : ""}
          </div>
        </td>
        <td>
          {row.counsellor_name}
          <div className="mobile-muted">{row.counsellor_email}</div>
        </td>
        <td>{formatDateTime(row.scheduled_start)}</td>
        <td>
          {row.confirmed_count}
          {row.capacity ? ` / ${row.capacity}` : ""}
          {row.waitlisted_count > 0 && (
            <div className="mobile-muted">{row.waitlisted_count} waiting</div>
          )}
          <button type="button" className="admin-btn link" onClick={onToggleRoster}>
            {expanded ? "Hide list" : "View list"}
          </button>
        </td>
        <td>
          {editingLink ? (
            <div className="admin-form-grid">
              <input
                type="url"
                value={url}
                placeholder="https://…"
                onChange={(e) => setUrl(e.target.value)}
              />
              <input
                type="text"
                value={passcode}
                placeholder="Passcode (optional)"
                onChange={(e) => setPasscode(e.target.value)}
              />
              <button
                type="button"
                className="admin-btn primary"
                disabled={saving || !url.trim()}
                onClick={saveLink}
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                type="button"
                className="admin-btn"
                onClick={() => setEditingLink(false)}
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              {row.meeting_url ? (
                <span className="admin-badge role">set</span>
              ) : (
                <span className="admin-badge danger">none</span>
              )}
              {row.links_sent_count > 0 && (
                <div className="mobile-muted">{row.links_sent_count} sent</div>
              )}
              {missingLink && (
                <div className="mobile-muted">Nothing will be sent until a link is added.</div>
              )}
              {canWrite && row.status !== "cancelled" && row.status !== "completed" && (
                <button
                  type="button"
                  className="admin-btn link"
                  onClick={() => setEditingLink(true)}
                >
                  {row.meeting_url ? "Change" : "Add link"}
                </button>
              )}
            </>
          )}
        </td>
        <td>
          <StatusBadge value={row.status} />
        </td>
        <td className="admin-row-actions">
          {reviewable && canWrite && (
            <>
              <button
                type="button"
                className="admin-btn primary"
                disabled={!isSuperAdmin}
                title={
                  isSuperAdmin
                    ? "Publish this session"
                    : "Only a mobile_super_admin can publish a group session"
                }
                onClick={() => onAction("approve")}
              >
                Approve
              </button>
              <button
                type="button"
                className="admin-btn"
                onClick={() => onAction("changes")}
              >
                Request changes
              </button>
              <button
                type="button"
                className="admin-btn danger"
                onClick={() => onAction("reject")}
              >
                Decline
              </button>
            </>
          )}
          {cancellable && canWrite && (
            <button
              type="button"
              className="admin-btn danger"
              onClick={() => onAction("cancel")}
            >
              Cancel
            </button>
          )}
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={7}>
            <div className="admin-card inset">
              <h4 className="admin-section-title">
                Who is coming ({roster.total})
              </h4>
              {roster.items.length === 0 ? (
                <p className="mobile-muted">Nobody has joined yet.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Place</th>
                      <th>Joined</th>
                      <th>Link sent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roster.items.map((r) => (
                      <tr key={r.id}>
                        <td>{r.full_name}</td>
                        <td>{r.email}</td>
                        <td>
                          <StatusBadge value={r.status} />
                        </td>
                        <td>{formatDateTime(r.joined_at)}</td>
                        <td>{r.link_sent_at ? formatDateTime(r.link_sent_at) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
