import type {
  Activity,
  ScheduleEvent,
  SchedulePage,
  ScheduleWrite,
  Target,
} from "../../schedule/api";
import {
  activityLabels,
  readScheduleState,
  type ActivityKind,
  type TargetKind,
} from "../../schedule/state";
import { validDay } from "../../schedule/calendar";

export const fixtureToday = "2026-10-30";
export const fixtureId = (n: number) =>
  `019a1250-0000-7000-8000-${String(n).padStart(12, "0")}`;
const target = (
  kind: TargetKind,
  n: number,
  label: string,
  lifecycle: string | null = "active",
): Target => ({ kind, id: fixtureId(n), label, lifecycle });
export const fixtureTargets: Target[] = [
  target("plant", 101, "Aloe · nursery plant 04"),
  target("plant_group", 102, "Basil · propagation group B"),
  target("sowing", 103, "Salvia · tray 12"),
  target("seed_lot", 104, "Lavender · packet 07"),
  {
    ...target("botanical_identity", 105, "Ocimum basilicum", null),
    scientific_name: "Ocimum basilicum",
    cultivar_name: "Genovese",
  },
  target("location", 106, "Greenhouse / East bench", null),
  target("plant", 107, "Aloe · transferred plant 02", "transferred"),
];
function activity(
  n: number,
  title: string,
  due: string,
  kind: ActivityKind,
  ref: Target | null,
): Activity {
  return {
    id: fixtureId(n),
    title,
    due_on: due,
    activity_kind: kind,
    target: ref,
    notes:
      "Synthetic planning example. Confirm the actual condition before recording an occurrence.",
    status: "planned",
    version: 1,
    overdue: due < fixtureToday,
    linked_event_id: null,
    completed_at: null,
    cancelled_at: null,
    created_at: "2026-10-20T10:00:00Z",
    updated_at: "2026-10-20T10:00:00Z",
  };
}
export function initialActivities(): Activity[] {
  return [
    activity(1, "Repot nursery aloe", "2026-10-28", "repot", fixtureTargets[0]),
    activity(
      2,
      "Review transferred plant follow-up",
      "2026-10-29",
      "follow_up",
      fixtureTargets[6],
    ),
    activity(
      3,
      "Check Salvia germination",
      fixtureToday,
      "check_germination",
      fixtureTargets[2],
    ),
    activity(
      4,
      "Inspect basil leaf colour",
      fixtureToday,
      "inspect",
      fixtureTargets[1],
    ),
    activity(5, "Water east bench", fixtureToday, "water", fixtureTargets[5]),
    activity(
      6,
      "Review lavender packet",
      fixtureToday,
      "follow_up",
      fixtureTargets[3],
    ),
    activity(
      7,
      "Inspect collection after cold night",
      fixtureToday,
      "inspect",
      null,
    ),
    activity(
      8,
      "Check basil reference notes",
      fixtureToday,
      "follow_up",
      fixtureTargets[4],
    ),
    activity(
      9,
      "Move aloe to winter bench",
      "2026-10-31",
      "move",
      fixtureTargets[0],
    ),
    activity(
      10,
      "Review basil harvest readiness",
      "2026-11-02",
      "harvest",
      fixtureTargets[1],
    ),
    activity(
      11,
      "Fertilize nursery aloe",
      "2026-11-05",
      "fertilize",
      fixtureTargets[0],
    ),
    activity(
      12,
      "Plan next collection inspection",
      "2026-11-20",
      "follow_up",
      null,
    ),
    {
      ...activity(
        13,
        "Review seed storage",
        "2026-10-27",
        "inspect",
        fixtureTargets[3],
      ),
      status: "completed",
      overdue: false,
      completed_at: "2026-10-29T09:00:00Z",
    },
    {
      ...activity(
        14,
        "Inspect basil group",
        "2026-10-25",
        "inspect",
        fixtureTargets[1],
      ),
      status: "completed",
      overdue: false,
      linked_event_id: fixtureId(201),
      completed_at: "2026-10-26T09:00:00Z",
    },
    {
      ...activity(
        15,
        "Water before collection move",
        "2026-10-26",
        "water",
        null,
      ),
      status: "cancelled",
      overdue: false,
      cancelled_at: "2026-10-26T09:00:00Z",
    },
  ];
}
const compatible: Partial<Record<ActivityKind, ScheduleEvent["kind"][]>> = {
  repot: ["repotting"],
  move: ["movement"],
  inspect: ["observation"],
  follow_up: ["observation", "other"],
};
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const failure = (message: string, status = 409) =>
  json({ detail: { message } }, status);

