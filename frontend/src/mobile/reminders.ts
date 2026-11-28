/**
 * Native Android Schedule reminders coordinator, Preferences persistence, and
 * Capacitor LocalNotifications/App bridge wrappers.
 *
 * Reached exclusively through `window.Capacitor` (zero `@capacitor/*` imports in
 * `frontend/package.json`) and lazily loaded only when `isNativeShell()` is true.
 */

import {
  isExpectedAuthCancellation,
  requestJson,
  type ProtectedRequestCapability,
} from "../auth/api";
import type { SchedulePage } from "../schedule/api";
import {
  addCalendarDays,
  buildReminderPlan,
  DEFAULT_REMINDER_SETTINGS,
  getDeviceTimeZone,
  getLocalDayInTimeZone,
  isOwnedReminderId,
  normalizeReminderSettings,
  REMINDER_CHANNEL_DESCRIPTION,
  REMINDER_CHANNEL_ID,
  REMINDER_CHANNEL_NAME,
  REMINDER_HORIZON_DAYS,
  validateReminderRoute,
  type ReminderPlanSummary,
  type ReminderSettings,
} from "./remindersPlan";
import {
  getCapacitorGlobal,
  type CapacitorGlobal,
  type CapacitorLocalNotificationActionPerformed,
  type CapacitorLocalNotificationPayload,
  type CapacitorLocalNotificationsBridge,
  type CapacitorPluginListenerHandle,
  type LocalNotificationPermissionState,
} from "./runtime";

export const REMINDER_SETTINGS_PREFERENCE_KEY = "florabase.reminders.settings";
export const REMINDER_PLAN_PREFERENCE_KEY = "florabase.reminders.plan";

const CHANNEL_IMPORTANCE_DEFAULT = 3;
const CHANNEL_VISIBILITY_PRIVATE = 0;

export interface ReminderPreferenceStore {
  loadSettings: () => Promise<ReminderSettings>;
  saveSettings: (settings: ReminderSettings) => Promise<void>;
  loadPlanSummary: () => Promise<ReminderPlanSummary | null>;
  savePlanSummary: (summary: ReminderPlanSummary) => Promise<void>;
  clearPlanSummary: () => Promise<void>;
}

export interface LocalNotificationsAdapter {
  checkPermissions: () => Promise<LocalNotificationPermissionState>;
  requestPermissions: () => Promise<LocalNotificationPermissionState>;
  ensureChannel: () => Promise<void>;
  getPendingIds: () => Promise<number[]>;
  cancelIds: (ids: number[]) => Promise<void>;
  getDelivered: () => Promise<{ id: number; tag?: string }[]>;
  removeDelivered: (items: { id: number; tag?: string }[]) => Promise<void>;
  schedule: (
    notifications: CapacitorLocalNotificationPayload[],
  ) => Promise<void>;
}

export type SchedulePageFetcher = (
  params: { today: string; dueFrom: string; dueTo: string },
  capability: ProtectedRequestCapability,
) => Promise<SchedulePage>;

export interface ReminderSnapshot {
  settings: ReminderSettings;
  permission: LocalNotificationPermissionState | "unknown";
  plan: ReminderPlanSummary | null;
  syncing: boolean;
  error: string | null;
}

export interface ReminderSyncResult {
  status:
    | "scheduled"
    | "disabled"
    | "permission-denied"
    | "unauthenticated"
    | "error";
  scheduledCount: number;
}

export interface ReminderCoordinator {
  getSnapshot: () => ReminderSnapshot;
  subscribe: (listener: () => void) => () => void;
  refreshState: () => Promise<ReminderSnapshot>;
  syncNow: (
    capability: ProtectedRequestCapability | null,
    options?: { now?: Date; timeZone?: string },
  ) => Promise<ReminderSyncResult>;
  enableWithPermission: (
    nextSettings: Omit<ReminderSettings, "enabled">,
    capability: ProtectedRequestCapability | null,
  ) => Promise<{
    granted: boolean;
    permission: LocalNotificationPermissionState;
  }>;
  disable: () => Promise<void>;
  updateSettings: (
    nextSettings: ReminderSettings,
    capability: ProtectedRequestCapability | null,
  ) => Promise<ReminderSyncResult>;
  clearOnTrustLoss: () => Promise<void>;
}

