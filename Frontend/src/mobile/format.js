/** Display helpers for Mobile Admin data.
 *
 *  Nothing here invents a value: a null stays "—" rather than becoming a
 *  plausible-looking default, matching the Mobile Admin API's own rule. */

const ISO_DATE = /^\d{4}-\d{2}-\d{2}(T|$)/;

export const DASH = "—";

export function formatDateTime(value) {
  if (!value) return DASH;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

export function formatDate(value) {
  if (!value) return DASH;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString();
}

export function formatMoney(cents, currency) {
  if (cents === null || cents === undefined) return DASH;
  const amount = Number(cents) / 100;
  if (Number.isNaN(amount)) return DASH;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "INR",
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency || ""}`.trim();
  }
}

export function formatBool(value) {
  if (value === null || value === undefined) return DASH;
  return value ? "Yes" : "No";
}

export function formatList(values) {
  if (!Array.isArray(values) || values.length === 0) return DASH;
  return values
    .map((v) => (v !== null && typeof v === "object" ? JSON.stringify(v) : String(v)))
    .join(", ");
}

export function humanize(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\bid\b/i, "ID")
    .replace(/^./, (c) => c.toUpperCase());
}

/** Generic cell value used by the table when a column has no renderer. */
export function formatValue(value) {
  if (value === null || value === undefined || value === "") return DASH;
  if (typeof value === "boolean") return formatBool(value);
  if (Array.isArray(value)) return formatList(value);
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "string" && ISO_DATE.test(value)) return formatDateTime(value);
  return String(value);
}