/** Deliberately bounded in-memory simulator, not a replacement for the domain service. */
export class FixtureSchedule {
  items = initialActivities();
  events: { id: string; target: Target; event: ScheduleEvent }[] = [];
  failNext = false;
  conflictNext = false;
  private completions = new Map<string, string>();
  private nextId = 300;

  injectConflict() {
    this.conflictNext = true;
  }
  injectFailure() {
    this.failNext = true;
  }

  fetch: typeof fetch = async (input, init) => {
    await Promise.resolve();
    init?.signal?.throwIfAborted();
    const url = new URL(
      input instanceof Request ? input.url : String(input),
      "http://fixture.invalid",
    );
    const path = url.pathname;
    // Fail closed: no real network request, including unknown APIs.
    if (!path.startsWith("/api/v1/schedule"))
      return failure(
        "No live API is available in this synthetic prototype.",
        503,
      );
    if (this.failNext) {
      this.failNext = false;
      return failure(
        "Injected fixture failure. Your entries are retained.",
        503,
      );
    }
    const parts = path.split("/").filter(Boolean).slice(3);
    if (parts[0] === "targets") {
      const choices = fixtureTargets.filter((t) => t.kind === parts[1]);
      if (parts[2]) return json(choices.find((t) => t.id === parts[2]) ?? null);
      const q = (url.searchParams.get("q") ?? "").toLowerCase();
      const matches = choices.filter((t) => t.label.toLowerCase().includes(q));
      return json({ items: matches, total: matches.length });
    }
    const method = init?.method ?? "GET";
    const item = this.items.find((row) => row.id === parts[0]);
    if (method === "GET") {
      if (parts[0])
        return item
          ? json(item)
          : failure("Synthetic activity not found.", 404);
      const state = readScheduleState(`#/schedule?${url.searchParams}`);
      const offset = Number(url.searchParams.get("offset") ?? 0);
      const limit = Number(url.searchParams.get("limit") ?? 50);
      const matches = this.items
        .filter((row) => {
          const q = state.q.toLowerCase();
          const day = row.due_on;
          return (
            (!state.status.length || state.status.includes(row.status)) &&
            (!state.activity_kind.length ||
              state.activity_kind.includes(row.activity_kind)) &&
            (!state.target_kind.length ||
              (row.target && state.target_kind.includes(row.target.kind))) &&
            (!state.target_id || row.target?.id === state.target_id) &&
            (!q ||
              `${row.title} ${row.notes ?? ""}`.toLowerCase().includes(q)) &&
            (!url.searchParams.get("due_from") ||
              day >= (url.searchParams.get("due_from") ?? "")) &&
            (!url.searchParams.get("due_to") ||
              day <= (url.searchParams.get("due_to") ?? "")) &&
            (state.window === "all" ||
              (state.window === "overdue" &&
                row.status === "planned" &&
                day < fixtureToday) ||
              (state.window === "today" && day === fixtureToday) ||
              (state.window === "next_seven_days" &&
                day > fixtureToday &&
                day <= "2026-11-06") ||
              (state.window === "later" && day > "2026-11-06"))
          );
        })
        .sort(
          (a, b) =>
            a.due_on.localeCompare(b.due_on) || a.id.localeCompare(b.id),
        );
      return json({
        items: matches.slice(offset, offset + limit),
        total: matches.length,
        offset,
        limit,
        today: fixtureToday,
        overdue_count: this.items.filter(
          (r) => r.status === "planned" && r.due_on < fixtureToday,
        ).length,
        today_count: this.items.filter(
          (r) => r.status === "planned" && r.due_on === fixtureToday,
        ).length,
      } satisfies SchedulePage);
    }
    const payload = JSON.parse(
      typeof init?.body === "string" ? init.body : "{}",
    ) as ScheduleWrite & {
      expected_version?: number;
      event?: ScheduleEvent | null;
    };
    const fingerprint = JSON.stringify(payload);
    if (
      item &&
      parts[1] === "complete" &&
      item.status === "completed" &&
      this.completions.get(item.id) === fingerprint
    )
      return json(item);
    if (this.conflictNext && item) {
      item.version++;
      this.conflictNext = false;
    }
    if (
      parts[0] &&
      (item?.status !== "planned" || item.version !== payload.expected_version)
    )
      return failure(
        "Activity changed. Reload the current activity before trying again.",
      );
    if (parts[1] === "cancel" && item) {
      item.status = "cancelled";
      item.cancelled_at = "2026-10-30T10:00:00Z";
    } else if (parts[1] === "complete" && item) {
      const event = payload.event;
      if (event) {
        if (
          !item.target ||
          !["plant", "plant_group"].includes(item.target.kind) ||
          item.target.lifecycle !== "active" ||
          !compatible[item.activity_kind]?.includes(event.kind) ||
          !validDay(event.occurred_on) ||
          (event.kind === "movement") !==
            Boolean(event.destination_location_id) ||
          (event.destination_location_id &&
            !fixtureTargets.some(
              (t) =>
                t.kind === "location" && t.id === event.destination_location_id,
            ))
        )
          return failure("This target or Event is incompatible.");
        const id = fixtureId(this.nextId++);
        this.events.push({ id, target: item.target, event });
        item.linked_event_id = id;
      }
      item.status = "completed";
      item.completed_at = "2026-10-30T10:00:00Z";
      this.completions.set(item.id, fingerprint);
    } else {
      if (
        !validDay(payload.due_on) ||
        !payload.title.trim() ||
        payload.title.length > 255 ||
        !(payload.activity_kind in activityLabels)
      )
        return failure("Use a valid title, kind and complete due day.", 422);
      const ref = payload.target
        ? fixtureTargets.find(
            (t) =>
              t.id === payload.target?.id && t.kind === payload.target.kind,
          )
        : null;
      if (payload.target && !ref)
        return failure("Choose an exact synthetic target.", 422);
      if (
        ref?.lifecycle &&
        ref.lifecycle !== "active" &&
        item?.target?.id !== ref.id
      )
        return failure("Inactive targets cannot be newly assigned.");
      const saved =
        item ??
        activity(
          this.nextId++,
          payload.title,
          payload.due_on,
          payload.activity_kind,
          ref ?? null,
        );
      Object.assign(saved, {
        title: payload.title.trim(),
        activity_kind: payload.activity_kind,
        due_on: payload.due_on,
        notes: payload.notes?.trim() ? payload.notes.trim() : null,
        target: ref ?? null,
      });
      if (!item) {
        this.items.push(saved);
        return json(saved);
      }
    }
    item.version++;
    item.updated_at = "2026-10-30T10:00:00Z";
    item.overdue = item.status === "planned" && item.due_on < fixtureToday;
    return json(item);
  };
}

// Provides only context required by the existing picker. No login/session restoration runs.
export const fixtureAuth: import("../../auth/context").AuthContextValue = {
  state: {
    status: "authenticated",
    session: {
      user_id: fixtureId(999),
      login_name: "synthetic",
      display_name: "Synthetic operator",
      owner: true,
      canonical_origin: "http://fixture.invalid",
    },
    csrfToken: "fixture-only",
  },
  logIn: () => Promise.reject(new Error("No authentication in this prototype")),
  logOut: () =>
    Promise.reject(new Error("No authentication in this prototype")),
  sessionExpired: () => {
    throw new Error("No live session in this prototype");
  },
  retryRestoration: () => {
    throw new Error("No live session in this prototype");
  },
  cancelLogout: () => {
    throw new Error("No live session in this prototype");
  },
};
