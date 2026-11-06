import type { EventResponse } from "../events/api";

/**
 * Almanac geometry and grouping (Specimen Sheet, M6B). Pure functions only.
 *
 * The axis is a visual summary: a recorded day is a dot, a month-only date spans its month,
 * a year-only date spans its year, and an undated entry is not drawn at all. The lists remain
 * the accessible record of every entry, grouped by the precision that was actually recorded.
 */
export type PartialDate = NonNullable<EventResponse["occurred_on"]>;

const monthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/** Months since year 0, so ranges are simple integer arithmetic. */
const monthIndex = (year: number, month: number) => year * 12 + (month - 1);

export interface AlmanacWindow {
  start: number;
  end: number;
  months: { key: number; label: string; year: number }[];
}

/**
 * At most twelve months covering today and every dated entry, ending with the latest of them;
 * older entries fall outside the axis but remain in the lists. Returns null when nothing is dated.
 */
export function almanacWindow(
  recorded: (PartialDate | null)[],
  planned: string[],
  today: string,
): AlmanacWindow | null {
  const indices: number[] = [];
  for (const date of recorded) {
    if (!date) continue;
    indices.push(
      monthIndex(date.year, date.precision === "year" ? 1 : (date.month ?? 1)),
    );
    if (date.precision === "year") indices.push(monthIndex(date.year, 12));
  }
  for (const day of planned) {
    const [year, month] = day.split("-").map(Number);
    indices.push(monthIndex(year, month));
  }
  if (!indices.length) return null;
  const [ty, tm] = today.split("-").map(Number);
  indices.push(monthIndex(ty, tm));
  const end = Math.max(...indices);
  const start = Math.max(Math.min(...indices), end - 11);
  const months = [];
  for (let key = start; key <= end; key += 1)
    months.push({
      key,
      year: Math.floor(key / 12),
      label: monthNames[key % 12].slice(0, 3),
    });
  return { start, end, months };
}

function daysInMonth(key: number) {
  const year = Math.floor(key / 12);
  return new Date(Date.UTC(year, (key % 12) + 1, 0)).getUTCDate();
}

/** Percent position of a day (YYYY-MM-DD) on the window, or null outside it. */
export function dayPosition(window: AlmanacWindow, day: string): number | null {
  const [year, month, date] = day.split("-").map(Number);
  const key = monthIndex(year, month);
  if (key < window.start || key > window.end) return null;
  const span = window.end - window.start + 1;
  return ((key - window.start + (date - 1) / daysInMonth(key)) / span) * 100;
}

/** A partial date as a mark: a dot for a day, a span for a month or a year (clipped). */
export function partialMark(
  window: AlmanacWindow,
  date: PartialDate,
):
  | { kind: "day"; left: number }
  | { kind: "span"; left: number; width: number }
  | null {
  if (date.precision === "day" && date.month && date.day) {
    const left = dayPosition(
      window,
      `${String(date.year)}-${String(date.month).padStart(2, "0")}-${String(date.day).padStart(2, "0")}`,
    );
    return left === null ? null : { kind: "day", left };
  }
  const first =
    date.precision === "month" && date.month
      ? monthIndex(date.year, date.month)
      : monthIndex(date.year, 1);
  const last =
    date.precision === "month" && date.month
      ? first
      : monthIndex(date.year, 12);
  const from = Math.max(first, window.start);
  const to = Math.min(last, window.end);
  if (from > to) return null;
  const span = window.end - window.start + 1;
  return {
    kind: "span",
    left: ((from - window.start) / span) * 100,
    width: ((to - from + 1) / span) * 100,
  };
}

/**
 * Ledger Folio grouping: consecutive entries that share a recorded period form one group, and
 * the heading says which part of the date was not recorded.
 */
export function precisionGroups<T extends { occurred_on: PartialDate | null }>(
  entries: T[],
): { heading: string; entries: T[] }[] {
  const groups: { heading: string; entries: T[] }[] = [];
  for (const entry of entries) {
    const date = entry.occurred_on;
    const heading = !date
      ? "Date not recorded"
      : date.precision === "year"
        ? `${String(date.year)} · month not recorded`
        : date.precision === "month"
          ? `${monthNames[(date.month ?? 1) - 1]} ${String(date.year)} · day not recorded`
          : `${monthNames[(date.month ?? 1) - 1]} ${String(date.year)}`;
    const last = groups.at(-1);
    if (last?.heading === heading) last.entries.push(entry);
    else groups.push({ heading, entries: [entry] });
  }
  return groups;
}
