/**
 * Pure, deterministic daily reminder plan builder for Android local notifications.
 *
 * Zero DOM or Capacitor runtime dependencies so every scheduling rule, DST edge case,
 * privacy constraint, and ID-range invariant can be unit-tested directly in Vitest.
 */

import type { SchedulePage } from "../schedule/api";
import type { CapacitorLocalNotificationPayload } from "./runtime";

export const REMINDER_HORIZON_DAYS = 14;
export const REMINDER_ID_BASE = 41_000;
export const REMINDER_ID_MAX = 41_099;
export const REMINDER_CHANNEL_ID = "schedule-reminders";
export const REMINDER_CHANNEL_NAME = "Schedule reminders";
export const REMINDER_CHANNEL_DESCRIPTION =
  "Daily digest of planned Florabase activities";
export const REMINDER_GROUP_ID = "florabase-schedule-reminders";
export const REMINDER_SMALL_ICON = "ic_stat_florabase";
export const REMINDER_ICON_COLOR = "#153A2C";
export const REMINDER_EXTRA_SCHEMA_VERSION = 1;
export const REMINDER_MAX_TITLES = 5;
export const REMINDER_MAX_TITLE_LENGTH = 60;
export const REMINDER_DEFAULT_ROUTE = "#/schedule?window=today";
export const REMINDER_OVERDUE_ROUTE = "#/schedule?window=overdue";

export interface ReminderSettings {
  enabled: boolean;
  /** Local 24-hour wall-clock time in HH:MM format (e.g. "08:00"). */
  time: string;
  includeOverdue: boolean;
}

export const DEFAULT_REMINDER_SETTINGS: ReminderSettings = {
  enabled: false,
  time: "08:00",
  includeOverdue: true,
};

/**
 * Minimal cached plan metadata persisted in Capacitor Preferences.
 * Intentionally stores ONLY timestamps, timezone, and per-day counts — never
 * activity titles, targets, locations, notes, server URLs, or tokens.
 */
export interface ReminderDaySummary {
  date: string;
  dueCount: number;
  overdueCount: number;
}

export interface ReminderPlanSummary {
  updatedAt: string;
  timeZone: string;
  days: ReminderDaySummary[];
}

export interface ReminderPlanResult {
  notifications: CapacitorLocalNotificationPayload[];
  summary: ReminderPlanSummary;
}

const TIME_PATTERN = /^([01]\d|2[0-3]):([0-5]\d)$/;
const CALENDAR_DAY_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const ALLOWED_ROUTE_PATTERN =
  /^#\/schedule(?:\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\?window=(?:today|overdue|next_seven_days))?$/i;

export function isOwnedReminderId(id: number): boolean {
  return (
    Number.isInteger(id) && id >= REMINDER_ID_BASE && id <= REMINDER_ID_MAX
  );
}

export function isValidReminderTime(value: string): boolean {
  return TIME_PATTERN.test(value);
}

export function parseReminderTime(value: string): {
  hour: number;
  minute: number;
} {
  const match = TIME_PATTERN.exec(value);
  if (match === null) {
    return { hour: 8, minute: 0 };
  }
  return {
    hour: Number(match[1]),
    minute: Number(match[2]),
  };
}

export function normalizeReminderSettings(raw: unknown): ReminderSettings {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    return { ...DEFAULT_REMINDER_SETTINGS };
  }
  const record = raw as Record<string, unknown>;
  const enabled = record.enabled === true;
  const time =
    typeof record.time === "string" && isValidReminderTime(record.time)
      ? record.time
      : DEFAULT_REMINDER_SETTINGS.time;
  const includeOverdue =
    typeof record.includeOverdue === "boolean"
      ? record.includeOverdue
      : DEFAULT_REMINDER_SETTINGS.includeOverdue;
  return { enabled, time, includeOverdue };
}

/**
 * Strips ASCII/C1 control characters, collapses whitespace, and caps plain-text
 * activity titles at `REMINDER_MAX_TITLE_LENGTH` characters for expanded digests.
 */
export function sanitizeReminderTitle(raw: string): string {
  let cleaned = "";
  for (const ch of raw) {
    const code = ch.codePointAt(0) ?? 0;
    if ((code >= 0x00 && code <= 0x1f) || (code >= 0x7f && code <= 0x9f)) {
      cleaned += " ";
    } else {
      cleaned += ch;
    }
  }
  const collapsed = cleaned.replace(/\s+/g, " ").trim();
  if (collapsed.length === 0) {
    return "";
  }
  const chars = Array.from(collapsed);
  if (chars.length <= REMINDER_MAX_TITLE_LENGTH) {
    return collapsed;
  }
  return `${chars
    .slice(0, REMINDER_MAX_TITLE_LENGTH - 1)
    .join("")
    .trimEnd()}…`;
}

/**
 * Validates notification tap routes against the strict Schedule route allowlist.
 * Any malformed or unexpected route safely falls back to Schedule Today.
 */
export function validateReminderRoute(raw: unknown): string {
  if (typeof raw !== "string") {
    return REMINDER_DEFAULT_ROUTE;
  }
  const trimmed = raw.trim();
  if (!ALLOWED_ROUTE_PATTERN.test(trimmed)) {
    return REMINDER_DEFAULT_ROUTE;
  }
  return trimmed;
}