function parsePlanSummary(raw: string | null): ReminderPlanSummary | null {
  if (raw === null || raw === "") return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      return null;
    }
    const record = parsed as Record<string, unknown>;
    if (
      typeof record.updatedAt !== "string" ||
      typeof record.timeZone !== "string" ||
      !Array.isArray(record.days)
    ) {
      return null;
    }
    const days = record.days
      .filter(
        (entry): entry is Record<string, unknown> =>
          typeof entry === "object" && entry !== null && !Array.isArray(entry),
      )
      .filter(
        (entry) =>
          typeof entry.date === "string" &&
          typeof entry.dueCount === "number" &&
          typeof entry.overdueCount === "number",
      )
      .map((entry) => ({
        date: entry.date as string,
        dueCount: entry.dueCount as number,
        overdueCount: entry.overdueCount as number,
      }));
    return {
      updatedAt: record.updatedAt,
      timeZone: record.timeZone,
      days,
    };
  } catch {
    return null;
  }
}

interface RawKeyValueStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
}

function createRawPreferenceStore(
  capacitor: CapacitorGlobal | undefined,
): RawKeyValueStore {
  const plugin = capacitor?.Plugins?.Preferences;
  if (plugin !== undefined) {
    return {
      async get(key) {
        const result = await plugin.get({ key });
        return typeof result.value === "string" ? result.value : null;
      },
      async set(key, value) {
        await plugin.set({ key, value });
      },
      async remove(key) {
        await plugin.remove({ key });
      },
    };
  }
  const nativePromise = capacitor?.nativePromise;
  if (typeof nativePromise === "function") {
    return {
      async get(key) {
        const result = await nativePromise<{ value?: string | null }>(
          "Preferences",
          "get",
          { key },
        );
        return typeof result.value === "string" ? result.value : null;
      },
      async set(key, value) {
        await nativePromise("Preferences", "set", { key, value });
      },
      async remove(key) {
        await nativePromise("Preferences", "remove", { key });
      },
    };
  }
  const memory = new Map<string, string>();
  return {
    get(key) {
      return Promise.resolve(memory.get(key) ?? null);
    },
    set(key, value) {
      memory.set(key, value);
      return Promise.resolve();
    },
    remove(key) {
      memory.delete(key);
      return Promise.resolve();
    },
  };
}

export function createReminderPreferenceStore(
  target: typeof globalThis = globalThis,
): ReminderPreferenceStore {
  const raw = createRawPreferenceStore(getCapacitorGlobal(target));
  return {
    async loadSettings() {
      const value = await raw.get(REMINDER_SETTINGS_PREFERENCE_KEY);
      if (value === null || value === "") {
        return { ...DEFAULT_REMINDER_SETTINGS };
      }
      try {
        return normalizeReminderSettings(JSON.parse(value) as unknown);
      } catch {
        return { ...DEFAULT_REMINDER_SETTINGS };
      }
    },
    async saveSettings(settings) {
      const normalized = normalizeReminderSettings(settings);
      await raw.set(
        REMINDER_SETTINGS_PREFERENCE_KEY,
        JSON.stringify(normalized),
      );
    },
    async loadPlanSummary() {
      const value = await raw.get(REMINDER_PLAN_PREFERENCE_KEY);
      return parsePlanSummary(value);
    },
    async savePlanSummary(summary) {
      // Explicitly project only updatedAt, timeZone, and per-day counts — never titles.
      const minimal: ReminderPlanSummary = {
        updatedAt: summary.updatedAt,
        timeZone: summary.timeZone,
        days: summary.days.map((day) => ({
          date: day.date,
          dueCount: day.dueCount,
          overdueCount: day.overdueCount,
        })),
      };
      await raw.set(REMINDER_PLAN_PREFERENCE_KEY, JSON.stringify(minimal));
    },
    async clearPlanSummary() {
      await raw.remove(REMINDER_PLAN_PREFERENCE_KEY);
    },
  };
}

function getLocalNotificationsPlugin(
  target: typeof globalThis = globalThis,
): CapacitorLocalNotificationsBridge | null {
  const capacitor = getCapacitorGlobal(target);
  return capacitor?.Plugins?.LocalNotifications ?? null;
}

