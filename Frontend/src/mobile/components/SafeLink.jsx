/**
 * Renders a document link supplied by an expert during onboarding.
 *
 * SECURITY: these are arbitrary third-party URLs typed by an untrusted user.
 * - The server never fetches them (no proxy, no preview, no SSRF surface).
 * - Only http/https render as a link; anything else (javascript:, data:, file:,
 *   a relative path) is shown as inert text so a click can never execute it.
 * - Links open in a new tab with rel="noopener noreferrer" so the opened page
 *   gets no handle on this console.
 */

function safeHref(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  let url;
  try {
    url = new URL(value.trim());
  } catch {
    return null;
  }
  return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
}

export default function SafeLink({ url, label }) {
  if (!url) return <span className="mobile-muted">Not provided</span>;

  const href = safeHref(url);
  if (!href) {
    return (
      <span className="mobile-unsafe-link" title="Not an http(s) link — not opened">
        {url} <span className="admin-badge inactive">unsafe link</span>
      </span>
    );
  }

  return (
    <a className="admin-link" href={href} target="_blank" rel="noopener noreferrer">
      {label || href}
    </a>
  );
}