export function getDeviceTimeZone(): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (typeof tz === "string" && tz.trim() !== "") {
      return tz;
    }
  } catch {
    // Fall back to UTC if Intl timezone lookup is unavailable.
  }
  return "UTC";
}

function getTimeZoneFormatter(timeZone: string): Intl.DateTimeFormat {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
}

function readWallClockParts(
  instantMs: number,
  formatter: Intl.DateTimeFormat,
): {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
} {
  const parts = formatter.formatToParts(new Date(instantMs));
  let year = 1970;
  let month = 1;
  let day = 1;
  let hour = 0;
  let minute = 0;
  for (const part of parts) {
    if (part.type === "year") year = Number(part.value);
    else if (part.type === "month") month = Number(part.value);
    else if (part.type === "day") day = Number(part.value);
    else if (part.type === "hour") {
      const parsed = Number(part.value);
      hour = parsed === 24 ? 0 : parsed;
    } else if (part.type === "minute") minute = Number(part.value);
  }
  return { year, month, day, hour, minute };
}

function wallClockKey(
  instantMs: number,
  formatter: Intl.DateTimeFormat,
): number {
  const p = readWallClockParts(instantMs, formatter);
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, 0, 0);
}

/** Formats a UTC instant as a local `YYYY-MM-DD` calendar day in `timeZone`. */
export function getLocalDayInTimeZone(
  now: Date = new Date(),
  timeZone: string = getDeviceTimeZone(),
): string {
  const formatter = getTimeZoneFormatter(timeZone);
  const p = readWallClockParts(now.getTime(), formatter);
  return `${String(p.year).padStart(4, "0")}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}`;
}

/** Pure calendar-day arithmetic on `YYYY-MM-DD`, unaffected by DST length. */
export function addCalendarDays(day: string, offset: number): string {
  const match = CALENDAR_DAY_PATTERN.exec(day);
  if (match === null) {
    throw new Error(`Invalid calendar day: ${day}`);
  }
  const utc = new Date(
    Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]) + offset),
  );
  return `${String(utc.getUTCFullYear()).padStart(4, "0")}-${String(utc.getUTCMonth() + 1).padStart(2, "0")}-${String(utc.getUTCDate()).padStart(2, "0")}`;
}

/**
 * Resolves a local wall-clock `(YYYY-MM-DD, hour, minute)` in `timeZone` to a UTC `Date`.
 *
 * DST behaviour:
 * - Normal wall-clock time: exact matching instant on that day.
 * - Fall-back ambiguous time (occurs twice, e.g. 02:30 on last Sunday of October in Europe/Rome):
 *   picks the first (earlier) valid instant (02:30 CEST).
 * - Spring-forward nonexistent time (skipped gap, e.g. 02:30 on last Sunday of March in Europe/Rome):
 *   picks the next valid instant immediately after the gap (03:00 CEST).
 */
