import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
import { monthDays } from "./calendar";
import {
  localDay,
  scheduleParams,
  type ScheduleState,
  type TargetKind,
} from "./state";
export type Activity = components["schemas"]["ScheduleResponse"];
export type SchedulePage = components["schemas"]["SchedulePage"];
export type Target = components["schemas"]["ScheduleTargetResponse"];
export type TargetPage = components["schemas"]["ScheduleTargetPage"];
export type ScheduleWrite = components["schemas"]["ScheduleWrite"];
export type ScheduleEvent = components["schemas"]["ScheduleEvent"];
export function listSchedule(
  state: ScheduleState,
  offset = 0,
  limit = 50,
  signal?: AbortSignal,
): Promise<SchedulePage> {
  const p = scheduleParams(state);
  p.set("today", localDay());
  p.set("offset", String(offset));
  p.set("limit", String(limit));
  return requestJson<SchedulePage>(`/api/v1/schedule?${p}`, { signal }).then(
    (page) => {
      if (!Array.isArray(page.items) || typeof page.total !== "number")
        throw new Error("Invalid Schedule response");
      return page;
    },
  );
}
export function getActivity(
  id: string,
  signal?: AbortSignal,
): Promise<Activity> {
  return requestJson(
    `/api/v1/schedule/${encodeURIComponent(id)}?today=${localDay()}`,
    { signal },
  );
}

/** Only the visible month, through the existing capped and ordered list API. */
export async function listCalendar(
  state: ScheduleState,
  signal?: AbortSignal,
): Promise<SchedulePage> {
  const days = monthDays(state.month);
  const p = scheduleParams(state);
  p.set("due_from", days[0] ?? "");
  p.set("due_to", days.at(-1) ?? "");
  p.set("today", localDay());
  p.set("limit", "100");
  const items: Activity[] = [];
  const seen = new Set<string>();
  let first: SchedulePage | undefined;
  for (let offset = 0; offset <= 100000; offset += 100) {
    p.set("offset", String(offset));
    const page = await requestJson<SchedulePage>(`/api/v1/schedule?${p}`, {
      signal,
    });
    if (
      !Array.isArray(page.items) ||
      !Number.isInteger(page.total) ||
      page.total < 0
    )
      throw new Error("Invalid Schedule response");
    first ??= page;
    for (const item of page.items) {
      if (!seen.has(item.id)) {
        seen.add(item.id);
        items.push(item);
      }
    }
    if (offset + 100 >= first.total || !page.items.length)
      return { ...first, items };
  }
  throw new Error("Calendar period exceeds the Schedule paging limit");
}
export function getTarget(
  kind: TargetKind,
  id: string,
  signal?: AbortSignal,
): Promise<Target> {
  return requestJson(
    `/api/v1/schedule/targets/${kind}/${encodeURIComponent(id)}`,
    { signal },
  );
}
export function listTargets(
  kind: TargetKind,
  q: string,
  offset: number,
  signal?: AbortSignal,
): Promise<TargetPage> {
  const p = new URLSearchParams({ q, offset: String(offset), limit: "50" });
  return requestJson(`/api/v1/schedule/targets/${kind}?${p}`, { signal });
}
export function writeActivity(
  id: string | null,
  payload: ScheduleWrite | components["schemas"]["ScheduleUpdate"],
  csrf: string,
): Promise<Activity> {
  return requestJson(
    `/api/v1/schedule${id ? `/${encodeURIComponent(id)}` : ""}?today=${localDay()}`,
    mutation(id ? "PUT" : "POST", payload, csrf),
  );
}
export function transitionActivity(
  item: Activity,
  action: "complete" | "cancel",
  csrf: string,
  event: ScheduleEvent | null = null,
): Promise<Activity> {
  return requestJson(
    `/api/v1/schedule/${item.id}/${action}?today=${localDay()}`,
    mutation(
      "POST",
      {
        expected_version: item.version,
        ...(action === "complete" ? { event } : {}),
      },
      csrf,
    ),
  );
}
function mutation(method: string, payload: unknown, csrf: string): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  };
}
