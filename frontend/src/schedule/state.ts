import type { Activity } from "./api";
import { localDay, validDay, validMonth } from "./calendar";
export { localDay } from "./calendar";

export const activityLabels = {
  repot: "Repot",
  water: "Water",
  fertilize: "Fertilize",
  move: "Move / relocate",
  check_germination: "Check germination",
  inspect: "Inspect",
  harvest: "Harvest",
  follow_up: "General follow-up",
} as const;
export const targetLabels = {
  botanical_identity: "Botanical identity",
  seed_lot: "Seed lot",
  sowing: "Sowing",
  plant: "Plant",
  plant_group: "Plant group",
  location: "Location",
} as const;
export const windowLabels = {
  all: "All dates",
  overdue: "Overdue",
  today: "Today",
  next_seven_days: "Next 7 days",
  later: "Later",
} as const;
export type ActivityKind = keyof typeof activityLabels;
export type TargetKind = keyof typeof targetLabels;
export type DateWindow = keyof typeof windowLabels;
export interface ScheduleState {
  view: "list" | "calendar";
  month: string;
  date: string;
  status: "planned" | "completed" | "cancelled";
  window: DateWindow;
  activity_kind: ActivityKind | "";
  target_kind: TargetKind | "";
  target_id: string;
  q: string;
}
export const defaultState: ScheduleState = {
  view: "list",
  month: localDay().slice(0, 7),
  date: "",
  status: "planned",
  window: "all",
  activity_kind: "",
  target_kind: "",
  target_id: "",
  q: "",
};
export function readScheduleState(hash = window.location.hash): ScheduleState {
  const [path, query = ""] = hash.split("?", 2);
  const p = new URLSearchParams(path.startsWith("#/schedule") ? query : "");
  const status = p.get("status");
  const window = p.get("window") ?? "all";
  const kind = p.get("activity_kind") ?? "";
  const target = p.get("target_kind") ?? "";
  const id = p.get("target_id") ?? "";
  const month = p.get("month") ?? "";
  const selected = p.get("date") ?? "";
  const period = validMonth(month) ? month : localDay().slice(0, 7);
  return {
    view: p.get("view") === "calendar" ? "calendar" : "list",
    month: period,
    date: validDay(selected) && selected.startsWith(period) ? selected : "",
    status:
      status === "completed" || status === "cancelled" ? status : "planned",
    window: Object.hasOwn(windowLabels, window)
      ? (window as DateWindow)
      : "all",
    activity_kind: Object.hasOwn(activityLabels, kind)
      ? (kind as ActivityKind)
      : "",
    target_kind: Object.hasOwn(targetLabels, target)
      ? (target as TargetKind)
      : "",
    target_id:
      Object.hasOwn(targetLabels, target) &&
      /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i.test(id)
        ? id.toLowerCase()
        : "",
    q: (p.get("q") ?? "").trim().slice(0, 200),
  };
}
export function scheduleParams(state: ScheduleState): URLSearchParams {
  const p = new URLSearchParams();
  if (state.status !== "planned") p.set("status", state.status);
  if (state.window !== "all") p.set("window", state.window);
  if (state.activity_kind) p.set("activity_kind", state.activity_kind);
  if (state.target_kind) {
    p.set("target_kind", state.target_kind);
    if (state.target_id) p.set("target_id", state.target_id);
  }
  if (state.q.trim()) p.set("q", state.q.trim());
  return p;
}
export function scheduleHash(state: ScheduleState): string {
  const p = scheduleParams(state);
  if (state.view === "calendar") {
    p.set("view", "calendar");
    p.set("month", state.month);
    if (state.date) p.set("date", state.date);
  }
  return `#/schedule${p.size ? `?${p}` : ""}`;
}
export function targetHref(target: { kind: TargetKind; id: string }): string {
  const routes = {
    botanical_identity: "identities",
    seed_lot: "seeds",
    sowing: "sowings",
    plant: "plants",
    plant_group: "plant-groups",
    location: "locations",
  };
  return `#/${routes[target.kind]}/${target.id}`;
}

export function activityState(item: Activity, today: string): string {
  if (item.status === "completed") return "Completed";
  if (item.status === "cancelled") return "Cancelled";
  if (item.due_on < today) return "Planned · Overdue";
  if (item.due_on === today) return "Planned · Due today";
  return "Planned";
}
