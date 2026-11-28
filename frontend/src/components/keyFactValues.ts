import type { components } from "../api/schema";

type PartialDate = components["schemas"]["PartialDate"];

/** Whole days from a day-precise date to today (local), or null when the date is coarser. */
export function daysSince(
  date: PartialDate | null | undefined,
  today: Date = new Date(),
): number | null {
  if (date?.precision !== "day" || !date.month || !date.day) return null;
  const start = Date.UTC(date.year, date.month - 1, date.day);
  const end = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.floor((end - start) / 86_400_000);
  return days >= 0 ? days : null;
}

/** "1 day" / "12 days". */
export function daysLabel(days: number): string {
  return `${String(days)} ${days === 1 ? "day" : "days"}`;
}