export function resolveWallClockInstant(
  day: string,
  hour: number,
  minute: number,
  timeZone: string = getDeviceTimeZone(),
): Date {
  const match = CALENDAR_DAY_PATTERN.exec(day);
  if (match === null) {
    throw new Error(`Invalid calendar day: ${day}`);
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const date = Number(match[3]);
  const targetKey = Date.UTC(year, month - 1, date, hour, minute, 0, 0);
  const formatter = getTimeZoneFormatter(timeZone);

  const offsets = new Set<number>();
  const sampleDeltasHours = [-14, -3, 0, 3, 14];
  for (const deltaHours of sampleDeltasHours) {
    const probeMs = targetKey + deltaHours * 3_600_000;
    const offsetMs = wallClockKey(probeMs, formatter) - probeMs;
    offsets.add(offsetMs);
  }

  const exactMatches: number[] = [];
  for (const offsetMs of offsets) {
    const candidateMs = targetKey - offsetMs;
    if (wallClockKey(candidateMs, formatter) === targetKey) {
      exactMatches.push(candidateMs);
    }
  }
  if (exactMatches.length > 0) {
    return new Date(Math.min(...exactMatches));
  }

  // Spring-forward gap: wall-clock time does not exist on this day.
  // Binary search in 1-minute steps for the first instant whose local wall clock >= targetKey.
  const sortedOffsets = [...offsets].sort((a, b) => a - b);
  const minOffset = sortedOffsets[0] ?? 0;
  const maxOffset = sortedOffsets[sortedOffsets.length - 1] ?? 0;
  let loMin = Math.floor((targetKey - maxOffset) / 60_000) - 60;
  let hiMin = Math.ceil((targetKey - minOffset) / 60_000) + 60;
  while (loMin < hiMin) {
    const midMin = Math.floor((loMin + hiMin) / 2);
    if (wallClockKey(midMin * 60_000, formatter) >= targetKey) {
      hiMin = midMin;
    } else {
      loMin = midMin + 1;
    }
  }
  return new Date(loMin * 60_000);
}

function pluralize(count: number, singular: string, plural: string): string {
  return `${String(count)} ${count === 1 ? singular : plural}`;
}

function formatDigestBody({
  dueCount,
  overdueCount,
  isTruncated,
}: {
  dueCount: number;
  overdueCount: number;
  isTruncated: boolean;
}): string {
  if (isTruncated && dueCount > 0) {
    const base = `At least ${pluralize(dueCount, "activity", "activities")} due today`;
    return overdueCount > 0
      ? `${base} · ${String(overdueCount)} overdue`
      : base;
  }
  if (dueCount > 0 && overdueCount > 0) {
    return `${pluralize(dueCount, "activity", "activities")} due today · ${String(overdueCount)} overdue`;
  }
  if (dueCount > 0) {
    return `${pluralize(dueCount, "activity", "activities")} due today`;
  }
  return pluralize(overdueCount, "overdue activity", "overdue activities");
}

export function buildReminderPlan(
  page: SchedulePage,
  settings: ReminderSettings,
  {
    now = new Date(),
    timeZone = getDeviceTimeZone(),
    horizonDays = REMINDER_HORIZON_DAYS,
  }: {
    now?: Date;
    timeZone?: string;
    horizonDays?: number;
  } = {},
): ReminderPlanResult {
  const effectiveHorizon = Math.max(
    1,
    Math.min(horizonDays, REMINDER_ID_MAX - REMINDER_ID_BASE + 1),
  );
  const today = getLocalDayInTimeZone(now, timeZone);
  const { hour, minute } = parseReminderTime(settings.time);

  const itemsByDay = new Map<string, { id: string; title: string }[]>();
  let lastItemDay: string | null = null;
  for (const item of page.items) {
    if (item.status !== "planned") continue;
    const list = itemsByDay.get(item.due_on) ?? [];
    list.push({ id: item.id, title: item.title });
    itemsByDay.set(item.due_on, list);
    if (lastItemDay === null || item.due_on > lastItemDay) {
      lastItemDay = item.due_on;
    }
  }

  const pageTruncated = page.total > page.items.length;
  const notifications: CapacitorLocalNotificationPayload[] = [];
  const days: ReminderDaySummary[] = [];

  for (let offset = 0; offset < effectiveHorizon; offset += 1) {
    const day = addCalendarDays(today, offset);
    const dayItems = itemsByDay.get(day) ?? [];

    let dueCount: number;
    let overdueCount: number;
    let isCountLowerBound = false;
    let omitTitles: boolean;

    if (offset === 0) {
      dueCount = Math.max(0, page.today_count);
      overdueCount = settings.includeOverdue
        ? Math.max(0, page.overdue_count)
        : 0;
      omitTitles = pageTruncated && dayItems.length < dueCount;
    } else {
      if (pageTruncated && lastItemDay !== null && day > lastItemDay) {
        break;
      }
      dueCount = dayItems.length;
      overdueCount = 0;
      isCountLowerBound =
        pageTruncated && lastItemDay !== null && day === lastItemDay;
      omitTitles = isCountLowerBound;
    }

    if (dueCount === 0 && overdueCount === 0) {
      continue;
    }

    const triggerAt = resolveWallClockInstant(day, hour, minute, timeZone);
    if (triggerAt.getTime() <= now.getTime()) {
      continue;
    }

    const summaryText = formatDigestBody({
      dueCount,
      overdueCount,
      isTruncated: isCountLowerBound,
    });
    const collapsedBody =
      dueCount === 0 && overdueCount > 0
        ? "Open Schedule to review overdue work"
        : "Open Schedule to review today's work";

    const titles = omitTitles
      ? []
      : dayItems
          .map((item) => sanitizeReminderTitle(item.title))
          .filter((title) => title !== "")
          .slice(0, REMINDER_MAX_TITLES);

    let route: string;
    if (dueCount === 0 && overdueCount > 0) {
      route = REMINDER_OVERDUE_ROUTE;
    } else if (
      dueCount === 1 &&
      overdueCount === 0 &&
      !omitTitles &&
      dayItems.length === 1
    ) {
      route = validateReminderRoute(`#/schedule/${dayItems[0].id}`);
    } else {
      route = REMINDER_DEFAULT_ROUTE;
    }

    const notification: CapacitorLocalNotificationPayload = {
      id: REMINDER_ID_BASE + offset,
      title: summaryText,
      body: collapsedBody,
      channelId: REMINDER_CHANNEL_ID,
      group: REMINDER_GROUP_ID,
      autoCancel: true,
      smallIcon: REMINDER_SMALL_ICON,
      iconColor: REMINDER_ICON_COLOR,
      isExactNotification: false,
      schedule: {
        at: triggerAt.toISOString(),
        allowWhileIdle: true,
      },
      extra: {
        route,
        v: REMINDER_EXTRA_SCHEMA_VERSION,
      },
    };
    if (titles.length > 0) {
      notification.inboxList = titles;
    }

    notifications.push(notification);
    days.push({ date: day, dueCount, overdueCount });

    if (isCountLowerBound) {
      break;
    }
  }

  return {
    notifications,
    summary: {
      updatedAt: now.toISOString(),
      timeZone,
      days,
    },
  };
}