export function createLocalNotificationsAdapter(
  target: typeof globalThis = globalThis,
): LocalNotificationsAdapter | null {
  const plugin = getLocalNotificationsPlugin(target);
  if (plugin === null) {
    return null;
  }
  let channelReady = false;
  return {
    async checkPermissions() {
      const result = await plugin.checkPermissions();
      return result.display;
    },
    async requestPermissions() {
      const result = await plugin.requestPermissions();
      return result.display;
    },
    async ensureChannel() {
      if (channelReady) return;
      await plugin.createChannel({
        id: REMINDER_CHANNEL_ID,
        name: REMINDER_CHANNEL_NAME,
        description: REMINDER_CHANNEL_DESCRIPTION,
        importance: CHANNEL_IMPORTANCE_DEFAULT,
        visibility: CHANNEL_VISIBILITY_PRIVATE,
        vibration: true,
      });
      channelReady = true;
    },
    async getPendingIds() {
      const result = await plugin.getPending();
      return (result.notifications ?? [])
        .map((item) => item.id)
        .filter((id): id is number => typeof id === "number");
    },
    async cancelIds(ids) {
      if (ids.length === 0) return;
      await plugin.cancel({
        notifications: ids.map((id) => ({ id })),
      });
    },
    async getDelivered() {
      const result = await plugin.getDeliveredNotifications();
      return (result.notifications ?? [])
        .filter((item) => typeof item.id === "number")
        .map((item) => ({ id: item.id, tag: item.tag }));
    },
    async removeDelivered(items) {
      if (items.length === 0) return;
      if (typeof plugin.removeDeliveredNotificationsById === "function") {
        await plugin.removeDeliveredNotificationsById({
          ids: items.map((item) => item.id),
        });
        return;
      }
      if (typeof plugin.removeDeliveredNotifications === "function") {
        await plugin.removeDeliveredNotifications({
          notifications: items,
        });
      }
    },
    async schedule(notifications) {
      if (notifications.length === 0) return;
      await plugin.schedule({ notifications });
    },
  };
}

async function clearOwnedReminders(
  adapter: LocalNotificationsAdapter | null,
  { includeDelivered }: { includeDelivered: boolean },
): Promise<void> {
  if (adapter === null) return;
  try {
    const pendingIds = await adapter.getPendingIds();
    const ownedPending = pendingIds.filter(isOwnedReminderId);
    if (ownedPending.length > 0) {
      await adapter.cancelIds(ownedPending);
    }
  } catch {
    // Best-effort pending cancellation.
  }
  if (includeDelivered) {
    try {
      const delivered = await adapter.getDelivered();
      const ownedDelivered = delivered.filter((item) =>
        isOwnedReminderId(item.id),
      );
      if (ownedDelivered.length > 0) {
        await adapter.removeDelivered(ownedDelivered);
      }
    } catch {
      // Best-effort delivered removal.
    }
  }
}

export const defaultSchedulePageFetcher: SchedulePageFetcher = (
  { today, dueFrom, dueTo },
  capability,
) => {
  const params = new URLSearchParams({
    status: "planned",
    due_from: dueFrom,
    due_to: dueTo,
    today,
    offset: "0",
    limit: "100",
  });
  return requestJson<SchedulePage>(`/api/v1/schedule?${params.toString()}`, {
    capability,
  });
};

