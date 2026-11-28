import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { useAuth } from "../auth/context";
import {
  createReminderCoordinator,
  getActiveReminderCoordinator,
  type ReminderCoordinator,
} from "./reminders";
import { isValidReminderTime } from "./remindersPlan";
import "./native-onboarding.css";

function formatUpdatedTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export interface NativeRemindersSettingsProps {
  coordinator?: ReminderCoordinator;
}

export function NativeRemindersSettings({
  coordinator,
}: NativeRemindersSettingsProps) {
  const { capability } = useAuth();
  const resolvedCoordinator = useMemo<ReminderCoordinator>(
    () =>
      coordinator ??
      getActiveReminderCoordinator() ??
      createReminderCoordinator(),
    [coordinator],
  );
  const snapshot = useSyncExternalStore(
    resolvedCoordinator.subscribe,
    resolvedCoordinator.getSnapshot,
    resolvedCoordinator.getSnapshot,
  );
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    void resolvedCoordinator.refreshState();
  }, [resolvedCoordinator]);

  const { settings, permission, plan, syncing, error } = snapshot;
  const controlsDisabled = busy || syncing;
  const permissionDenied = permission === "denied";

  async function handleToggleEnabled(checked: boolean) {
    if (busy) return;
    setBusy(true);
    setStatusMessage(null);
    try {
      if (checked) {
        const outcome = await resolvedCoordinator.enableWithPermission(
          {
            time: settings.time,
            includeOverdue: settings.includeOverdue,
          },
          capability,
        );
        if (outcome.granted) {
          setStatusMessage("Daily reminders enabled for this device.");
        }
      } else {
        await resolvedCoordinator.disable();
        setStatusMessage("Daily reminders turned off on this device.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleTimeChange(nextTime: string) {
    if (!isValidReminderTime(nextTime) || busy) return;
    setBusy(true);
    setStatusMessage(null);
    try {
      await resolvedCoordinator.updateSettings(
        { ...settings, time: nextTime },
        capability,
      );
      setStatusMessage(
        settings.enabled
          ? `Reminder time updated to ${nextTime}.`
          : `Default reminder time saved as ${nextTime}.`,
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleIncludeOverdueChange(checked: boolean) {
    if (busy) return;
    setBusy(true);
    setStatusMessage(null);
    try {
      await resolvedCoordinator.updateSettings(
        { ...settings, includeOverdue: checked },
        capability,
      );
      setStatusMessage(
        checked
          ? "Overdue activities will be included in today's digest."
          : "Overdue activities excluded from reminders.",
      );
    } finally {
      setBusy(false);
    }
  }

  const scheduledDayCount = plan?.days.length ?? 0;

  return (
    <section className="settings-panel" aria-labelledby="reminders-heading">
      <h3 id="reminders-heading">Reminders</h3>
      <p>
        Schedule one daily local digest on this device for upcoming planned
        activities. Reminders update when you open the app
        {plan !== null
          ? ` · Last updated ${formatUpdatedTimestamp(plan.updatedAt)}.`
          : "."}
      </p>

      <div className="mobile-reminders__controls">
        <label className="mobile-reminders__checkbox">
          <input
            type="checkbox"
            checked={settings.enabled}
            disabled={controlsDisabled}
            onChange={(event) => {
              void handleToggleEnabled(event.currentTarget.checked);
            }}
          />
          <span>Enable daily Schedule reminders on this device</span>
        </label>

        <div className="field mobile-reminders__time">
          <label htmlFor="mobile-reminder-time">
            Daily reminder time (device local time)
          </label>
          <input
            id="mobile-reminder-time"
            type="time"
            value={settings.time}
            disabled={controlsDisabled}
            onChange={(event) => {
              void handleTimeChange(event.currentTarget.value);
            }}
          />
        </div>

        <label className="mobile-reminders__checkbox">
          <input
            type="checkbox"
            checked={settings.includeOverdue}
            disabled={controlsDisabled}
            onChange={(event) => {
              void handleIncludeOverdueChange(event.currentTarget.checked);
            }}
          />
          <span>Include overdue activities</span>
        </label>
      </div>

      {permissionDenied && (
        <div className="notice notice--warning" role="alert">
          <p>
            <strong>Notifications are disabled in Android.</strong> To turn
            reminders on, open{" "}
            <strong>Android Settings → Apps → Florabase → Notifications</strong>
            , allow notifications, then return here and enable reminders.
          </p>
        </div>
      )}

      {error !== null && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}

      {statusMessage !== null && <p role="status">{statusMessage}</p>}

      {settings.enabled && !permissionDenied && (
        <p className="mobile-reminders__meta" aria-live="polite">
          {syncing
            ? "Updating reminder schedule…"
            : plan === null
              ? "Waiting for first Schedule sync."
              : scheduledDayCount === 0
                ? "No upcoming activities in the next 14 days."
                : `${String(scheduledDayCount)} upcoming ${scheduledDayCount === 1 ? "day" : "days"} scheduled (next 14 days).`}
        </p>
      )}

      <p className="mobile-reminders__meta">
        Lock screen notifications hide activity titles until unlocked and
        expanded. No server URL, target names, locations, or notes are included.
      </p>
    </section>
  );
}
