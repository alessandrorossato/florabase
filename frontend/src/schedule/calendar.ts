export function localDay(day = new Date()): string {
  return `${String(day.getFullYear()).padStart(4, "0")}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}

/** Construct local noon from numeric components, never parse a date-only value as UTC. */
export function calendarDate(day: string): Date {
  const [year, month, date] = day.split("-").map(Number);
  const result = new Date(0);
  result.setHours(12, 0, 0, 0);
  result.setFullYear(year, month - 1, date);
  return result;
}
export function validMonth(value: string): boolean {
  return /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(value);
}
export function validDay(value: string): boolean {
  return (
    /^(?!0000)\d{4}-(0[1-9]|1[0-2])-\d{2}$/.test(value) &&
    localDay(calendarDate(value)) === value
  );
}
export function monthDays(month: string): string[] {
  const first = calendarDate(`${month}-01`);
  const days: string[] = [];
  while (localDay(first).startsWith(month)) {
    days.push(localDay(first));
    first.setDate(first.getDate() + 1);
  }
  return days;
}
export function shiftMonth(month: string, delta: number): string {
  const day = calendarDate(`${month}-01`);
  day.setMonth(day.getMonth() + delta);
  return localDay(day).slice(0, 7);
}
export function monthLabel(month: string): string {
  return calendarDate(`${month}-01`).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  });
}
export function dayLabel(day: string): string {
  return calendarDate(day).toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
