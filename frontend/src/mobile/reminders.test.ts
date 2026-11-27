import { describe, expect, it, vi } from "vitest";

import type { ProtectedRequestCapability } from "../auth/api";
import type { Activity, SchedulePage } from "../schedule/api";
import {
  createReminderCoordinator,
  createReminderPreferenceStore,
  REMINDER_PLAN_PREFERENCE_KEY,
  REMINDER_SETTINGS_PREFERENCE_KEY,
  type LocalNotificationsAdapter,
  type ReminderPreferenceStore,
} from "./reminders";
import {
  DEFAULT_REMINDER_SETTINGS,
  REMINDER_ID_BASE,
  type ReminderPlanSummary,
  type ReminderSettings,
} from "./remindersPlan";
import type {
  CapacitorLocalNotificationPayload,
  LocalNotificationPermissionState,
} from "./runtime";

function fakeCapability(authorized = true): ProtectedRequestCapability {
  return {
    isAuthorized: () => authorized,
    subscribeInvalidation: () => () => undefined,
    subscribePermanentRevocation: () => () => undefined,
  } as unknown as ProtectedRequestCapability;
}

function makeActivity(id: string, title: string, due_on: string): Activity {
  return {
    id,
    activity_kind: "water",
    title,
    due_on,
    target: null,
    notes: null,
    status: "planned",
    version: 1,
    overdue: false,
    linked_event_id: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    completed_at: null,
    cancelled_at: null,
  };
}

function makeMemoryStore(
  initial: Partial<ReminderSettings> = {},
): ReminderPreferenceStore & {
  savedPlans: ReminderPlanSummary[];
} {
  let settings: ReminderSettings = {
    ...DEFAULT_REMINDER_SETTINGS,
    ...initial,
  };
  let plan: ReminderPlanSummary | null = null;
  const savedPlans: ReminderPlanSummary[] = [];
  return {
    savedPlans,
    loadSettings: vi.fn(() => Promise.resolve({ ...settings })),
    saveSettings: vi.fn((next: ReminderSettings) => {
      settings = { ...next };
      return Promise.resolve();
    }),
    loadPlanSummary: vi.fn(() => Promise.resolve(plan)),
    savePlanSummary: vi.fn((next: ReminderPlanSummary) => {
      plan = next;
      savedPlans.push(next);
      return Promise.resolve();
    }),
    clearPlanSummary: vi.fn(() => {
      plan = null;
      return Promise.resolve();
    }),
  };
}

function makeFakeAdapter({
  permission = "granted",
  initialPending = [],
  initialDelivered = [],
}: {
  permission?: LocalNotificationPermissionState;
  initialPending?: number[];
  initialDelivered?: { id: number; tag?: string }[];
} = {}) {
  let currentPermission: LocalNotificationPermissionState = permission;
  const pending = new Map<number, CapacitorLocalNotificationPayload | null>(
    initialPending.map((id) => [id, null]),
  );
  let delivered = [...initialDelivered];
  const ops: string[] = [];

  const adapter: LocalNotificationsAdapter = {
    checkPermissions: vi.fn(() => Promise.resolve(currentPermission)),
    requestPermissions: vi.fn(() => Promise.resolve(currentPermission)),
    ensureChannel: vi.fn(() => {
      ops.push("ensureChannel");
      return Promise.resolve();
    }),
    getPendingIds: vi.fn(() => {
      ops.push("getPending");
      return Promise.resolve([...pending.keys()]);
    }),
    cancelIds: vi.fn((ids: number[]) => {
      ops.push(`cancel:${ids.join(",")}`);
      for (const id of ids) {
        pending.delete(id);
      }
      return Promise.resolve();
    }),
    getDelivered: vi.fn(() => {
      ops.push("getDelivered");
      return Promise.resolve([...delivered]);
    }),
    removeDelivered: vi.fn((items: { id: number; tag?: string }[]) => {
      ops.push(`removeDelivered:${items.map((i) => i.id).join(",")}`);
      const removeSet = new Set(items.map((i) => i.id));
      delivered = delivered.filter((item) => !removeSet.has(item.id));
      return Promise.resolve();
    }),
    schedule: vi.fn((notifications: CapacitorLocalNotificationPayload[]) => {
      ops.push(`schedule:${notifications.map((n) => n.id).join(",")}`);
      for (const n of notifications) {
        pending.set(n.id, n);
      }
      return Promise.resolve();
    }),
  };

  return {
    adapter,
    ops,
    setPermission(next: LocalNotificationPermissionState) {
      currentPermission = next;
    },
    getPendingMap() {
      return pending;
    },
    getDeliveredList() {
      return delivered;
    },
  };
}

