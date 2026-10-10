import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
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
