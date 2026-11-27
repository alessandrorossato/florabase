// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import type { ProtectedRequestCapability } from "../auth/api";
import { NativeRemindersSettings } from "./NativeRemindersSettings";
import {
  createReminderCoordinator,
  type LocalNotificationsAdapter,
  type ReminderPreferenceStore,
} from "./reminders";
import {
  DEFAULT_REMINDER_SETTINGS,
  type ReminderPlanSummary,
  type ReminderSettings,
} from "./remindersPlan";
import type { LocalNotificationPermissionState } from "./runtime";

function fakeCapability(): ProtectedRequestCapability {
  return {
    isAuthorized: () => true,
    subscribeInvalidation: () => () => undefined,
    subscribePermanentRevocation: () => () => undefined,
  } as unknown as ProtectedRequestCapability;
}

function renderWithAuth(ui: React.ReactNode) {
  const value: AuthContextValue = {
    state: {
      status: "authenticated",
      session: {
        user_id: "u1",
        login_name: "owner",
        display_name: "Owner",
        owner: true,
        canonical_origin: null,
        demo_readonly: false,
      },
      csrfToken: "bearer",
    },
    workspaceKey: 1,
    capability: fakeCapability(),
    logIn: vi.fn(),
    logOut: vi.fn(),
    cancelLogout: vi.fn(),
    retryRestoration: vi.fn(),
    sessionExpired: vi.fn(),
  };
  return render(
    <AuthContext.Provider value={value}>{ui}</AuthContext.Provider>,
  );
}

function makeHarness(
  initialPermission: LocalNotificationPermissionState = "prompt",
  initialSettings: Partial<ReminderSettings> = {},
) {
  let settings: ReminderSettings = {
    ...DEFAULT_REMINDER_SETTINGS,
    ...initialSettings,
  };
  let plan: ReminderPlanSummary | null = null;
  let permission = initialPermission;

  const store: ReminderPreferenceStore = {
    loadSettings: vi.fn(() => Promise.resolve({ ...settings })),
    saveSettings: vi.fn((next: ReminderSettings) => {
      settings = { ...next };
      return Promise.resolve();
    }),
    loadPlanSummary: vi.fn(() => Promise.resolve(plan)),
    savePlanSummary: vi.fn((next: ReminderPlanSummary) => {
      plan = next;
      return Promise.resolve();
    }),
    clearPlanSummary: vi.fn(() => {
      plan = null;
      return Promise.resolve();
    }),
  };

  const adapter: LocalNotificationsAdapter = {
    checkPermissions: vi.fn(() => Promise.resolve(permission)),
    requestPermissions: vi.fn(() => Promise.resolve(permission)),
    ensureChannel: vi.fn(() => Promise.resolve()),
    getPendingIds: vi.fn(() => Promise.resolve([])),
    cancelIds: vi.fn(() => Promise.resolve()),
    getDelivered: vi.fn(() => Promise.resolve([])),
    removeDelivered: vi.fn(() => Promise.resolve()),
    schedule: vi.fn(() => Promise.resolve()),
  };

  const coordinator = createReminderCoordinator({
    store,
    adapter,
    fetchSchedulePage: vi.fn(() =>
      Promise.resolve({
        items: [],
        total: 0,
        offset: 0,
        limit: 100,
        today: "2026-05-01",
        overdue_count: 1,
        today_count: 0,
      }),
    ),
    nowProvider: () => new Date("2026-05-01T06:00:00Z"),
    timeZoneProvider: () => "UTC",
  });

  return {
    coordinator,
    store,
    adapter,
    setPermission(next: LocalNotificationPermissionState) {
      permission = next;
    },
  };
}

afterEach(() => {
  cleanup();
});

describe("NativeRemindersSettings", () => {
  it("defaults off without prompting and shows Android Settings instructions when permission is denied", async () => {
    const harness = makeHarness("denied");
    renderWithAuth(
      <NativeRemindersSettings coordinator={harness.coordinator} />,
    );

    const toggle = await screen.findByRole("checkbox", {
      name: /Enable daily Schedule reminders/i,
    });
    expect(toggle).not.toBeChecked();
    expect(harness.adapter.requestPermissions).not.toHaveBeenCalled();

    fireEvent.click(toggle);

    await waitFor(() => {
      expect(harness.adapter.requestPermissions).toHaveBeenCalledTimes(1);
    });
    expect(toggle).not.toBeChecked();
    expect(
      screen.getByText(/Notifications are disabled in Android/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Android Settings → Apps → Florabase → Notifications/i),
    ).toBeInTheDocument();
  });

  it("enables reminders when granted, updates time & includeOverdue, and disables cleanly", async () => {
    const harness = makeHarness("granted");
    renderWithAuth(
      <NativeRemindersSettings coordinator={harness.coordinator} />,
    );

    const toggle = await screen.findByRole("checkbox", {
      name: /Enable daily Schedule reminders/i,
    });
    fireEvent.click(toggle);

    await waitFor(() => {
      expect(toggle).toBeChecked();
      expect(harness.adapter.schedule).toHaveBeenCalledTimes(1);
    });
    expect(
      screen.getByText(
        /Reminders update when you open the app · Last updated/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 upcoming day scheduled/i)).toBeInTheDocument();

    const timeInput = screen.getByLabelText(/Daily reminder time/i);
    fireEvent.change(timeInput, { target: { value: "09:15" } });
    await waitFor(() => {
      expect(harness.adapter.schedule).toHaveBeenCalledTimes(2);
    });

    const overdueToggle = screen.getByRole("checkbox", {
      name: /Include overdue activities/i,
    });
    fireEvent.click(overdueToggle);
    await waitFor(() => {
      expect(overdueToggle).not.toBeChecked();
    });

    fireEvent.click(toggle);
    await waitFor(() => {
      expect(toggle).not.toBeChecked();
      expect(harness.store.clearPlanSummary).toHaveBeenCalled();
    });
  });

  it("shows revoked-permission notice without re-prompting when permission was turned off later", async () => {
    const harness = makeHarness("denied", { enabled: true, time: "08:00" });
    renderWithAuth(
      <NativeRemindersSettings coordinator={harness.coordinator} />,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Notifications are disabled in Android/i),
      ).toBeInTheDocument();
    });
    expect(harness.adapter.requestPermissions).not.toHaveBeenCalled();
    expect(harness.adapter.schedule).not.toHaveBeenCalled();
  });
});