describe("reminders coordinator", () => {
  it("cancels and replaces ONLY owned IDs (41000..41099) and never touches unrelated notifications", async () => {
    const store = makeMemoryStore({ enabled: true, time: "08:00" });
    const fake = makeFakeAdapter({
      permission: "granted",
      initialPending: [7, REMINDER_ID_BASE + 5, 50_000],
      initialDelivered: [{ id: 99 }, { id: REMINDER_ID_BASE + 2 }],
    });
    const fetchPage = vi.fn((): Promise<SchedulePage> =>
      Promise.resolve({
        items: [
          makeActivity(
            "00000000-0000-4000-8000-000000000001",
            "Water ferns",
            "2026-05-01",
          ),
        ],
        total: 1,
        offset: 0,
        limit: 100,
        today: "2026-05-01",
        overdue_count: 0,
        today_count: 1,
      }),
    );

    const coordinator = createReminderCoordinator({
      store,
      adapter: fake.adapter,
      fetchSchedulePage: fetchPage,
      nowProvider: () => new Date("2026-05-01T06:00:00Z"),
      timeZoneProvider: () => "UTC",
    });

    const result = await coordinator.syncNow(fakeCapability(true));
    expect(result).toEqual({ status: "scheduled", scheduledCount: 1 });
    expect(fake.adapter.cancelIds).toHaveBeenCalledWith([REMINDER_ID_BASE + 5]);
    // Unrelated pending IDs 7 and 50_000 remain untouched
    expect([...fake.getPendingMap().keys()].sort((a, b) => a - b)).toEqual([
      7,
      REMINDER_ID_BASE,
      50_000,
    ]);

    // Running twice in a row gives the exact same pending set
    await coordinator.syncNow(fakeCapability(true));
    expect([...fake.getPendingMap().keys()].sort((a, b) => a - b)).toEqual([
      7,
      REMINDER_ID_BASE,
      50_000,
    ]);

    // Trust loss cancels pending AND delivered ONLY in 41000..41099
    await coordinator.clearOnTrustLoss();
    expect([...fake.getPendingMap().keys()].sort((a, b) => a - b)).toEqual([
      7, 50_000,
    ]);
    expect(fake.getDeliveredList()).toEqual([{ id: 99 }]);
    expect(store.clearPlanSummary).toHaveBeenCalled();
  });

  it("serialises concurrent recomputes so getPending -> cancel -> schedule never interleaves and last call wins", async () => {
    const store = makeMemoryStore({ enabled: true, time: "08:00" });
    const fake = makeFakeAdapter({
      permission: "granted",
      initialPending: [REMINDER_ID_BASE],
    });

    let resolveFirstFetch: ((page: SchedulePage) => void) | null = null;
    let fetchCount = 0;
    const fetchPage = vi.fn((): Promise<SchedulePage> => {
      fetchCount += 1;
      if (fetchCount === 1) {
        return new Promise<SchedulePage>((resolve) => {
          resolveFirstFetch = resolve;
        });
      }
      // Second call returns updated schedule (2 items due tomorrow, none today)
      return Promise.resolve({
        items: [
          makeActivity(
            "00000000-0000-4000-8000-000000000010",
            "Latest task A",
            "2026-05-02",
          ),
          makeActivity(
            "00000000-0000-4000-8000-000000000011",
            "Latest task B",
            "2026-05-02",
          ),
        ],
        total: 2,
        offset: 0,
        limit: 100,
        today: "2026-05-01",
        overdue_count: 0,
        today_count: 0,
      });
    });

    // Track strict non-interleaving of getPending -> cancel -> schedule
    let inCriticalSection = false;
    let interleaved = false;
    const origGetPending = fake.adapter.getPendingIds;
    const origSchedule = fake.adapter.schedule;
    fake.adapter.getPendingIds = vi.fn(async () => {
      if (inCriticalSection) interleaved = true;
      inCriticalSection = true;
      return await origGetPending();
    });
    fake.adapter.schedule = vi.fn(
      async (list: CapacitorLocalNotificationPayload[]) => {
        await origSchedule(list);
        inCriticalSection = false;
      },
    );

    const coordinator = createReminderCoordinator({
      store,
      adapter: fake.adapter,
      fetchSchedulePage: fetchPage,
      nowProvider: () => new Date("2026-05-01T06:00:00Z"),
      timeZoneProvider: () => "UTC",
    });

    const firstPromise = coordinator.syncNow(fakeCapability(true));
    const secondPromise = coordinator.syncNow(fakeCapability(true));

    // Resolve the first slow fetch while the second recompute is queued
    await vi.waitFor(() => {
      expect(resolveFirstFetch).not.toBeNull();
    });
    (resolveFirstFetch as ((page: SchedulePage) => void) | null)?.({
      items: [
        makeActivity(
          "00000000-0000-4000-8000-000000000001",
          "Stale task",
          "2026-05-01",
        ),
      ],
      total: 1,
      offset: 0,
      limit: 100,
      today: "2026-05-01",
      overdue_count: 0,
      today_count: 1,
    });

    const [firstResult, secondResult] = await Promise.all([
      firstPromise,
      secondPromise,
    ]);

    expect(interleaved).toBe(false);
    expect(fetchPage).toHaveBeenCalledTimes(2);
    expect(firstResult.status).toBe("scheduled");
    expect(secondResult).toEqual({ status: "scheduled", scheduledCount: 1 });
    // Last call wins: final pending notification is day +1 ("2 activities due today"), not stale day 0
    expect([...fake.getPendingMap().keys()]).toEqual([REMINDER_ID_BASE + 1]);
    expect(fake.getPendingMap().get(REMINDER_ID_BASE + 1)?.title).toBe(
      "2 activities due today",
    );
  });

  it("never prompts during syncNow and stops scheduling if permission is revoked later", async () => {
    const store = makeMemoryStore({ enabled: true, time: "08:00" });
    const fake = makeFakeAdapter({
      permission: "denied",
      initialPending: [REMINDER_ID_BASE],
    });
    const fetchPage = vi.fn();

    const coordinator = createReminderCoordinator({
      store,
      adapter: fake.adapter,
      fetchSchedulePage: fetchPage,
    });

    const result = await coordinator.syncNow(fakeCapability(true));
    expect(result).toEqual({ status: "permission-denied", scheduledCount: 0 });
    expect(fake.adapter.requestPermissions).not.toHaveBeenCalled();
    expect(fake.adapter.schedule).not.toHaveBeenCalled();
    expect(fetchPage).not.toHaveBeenCalled();
    expect(coordinator.getSnapshot().permission).toBe("denied");
    expect([...fake.getPendingMap().keys()]).toEqual([]);
  });

  it("requests permission ONLY in enableWithPermission and cancels pending+delivered on disable", async () => {
    const store = makeMemoryStore({ enabled: false, time: "08:00" });
    const fake = makeFakeAdapter({
      permission: "denied",
      initialPending: [REMINDER_ID_BASE],
      initialDelivered: [{ id: REMINDER_ID_BASE }],
    });
    const fetchPage = vi.fn((): Promise<SchedulePage> =>
      Promise.resolve({
        items: [
          makeActivity(
            "00000000-0000-4000-8000-000000000001",
            "Water citrus",
            "2026-05-01",
          ),
        ],
        total: 1,
        offset: 0,
        limit: 100,
        today: "2026-05-01",
        overdue_count: 0,
        today_count: 1,
      }),
    );

    const coordinator = createReminderCoordinator({
      store,
      adapter: fake.adapter,
      fetchSchedulePage: fetchPage,
      nowProvider: () => new Date("2026-05-01T06:00:00Z"),
      timeZoneProvider: () => "UTC",
    });

    // Denied opt-in keeps enabled=false
    const deniedOutcome = await coordinator.enableWithPermission(
      { time: "08:30", includeOverdue: true },
      fakeCapability(true),
    );
    expect(deniedOutcome).toEqual({ granted: false, permission: "denied" });
    expect(fake.adapter.requestPermissions).toHaveBeenCalledTimes(1);
    expect(coordinator.getSnapshot().settings.enabled).toBe(false);
    expect(fake.adapter.schedule).not.toHaveBeenCalled();

    // Granted opt-in enables and schedules
    fake.setPermission("granted");
    const grantedOutcome = await coordinator.enableWithPermission(
      { time: "08:30", includeOverdue: true },
      fakeCapability(true),
    );
    expect(grantedOutcome).toEqual({ granted: true, permission: "granted" });
    expect(coordinator.getSnapshot().settings.enabled).toBe(true);
    expect(fake.adapter.schedule).toHaveBeenCalledTimes(1);

    // Switching off cancels pending AND delivered owned notifications
    await coordinator.disable();
    expect(coordinator.getSnapshot().settings.enabled).toBe(false);
    expect([...fake.getPendingMap().keys()]).toEqual([]);
    expect(fake.getDeliveredList()).toEqual([]);
  });

  it("persists settings and minimal plan summary (counts only, zero titles) in Capacitor Preferences", async () => {
    const kv = new Map<string, string>();
    const fakeGlobal = {
      Capacitor: {
        Plugins: {
          Preferences: {
            get: ({ key }: { key: string }) =>
              Promise.resolve({ value: kv.get(key) ?? null }),
            set: ({ key, value }: { key: string; value: string }) => {
              kv.set(key, value);
              return Promise.resolve();
            },
            remove: ({ key }: { key: string }) => {
              kv.delete(key);
              return Promise.resolve();
            },
          },
        },
      },
    } as unknown as typeof globalThis;

    const store = createReminderPreferenceStore(fakeGlobal);
    await store.saveSettings({
      enabled: true,
      time: "07:45",
      includeOverdue: false,
    });
    expect(await store.loadSettings()).toEqual({
      enabled: true,
      time: "07:45",
      includeOverdue: false,
    });
    expect(kv.has(REMINDER_SETTINGS_PREFERENCE_KEY)).toBe(true);

    // Even if extra fields were passed at runtime, savePlanSummary strips them
    await store.savePlanSummary({
      updatedAt: "2026-05-01T06:00:00.000Z",
      timeZone: "Europe/Rome",
      days: [
        {
          date: "2026-05-01",
          dueCount: 2,
          overdueCount: 1,
          ...({ titles: ["Should never persist"] } as Record<string, unknown>),
        },
      ],
    });
    const persisted = kv.get(REMINDER_PLAN_PREFERENCE_KEY) ?? "";
    expect(persisted).not.toContain("Should never persist");
    expect(await store.loadPlanSummary()).toEqual({
      updatedAt: "2026-05-01T06:00:00.000Z",
      timeZone: "Europe/Rome",
      days: [{ date: "2026-05-01", dueCount: 2, overdueCount: 1 }],
    });
  });
});
