/** Turns `counsellor_profiles.availability_schedule` into a readable week.
 *
 *  The column is free-form JSONB. What the Mobile backend actually reads (see
 *  `sessions/service.py::availability` and `counsellor/service.py::_has_bookable_slot`)
 *  is a map keyed by the three-letter day abbreviation Python's `%a` produces —
 *  `{"Mon": [{"label": "09:00 AM", "isAvailable": true}, ...]}` — and it also
 *  tolerates a plain list of labels. Both shapes are handled here, plus a
 *  `{start, end}` pair, because the column has no constraint enforcing any of them.
 *
 *  Nothing is invented: an unreadable label is shown verbatim rather than
 *  dropped or guessed at, and a day with no open slot reads "Not available"
 *  instead of borrowing a neighbouring day's hours.
 */

const WEEK = [
  ["mon", "Monday"],
  ["tue", "Tuesday"],
  ["wed", "Wednesday"],
  ["thu", "Thursday"],
  ["fri", "Friday"],
  ["sat", "Saturday"],
  ["sun", "Sunday"],
];

const DAY_KEYS = new Set(WEEK.map(([key]) => key));

/** Keys the app may store alongside the days. Never rendered as a weekday. */
const TIMEZONE_KEYS = ["timezone", "time_zone", "tz"];
const IGNORED_KEYS = new Set([...TIMEZONE_KEYS, "duration", "duration_minutes", "notes"]);

const TIME_PATTERN = /^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$/;

/** "09:00 AM" / "9 am" / "21:30" -> minutes past midnight; null when unreadable. */
export function parseTimeLabel(value) {
  if (typeof value !== "string") return null;
  const match = value.trim().toUpperCase().match(TIME_PATTERN);
  if (!match) return null;

  let hour = Number(match[1]);
  const minute = match[2] ? Number(match[2]) : 0;
  const meridiem = match[3];
  if (Number.isNaN(hour) || Number.isNaN(minute) || minute > 59) return null;

  if (meridiem) {
    if (hour < 1 || hour > 12) return null;
    hour = (hour % 12) + (meridiem === "PM" ? 12 : 0);
  } else if (hour > 23) {
    return null;
  }
  return hour * 60 + minute;
}

export function formatMinutes(total) {
  const wrapped = ((Math.round(total) % 1440) + 1440) % 1440;
  const hour = Math.floor(wrapped / 60);
  const minute = wrapped % 60;
  const meridiem = hour < 12 ? "AM" : "PM";
  const hour12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${hour12}:${String(minute).padStart(2, "0")} ${meridiem}`;
}

function normalizeDayKey(key) {
  const lower = String(key).trim().toLowerCase();
  const abbreviation = lower.slice(0, 3);
  return DAY_KEYS.has(abbreviation) ? abbreviation : null;
}

/** One published entry -> `{ start, end, raw }`. `start === null` means the
 *  label could not be read and only `raw` is safe to display. */
function readSlot(entry) {
  if (typeof entry === "string") {
    const start = parseTimeLabel(entry);
    return { start, end: null, raw: entry.trim() };
  }
  if (!entry || typeof entry !== "object") return null;

  // The app writes `isAvailable`; the backend treats a missing flag as open.
  const available = entry.isAvailable ?? entry.is_available ?? true;
  if (!available) return null;

  const label = entry.label ?? entry.time ?? entry.start ?? entry.from;
  const start = parseTimeLabel(label);
  const end = parseTimeLabel(entry.end ?? entry.to);
  return {
    start,
    end: start !== null && end !== null && end > start ? end : null,
    raw: typeof label === "string" ? label.trim() : JSON.stringify(entry),
  };
}

/** Slot length to close an open-ended start with. The profile's own
 *  `session_duration_minutes` wins; otherwise the day's own spacing is used, so
 *  hourly slots read as hourly blocks without assuming a house default. */
function slotLength(slots, durationMinutes) {
  if (durationMinutes > 0) return durationMinutes;
  const starts = slots
    .filter((slot) => slot.start !== null)
    .map((slot) => slot.start)
    .sort((a, b) => a - b);
  let step = null;
  for (let i = 1; i < starts.length; i += 1) {
    const gap = starts[i] - starts[i - 1];
    if (gap > 0 && (step === null || gap < step)) step = gap;
  }
  return step;
}

/** Contiguous slots collapse into one range: 9:00, 10:00, 11:00 at 60 min each
 *  is "9:00 AM – 12:00 PM", while a gap starts a new range. */
function buildRanges(slots, durationMinutes) {
  const readable = slots
    .filter((slot) => slot.start !== null)
    .sort((a, b) => a.start - b.start);
  const unreadable = slots.filter((slot) => slot.start === null).map((slot) => slot.raw);

  const step = slotLength(readable, durationMinutes);
  const ranges = [];
  let current = null;

  readable.forEach((slot) => {
    const end = slot.end ?? (step ? slot.start + step : null);
    if (current && current.end !== null && slot.start <= current.end) {
      // Overlapping or back-to-back with the block being built.
      current.end = end === null ? current.end : Math.max(current.end, end);
      return;
    }
    if (current) ranges.push(current);
    current = { start: slot.start, end };
  });
  if (current) ranges.push(current);

  const labels = ranges.map((range) =>
    range.end === null || range.end === range.start
      ? formatMinutes(range.start)
      : `${formatMinutes(range.start)} – ${formatMinutes(range.end)}`
  );

  return [...new Set([...labels, ...unreadable.filter(Boolean)])];
}

function collectSlots(value) {
  const entries = Array.isArray(value) ? value : [value];
  return entries.map(readSlot).filter(Boolean);
}

/**
 * @param {object|null} schedule  `profile.availability_schedule`, as stored.
 * @param {number|null} durationMinutes `profile.session_duration_minutes`.
 * @returns {{hasSchedule: boolean, timezone: string|null,
 *            days: Array<{key: string, label: string, ranges: string[]}>,
 *            extras: Array<{key: string, label: string, ranges: string[]}>}}
 */
export function formatWeeklyAvailability(schedule, durationMinutes) {
  if (!schedule || typeof schedule !== "object" || Array.isArray(schedule)) {
    return { hasSchedule: false, timezone: null, days: [], extras: [] };
  }

  const timezoneKey = TIMEZONE_KEYS.find(
    (key) => typeof schedule[key] === "string" && schedule[key].trim()
  );
  const timezone = timezoneKey ? schedule[timezoneKey].trim() : null;

  const byDay = new Map(WEEK.map(([key]) => [key, []]));
  const extras = [];
  let sawDay = false;

  Object.entries(schedule).forEach(([rawKey, value]) => {
    if (IGNORED_KEYS.has(String(rawKey).trim().toLowerCase())) return;
    const day = normalizeDayKey(rawKey);
    const slots = collectSlots(value);
    if (day) {
      sawDay = true;
      byDay.get(day).push(...slots);
      return;
    }
    // An unrecognised key is still someone's data — surfaced, not swallowed.
    const ranges = buildRanges(slots, durationMinutes);
    if (ranges.length) extras.push({ key: rawKey, label: String(rawKey), ranges });
  });

  const days = WEEK.map(([key, label]) => ({
    key,
    label,
    ranges: buildRanges(byDay.get(key), durationMinutes),
  }));

  // A week whose every slot is switched off is still a published week: it
  // renders as seven "Not available" rows, not as "nothing set".
  const hasSchedule = sawDay || extras.length > 0 || Boolean(timezone);

  return { hasSchedule, timezone, days, extras };
}
