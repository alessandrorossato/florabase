import { requestJson } from "../../auth/api";
import { calendarDate } from "../../schedule/calendar";
import {
  localDay,
  readScheduleState,
  scheduleHash,
  scheduleParams,
  type ScheduleState,
} from "../../schedule/state";
import type { Activity, SchedulePage } from "../../schedule/api";
import { fixtureToday } from "./fixtures";

export type UxView = "agenda" | "week" | "month";
export function shiftDay(day: string, delta: number): string {
  const date = calendarDate(day);
  date.setDate(date.getDate() + delta);
  const value = localDay(date);
  return /^\d{4}-/.test(value) && !value.startsWith("0000") ? value : day;
}
export function weekDays(day: string): string[] {
  const start = shiftDay(day, -((calendarDate(day).getDay() + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => shiftDay(start, i));
}
export function readPrototype() {
  const state = readScheduleState();
  const p = new URLSearchParams(window.location.hash.split("?")[1]);
  const ux: UxView =
    state.view === "calendar"
      ? "month"
      : p.get("ux") === "week"
        ? "week"
        : "agenda";
  return {
    state,
    ux,
    selected: window.location.hash.split("?")[0].split("/")[2] ?? "",
  };
}
export function prototypeHash(state: ScheduleState, ux: UxView, selected = "") {
  const hash = scheduleHash({
    ...state,
    view: ux === "month" ? "calendar" : "list",
  });
  const [path, query = ""] = hash.split("?");
  const p = new URLSearchParams(query);
  if (ux === "week") p.set("ux", "week");
  return `${path}${selected ? `/${selected}` : ""}${p.size ? `?${p}` : ""}`;
}
export function agendaGroups(items: Activity[], selected: string) {
  const groups = new Map<string, Activity[]>();
  groups.set("Overdue", []);
  groups.set(selected, []);
  for (const item of items) {
    const key =
      item.status !== "planned"
        ? item.status === "completed"
          ? "Completed"
          : "Cancelled"
        : item.due_on < fixtureToday && item.due_on !== selected
          ? "Overdue"
          : item.due_on;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return [...groups.entries()].sort(([a], [b]) => {
    const rank = (s: string) => (s === "Overdue" ? 0 : /^\d/.test(s) ? 1 : 2);
    return rank(a) - rank(b) || a.localeCompare(b);
  });
}
export async function loadWeek(
  state: ScheduleState,
  signal: AbortSignal,
): Promise<SchedulePage> {
  const days = weekDays(state.date || fixtureToday);
  const params = scheduleParams(state);
  params.set("due_from", days[0]);
  params.set("due_to", days[6]);
  params.set("today", fixtureToday);
  params.set("limit", "100");
  const items: Activity[] = [];
  let first: SchedulePage | undefined;
  for (let offset = 0; offset <= 100000; offset += 100) {
    params.set("offset", String(offset));
    const page = await requestJson<SchedulePage>(`/api/v1/schedule?${params}`, {
      signal,
    });
    first ??= page;
    items.push(...page.items);
    if (offset + 100 >= first.total || !page.items.length)
      return { ...first, items };
  }
  throw new Error("Week exceeds the existing paging boundary");
}