export function createReminderCoordinator({
  store,
  adapter,
  fetchSchedulePage = defaultSchedulePageFetcher,
  nowProvider = () => new Date(),
  timeZoneProvider = getDeviceTimeZone,
}: {
  store?: ReminderPreferenceStore;
  adapter?: LocalNotificationsAdapter | null;
  fetchSchedulePage?: SchedulePageFetcher;
  nowProvider?: () => Date;
  timeZoneProvider?: () => string;
} = {}): ReminderCoordinator {
  const resolvedStore = store ?? createReminderPreferenceStore();
  const resolvedAdapter =
    adapter !== undefined ? adapter : createLocalNotificationsAdapter();

  let snapshot: ReminderSnapshot = {
    settings: { ...DEFAULT_REMINDER_SETTINGS },
    permission: "unknown",
    plan: null,
    syncing: false,
    error: null,
  };
  const listeners = new Set<() => void>();

  function emit(patch: Partial<ReminderSnapshot>): void {
    snapshot = { ...snapshot, ...patch };
    for (const listener of [...listeners]) {
      try {
        listener();
      } catch {
        // Never allow UI listener errors to break scheduling serialization.
      }
    }
  }

  // Serialized queue + coalesced pending sync so start/resume/mutation/settings
  // never interleave `getPending -> cancel -> schedule`, and the last call wins.
  let queueTail: Promise<void> = Promise.resolve();
  let syncInFlight = false;
  let queuedSyncRequest: {
    capability: ProtectedRequestCapability | null;
    now?: Date;
    timeZone?: string;
    waiters: ((result: ReminderSyncResult) => void)[];
  } | null = null;
  let activeSyncPromise: Promise<ReminderSyncResult> | null = null;

  function enqueueExclusive<T>(task: () => Promise<T>): Promise<T> {
    const run = queueTail.then(task, task);
    queueTail = run.then(
      () => undefined,
      () => undefined,
    );
    return run;
  }

  function discardQueuedSync(result: ReminderSyncResult): void {
    if (queuedSyncRequest !== null) {
      const waiters = queuedSyncRequest.waiters;
      queuedSyncRequest = null;
      for (const resolve of waiters) {
        resolve(result);
      }
    }
  }

  async function runSingleSyncPass(
    capability: ProtectedRequestCapability | null,
    options?: { now?: Date; timeZone?: string },
  ): Promise<ReminderSyncResult> {
    emit({ syncing: true, error: null });
    try {
      const settings = await resolvedStore.loadSettings();
      const existingPlan = await resolvedStore.loadPlanSummary();
      emit({ settings, plan: existingPlan });

      if (!settings.enabled) {
        await clearOwnedReminders(resolvedAdapter, { includeDelivered: true });
        await resolvedStore.clearPlanSummary();
        emit({ plan: null, syncing: false, error: null });
        return { status: "disabled", scheduledCount: 0 };
      }

      if (resolvedAdapter === null) {
        emit({ syncing: false });
        return { status: "error", scheduledCount: 0 };
      }

      // Always check permission BEFORE schedule(): plugin 8.3.x schedule() would
      // otherwise trigger a system prompt outside the user toggle.
      const permission = await resolvedAdapter.checkPermissions();
      emit({ permission });
      if (permission !== "granted") {
        await clearOwnedReminders(resolvedAdapter, { includeDelivered: false });
        await resolvedStore.clearPlanSummary();
        emit({ plan: null, syncing: false, error: null });
        return { status: "permission-denied", scheduledCount: 0 };
      }

      if (!capability?.isAuthorized()) {
        emit({ syncing: false });
        return { status: "unauthenticated", scheduledCount: 0 };
      }

      const now = options?.now ?? nowProvider();
      const timeZone = options?.timeZone ?? timeZoneProvider();
      const today = getLocalDayInTimeZone(now, timeZone);
      const dueTo = addCalendarDays(today, REMINDER_HORIZON_DAYS - 1);

      const page = await fetchSchedulePage(
        { today, dueFrom: today, dueTo },
        capability,
      );

      // Re-check settings & authorization after async fetch in case the user
      // disabled reminders or logged out while the network request was in flight.
      const latestSettings = await resolvedStore.loadSettings();
      if (!latestSettings.enabled) {
        await clearOwnedReminders(resolvedAdapter, { includeDelivered: true });
        await resolvedStore.clearPlanSummary();
        emit({ settings: latestSettings, plan: null, syncing: false });
        return { status: "disabled", scheduledCount: 0 };
      }
      if (!capability.isAuthorized()) {
        emit({ syncing: false });
        return { status: "unauthenticated", scheduledCount: 0 };
      }

      const latestPermission = await resolvedAdapter.checkPermissions();
      emit({ permission: latestPermission });
      if (latestPermission !== "granted") {
        await clearOwnedReminders(resolvedAdapter, { includeDelivered: false });
        await resolvedStore.clearPlanSummary();
        emit({ plan: null, syncing: false });
        return { status: "permission-denied", scheduledCount: 0 };
      }

      const plan = buildReminderPlan(page, latestSettings, {
        now,
        timeZone,
        horizonDays: REMINDER_HORIZON_DAYS,
      });

      await resolvedAdapter.ensureChannel();
      await clearOwnedReminders(resolvedAdapter, { includeDelivered: false });
      if (plan.notifications.length > 0) {
        await resolvedAdapter.schedule(plan.notifications);
      }
      await resolvedStore.savePlanSummary(plan.summary);
      emit({
        settings: latestSettings,
        plan: plan.summary,
        syncing: false,
        error: null,
      });
      return {
        status: "scheduled",
        scheduledCount: plan.notifications.length,
      };
    } catch (caught: unknown) {
      if (isExpectedAuthCancellation(caught)) {
        emit({ syncing: false });
        return { status: "unauthenticated", scheduledCount: 0 };
      }
      emit({
        syncing: false,
        error: "Could not refresh reminders from the server.",
      });
      return { status: "error", scheduledCount: 0 };
    }
  }

  function scheduleCoalescedSync(
    capability: ProtectedRequestCapability | null,
    options?: { now?: Date; timeZone?: string },
  ): Promise<ReminderSyncResult> {
    if (syncInFlight) {
      return new Promise<ReminderSyncResult>((resolve) => {
        if (queuedSyncRequest === null) {
          queuedSyncRequest = {
            capability,
            now: options?.now,
            timeZone: options?.timeZone,
            waiters: [resolve],
          };
        } else {
          // Last call wins: replace trigger arguments, keep all waiters resolved when done.
          queuedSyncRequest.capability = capability;
          queuedSyncRequest.now = options?.now;
          queuedSyncRequest.timeZone = options?.timeZone;
          queuedSyncRequest.waiters.push(resolve);
        }
      });
    }

    syncInFlight = true;
    const promise = enqueueExclusive(async () => {
      let current: {
        capability: ProtectedRequestCapability | null;
        now?: Date;
        timeZone?: string;
        waiters: ((result: ReminderSyncResult) => void)[];
      } | null = {
        capability,
        now: options?.now,
        timeZone: options?.timeZone,
        waiters: [],
      };
      let lastResult: ReminderSyncResult = {
        status: "error",
        scheduledCount: 0,
      };
      try {
        while (current !== null) {
          const active = current;
          current = null;
          lastResult = await runSingleSyncPass(active.capability, {
            now: active.now,
            timeZone: active.timeZone,
          });
          for (const resolve of active.waiters) {
            resolve(lastResult);
          }
          if (queuedSyncRequest !== null) {
            current = queuedSyncRequest;
            queuedSyncRequest = null;
          }
        }
        return lastResult;
      } finally {
        syncInFlight = false;
        activeSyncPromise = null;
      }
    });
    activeSyncPromise = promise;
    return promise;
  }

  return {
    getSnapshot() {
      return snapshot;
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    async refreshState() {
      return await enqueueExclusive(async () => {
        const settings = await resolvedStore.loadSettings();
        const plan = await resolvedStore.loadPlanSummary();
        let permission: ReminderSnapshot["permission"] = "unknown";
        if (resolvedAdapter !== null) {
          try {
            permission = await resolvedAdapter.checkPermissions();
          } catch {
            permission = "unknown";
          }
        }
        emit({ settings, plan, permission });
        return snapshot;
      });
    },
    syncNow(capability, options) {
      return scheduleCoalescedSync(capability, options);
    },
    async enableWithPermission(nextSettings, capability) {
      const outcome = await enqueueExclusive(async () => {
        if (resolvedAdapter === null) {
          const disabled: ReminderSettings = {
            ...normalizeReminderSettings({ ...nextSettings, enabled: false }),
            enabled: false,
          };
          await resolvedStore.saveSettings(disabled);
          emit({ settings: disabled, permission: "denied" });
          return {
            granted: false,
            permission: "denied" as LocalNotificationPermissionState,
          };
        }
        const permission = await resolvedAdapter.requestPermissions();
        if (permission !== "granted") {
          const disabled: ReminderSettings = {
            ...normalizeReminderSettings({ ...nextSettings, enabled: false }),
            enabled: false,
          };
          await resolvedStore.saveSettings(disabled);
          await clearOwnedReminders(resolvedAdapter, {
            includeDelivered: true,
          });
          await resolvedStore.clearPlanSummary();
          emit({
            settings: disabled,
            permission,
            plan: null,
            error: null,
          });
          return { granted: false, permission };
        }
        const enabled: ReminderSettings = {
          ...normalizeReminderSettings({ ...nextSettings, enabled: true }),
          enabled: true,
        };
        await resolvedStore.saveSettings(enabled);
        emit({ settings: enabled, permission, error: null });
        return { granted: true, permission };
      });
      if (outcome.granted) {
        await scheduleCoalescedSync(capability);
      }
      return outcome;
    },
    async disable() {
      discardQueuedSync({ status: "disabled", scheduledCount: 0 });
      await enqueueExclusive(async () => {
        const current = await resolvedStore.loadSettings();
        const disabled: ReminderSettings = { ...current, enabled: false };
        await resolvedStore.saveSettings(disabled);
        await clearOwnedReminders(resolvedAdapter, { includeDelivered: true });
        await resolvedStore.clearPlanSummary();
        emit({ settings: disabled, plan: null, syncing: false, error: null });
      });
    },
    async updateSettings(nextSettings, capability) {
      const normalized = normalizeReminderSettings(nextSettings);
      if (!normalized.enabled) {
        discardQueuedSync({ status: "disabled", scheduledCount: 0 });
        await enqueueExclusive(async () => {
          await resolvedStore.saveSettings(normalized);
          await clearOwnedReminders(resolvedAdapter, {
            includeDelivered: true,
          });
          await resolvedStore.clearPlanSummary();
          emit({
            settings: normalized,
            plan: null,
            syncing: false,
            error: null,
          });
        });
        return { status: "disabled", scheduledCount: 0 };
      }
      await enqueueExclusive(async () => {
        await resolvedStore.saveSettings(normalized);
        emit({ settings: normalized, error: null });
      });
      return await scheduleCoalescedSync(capability);
    },
    async clearOnTrustLoss() {
      discardQueuedSync({ status: "unauthenticated", scheduledCount: 0 });
      if (activeSyncPromise !== null) {
        try {
          await activeSyncPromise;
        } catch {
          // Proceed with cleanup even if the in-flight sync errored.
        }
      }
      await enqueueExclusive(async () => {
        await clearOwnedReminders(resolvedAdapter, { includeDelivered: true });
        await resolvedStore.clearPlanSummary();
        emit({ plan: null, syncing: false, error: null });
      });
    },
  };
}

let activeCoordinator: ReminderCoordinator | null = null;

export function registerActiveReminderCoordinator(
  coordinator: ReminderCoordinator | null,
): void {
  activeCoordinator = coordinator;
}

export function getActiveReminderCoordinator(): ReminderCoordinator | null {
  return activeCoordinator;
}

/** Extracts and validates the target hash route from a notification tap payload. */
export function extractRouteFromNotificationAction(
  action: CapacitorLocalNotificationActionPerformed,
): string {
  const extra = action.notification?.extra;
  if (typeof extra === "object" && extra !== null && !Array.isArray(extra)) {
    return validateReminderRoute((extra as Record<string, unknown>).route);
  }
  return validateReminderRoute(undefined);
}

/**
 * Attaches a listener for `localNotificationActionPerformed` (covers both warm
 * taps and Capacitor's cold-start retained intent replay).
 */
export function subscribeNotificationTap(
  onRoute: (route: string) => void,
  target: typeof globalThis = globalThis,
): () => void {
  const capacitor = getCapacitorGlobal(target);
  const plugin = capacitor?.Plugins?.LocalNotifications;
  let removed = false;
  let handle: CapacitorPluginListenerHandle | null = null;

  const callback = (action: CapacitorLocalNotificationActionPerformed) => {
    if (removed) return;
    onRoute(extractRouteFromNotificationAction(action));
  };

  if (plugin !== undefined && typeof plugin.addListener === "function") {
    const maybeHandle = plugin.addListener(
      "localNotificationActionPerformed",
      callback,
    );
    void Promise.resolve(maybeHandle).then((resolved) => {
      if (removed) {
        void resolved.remove();
      } else {
        handle = resolved;
      }
    });
  } else if (typeof capacitor?.addListener === "function") {
    handle = capacitor.addListener(
      "LocalNotifications",
      "localNotificationActionPerformed",
      (event) => {
        callback(event as CapacitorLocalNotificationActionPerformed);
      },
    );
  }

  return () => {
    removed = true;
    if (handle !== null) {
      void handle.remove();
      handle = null;
    }
  };
}

/** Subscribes to Capacitor `App` foreground resume events. */
export function subscribeAppResume(
  onResume: () => void,
  target: typeof globalThis = globalThis,
): () => void {
  const capacitor = getCapacitorGlobal(target);
  const appPlugin = capacitor?.Plugins?.App;
  let removed = false;
  let handle: CapacitorPluginListenerHandle | null = null;

  const handleStateChange = (state: { isActive: boolean }) => {
    if (!removed && state.isActive) {
      onResume();
    }
  };

  if (appPlugin !== undefined && typeof appPlugin.addListener === "function") {
    const maybeHandle = appPlugin.addListener(
      "appStateChange",
      handleStateChange,
    );
    void Promise.resolve(maybeHandle).then((resolved) => {
      if (removed) {
        void resolved.remove();
      } else {
        handle = resolved;
      }
    });
  } else if (typeof capacitor?.addListener === "function") {
    handle = capacitor.addListener("App", "appStateChange", (event) => {
      handleStateChange(event as { isActive: boolean });
    });
  }

  return () => {
    removed = true;
    if (handle !== null) {
      void handle.remove();
      handle = null;
    }
  };
}
