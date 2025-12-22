/**
 * Datetime Formatting Helpers
 * ==========================
 *
 * WHAT: Small, dependency-free helpers for formatting dashboard chart labels.
 * WHY: Prevent timezone bugs caused by parsing date-only strings (YYYY-MM-DD) as UTC timestamps.
 *
 * REFERENCES:
 * - ui/app/(dashboard)/dashboard/components/BlendedMetricsModule.jsx (chart axis/tooltip formatting)
 */

/**
 * Check if a value is an ISO date-only string (YYYY-MM-DD).
 *
 * @param {unknown} value
 * @returns {boolean}
 */
export function isIsoDateOnly(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

/**
 * Format a date-only string without timezone shifting.
 *
 * Implementation detail:
 * - We construct a Date at 12:00 UTC to avoid day rollovers when formatting in arbitrary timezones.
 *
 * @param {string} dateOnly - YYYY-MM-DD
 * @param {{ timeZone?: string, options?: Intl.DateTimeFormatOptions }} params
 * @returns {string}
 */
export function formatDateOnlyLabel(
  dateOnly,
  { timeZone = "UTC", options } = {}
) {
  if (!isIsoDateOnly(dateOnly)) return String(dateOnly);
  const [y, m, d] = dateOnly.split("-").map((v) => Number(v));
  if (!y || !m || !d) return String(dateOnly);

  const safeMiddayUtc = new Date(Date.UTC(y, m - 1, d, 12, 0, 0));
  return new Intl.DateTimeFormat("en-US", {
    timeZone,
    month: "short",
    day: "numeric",
    ...(options || {}),
  }).format(safeMiddayUtc);
}

/**
 * Format an ISO timestamp string in a specific timezone.
 *
 * @param {string} isoTimestamp
 * @param {{ timeZone?: string, options?: Intl.DateTimeFormatOptions }} params
 * @returns {string}
 */
export function formatTimestampLabel(
  isoTimestamp,
  { timeZone = "UTC", options } = {}
) {
  const dt = new Date(isoTimestamp);
  if (Number.isNaN(dt.getTime())) return String(isoTimestamp);
  return new Intl.DateTimeFormat("en-US", {
    timeZone,
    ...(options || {}),
  }).format(dt);
}

