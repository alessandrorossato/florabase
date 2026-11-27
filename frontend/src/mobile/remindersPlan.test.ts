import { describe, expect, it } from "vitest";

import type { Activity, SchedulePage } from "../schedule/api";
import {
  addCalendarDays,
  buildReminderPlan,
  DEFAULT_REMINDER_SETTINGS,
  getLocalDayInTimeZone,
  isOwnedReminderId,
  REMINDER_CHANNEL_ID,
  REMINDER_DEFAULT_ROUTE,
  REMINDER_EXTRA_SCHEMA_VERSION,
  REMINDER_GROUP_ID,
  REMINDER_HORIZON_DAYS,
  REMINDER_ICON_COLOR,
  REMINDER_ID_BASE,
  REMINDER_ID_MAX,
  REMINDER_OVERDUE_ROUTE,
  REMINDER_SMALL_ICON,
  resolveWallClockInstant,
  sanitizeReminderTitle,
  validateReminderRoute,
  type ReminderSettings,
} from "./remindersPlan";

function makeActivity(
  overrides: Partial<Activity> & Pick<Activity, "id" | "title" | "due_on">,
): Activity {
  return {
    activity_kind: "water",
    target: {
      kind: "plant",
      id: "11111111-1111-4111-8111-111111111111",
      label: "Secret Greenhouse Specimen",
      lifecycle: "active",
      scientific_name: "Monstera deliciosa",
      cultivar_name: null,
    },
    notes: "Private shelf note at https://secret.example.com",
    status: "planned",
    version: 1,
    overdue: false,
    linked_event_id: null,
    created_at: "2026-03-01T08:00:00Z",
    updated_at: "2026-03-01T08:00:00Z",
    completed_at: null,
    cancelled_at: null,
    ...overrides,
  };
}

function makePage(
  items: Activity[],
  overrides: Partial<SchedulePage> = {},
): SchedulePage {
  return {
    items,
    total: items.length,
    offset: 0,
    limit: 100,
    today: "2026-03-27",
    overdue_count: 0,
    today_count: items.filter((item) => item.due_on === "2026-03-27").length,
    ...overrides,
  };
}

const enabledSettings: ReminderSettings = {
  ...DEFAULT_REMINDER_SETTINGS,
  enabled: true,
  time: "08:00",
  includeOverdue: true,
};

describe("remindersPlan", () => {
  it("builds one digest per active day, skips empty days, and caps at horizon N=14", () => {
    const items: Activity[] = [];
    for (let dayOffset = 0; dayOffset < 18; dayOffset += 1) {
      if (dayOffset === 1 || dayOffset === 3) continue; // empty days
      items.push(
        makeActivity({
          id: `00000000-0000-4000-8000-${String(dayOffset).padStart(12, "0")}`,
          title: `Water tray ${String(dayOffset)}`,
          due_on: addCalendarDays("2026-05-01", dayOffset),
        }),
      );
    }
    // Add two more on day 0 to test multi-activity digest + overdue copy
    items.push(
      makeActivity({
        id: "00000000-0000-4000-8000-000000000101",
        title: "Inspect seedlings",
        due_on: "2026-05-01",
      }),
      makeActivity({
        id: "00000000-0000-4000-8000-000000000102",
        title: "Feed orchids",
        due_on: "2026-05-01",
      }),
    );

    const page = makePage(items, {
      today: "2026-05-01",
      today_count: 3,
      overdue_count: 1,
    });

    const result = buildReminderPlan(page, enabledSettings, {
      now: new Date("2026-05-01T06:00:00Z"),
      timeZone: "UTC",
    });

    expect(result.notifications.length).toBeLessThanOrEqual(
      REMINDER_HORIZON_DAYS,
    );
    // 14 days minus 2 skipped empty days (offset 1 & 3) = 12 scheduled notifications
    expect(result.notifications).toHaveLength(12);
    expect(result.notifications[0]).toMatchObject({
      id: REMINDER_ID_BASE,
      title: "3 activities due today · 1 overdue",
      body: "Open Schedule to review today's work",
      inboxList: ["Water tray 0", "Inspect seedlings", "Feed orchids"],
      channelId: REMINDER_CHANNEL_ID,
      group: REMINDER_GROUP_ID,
      autoCancel: true,
      smallIcon: REMINDER_SMALL_ICON,
      iconColor: REMINDER_ICON_COLOR,
      isExactNotification: false,
      schedule: {
        at: "2026-05-01T08:00:00.000Z",
        allowWhileIdle: true,
      },
      extra: {
        route: REMINDER_DEFAULT_ROUTE,
        v: REMINDER_EXTRA_SCHEMA_VERSION,
      },
    });
    // Day offset 2 has a single activity -> deep link directly to #/schedule/<id>
    expect(result.notifications[1]).toMatchObject({
      id: REMINDER_ID_BASE + 2,
      title: "1 activity due today",
      body: "Open Schedule to review today's work",
      inboxList: ["Water tray 2"],
      extra: {
        route: "#/schedule/00000000-0000-4000-8000-000000000002",
        v: REMINDER_EXTRA_SCHEMA_VERSION,
      },
    });
    // Summary stores ONLY updatedAt, timeZone, and counts — never titles
    expect(result.summary.updatedAt).toBe("2026-05-01T06:00:00.000Z");
    expect(result.summary.timeZone).toBe("UTC");
    expect(result.summary.days[0]).toEqual({
      date: "2026-05-01",
      dueCount: 3,
      overdueCount: 1,
    });
    expect(JSON.stringify(result.summary)).not.toContain("Water tray");
  });

  it("handles overdue-only today when includeOverdue is on vs off and keeps empty future days silent", () => {
    const page = makePage([], {
      today: "2026-05-01",
      today_count: 0,
      overdue_count: 2,
    });

    const withOverdue = buildReminderPlan(page, enabledSettings, {
      now: new Date("2026-05-01T06:00:00Z"),
      timeZone: "UTC",
    });
    expect(withOverdue.notifications).toHaveLength(1);
    expect(withOverdue.notifications[0]?.title).toBe("2 overdue activities");
    expect(withOverdue.notifications[0]?.body).toBe(
      "Open Schedule to review overdue work",
    );
    expect(withOverdue.notifications[0]?.extra).toEqual({
      route: REMINDER_OVERDUE_ROUTE,
      v: REMINDER_EXTRA_SCHEMA_VERSION,
    });
    expect(withOverdue.notifications[0]?.inboxList).toBeUndefined();

    const withoutOverdue = buildReminderPlan(
      page,
      { ...enabledSettings, includeOverdue: false },
      { now: new Date("2026-05-01T06:00:00Z"), timeZone: "UTC" },
    );
    expect(withoutOverdue.notifications).toHaveLength(0);
  });

  it("skips today when the chosen local time has already passed so past alarms never fire immediately", () => {
    const page = makePage(
      [
        makeActivity({
          id: "00000000-0000-4000-8000-000000000001",
          title: "Morning mist",
          due_on: "2026-05-01",
        }),
        makeActivity({
          id: "00000000-0000-4000-8000-000000000002",
          title: "Tomorrow water",
          due_on: "2026-05-02",
        }),
      ],
      { today: "2026-05-01", today_count: 1, overdue_count: 1 },
    );

    const plan = buildReminderPlan(page, enabledSettings, {
      now: new Date("2026-05-01T08:01:00Z"),
      timeZone: "UTC",
    });

    expect(plan.notifications).toHaveLength(1);
    expect(plan.notifications[0]?.id).toBe(REMINDER_ID_BASE + 1);
    expect(plan.notifications[0]?.schedule?.at).toBe(
      "2026-05-02T08:00:00.000Z",
    );
  });

  it("strips control chars, caps title count (<=5) and length (<=60), and never leaks targets, locations, notes, or URLs", () => {
    const longTitle =
      "Check\n\tgermination\x00of\x1fhigh-altitude\x7fcultivar tray number forty-two in bench A";
    const items = Array.from({ length: 7 }, (_, idx) =>
      makeActivity({
        id: `00000000-0000-4000-8000-${String(idx).padStart(12, "0")}`,
        title: idx === 0 ? longTitle : `Task ${String(idx)}`,
        due_on: "2026-05-01",
      }),
    );

    const plan = buildReminderPlan(
      makePage(items, { today: "2026-05-01", today_count: 7 }),
      enabledSettings,
      { now: new Date("2026-05-01T06:00:00Z"), timeZone: "UTC" },
    );

    const notif = plan.notifications[0];
    expect(notif).toBeDefined();
    expect(notif.title).toBe("7 activities due today");
    expect(notif.body).toBe("Open Schedule to review today's work");
    expect(notif.inboxList).toHaveLength(5);
    const firstTitle = notif.inboxList?.[0] ?? "";
    expect(firstTitle.length).toBeLessThanOrEqual(60);
    expect(firstTitle).toMatch(/…$/);
    expect(
      Array.from(firstTitle).some((ch) => {
        const code = ch.codePointAt(0) ?? 0;
        return (code >= 0x00 && code <= 0x1f) || (code >= 0x7f && code <= 0x9f);
      }),
    ).toBe(false);
    expect(Object.keys(notif.extra ?? {}).sort()).toEqual(["route", "v"]);

    const serialized = JSON.stringify(notif);
    expect(serialized).not.toContain("Secret Greenhouse Specimen");
    expect(serialized).not.toContain("Private shelf note");
    expect(serialized).not.toContain("secret.example.com");
    expect(serialized).not.toContain("Monstera");
  });

  it("handles overflow pages (total > 100) using count-only digests on truncated days", () => {
    const items = [
      makeActivity({
        id: "00000000-0000-4000-8000-000000000001",
        title: "Today task",
        due_on: "2026-05-01",
      }),
      makeActivity({
        id: "00000000-0000-4000-8000-000000000002",
        title: "Boundary task A",
        due_on: "2026-05-02",
      }),
      makeActivity({
        id: "00000000-0000-4000-8000-000000000003",
        title: "Boundary task B",
        due_on: "2026-05-02",
      }),
    ];
    const page = makePage(items, {
      today: "2026-05-01",
      today_count: 1,
      overdue_count: 0,
      total: 140,
    });

    const plan = buildReminderPlan(page, enabledSettings, {
      now: new Date("2026-05-01T06:00:00Z"),
      timeZone: "UTC",
    });

    expect(plan.notifications).toHaveLength(2);
    expect(plan.notifications[0]?.title).toBe("1 activity due today");
    expect(plan.notifications[0]?.inboxList).toEqual(["Today task"]);
    expect(plan.notifications[1]?.title).toBe(
      "At least 2 activities due today",
    );
    expect(plan.notifications[1]?.inboxList).toBeUndefined();
    expect(plan.notifications[1]?.extra).toEqual({
      route: REMINDER_DEFAULT_ROUTE,
      v: REMINDER_EXTRA_SCHEMA_VERSION,
    });
  });

  it("computes local wall-clock instants across Europe/Rome spring-forward and fall-back DST changes", () => {
    // Spring forward: 2026-03-29 clocks jump 02:00 CET -> 03:00 CEST (23-hour day)
    const beforeSpring = resolveWallClockInstant(
      "2026-03-28",
      8,
      0,
      "Europe/Rome",
    );
    const onSpring = resolveWallClockInstant("2026-03-29", 8, 0, "Europe/Rome");
    expect(beforeSpring.toISOString()).toBe("2026-03-28T07:00:00.000Z");
    expect(onSpring.toISOString()).toBe("2026-03-29T06:00:00.000Z");
    expect(onSpring.getTime() - beforeSpring.getTime()).toBe(23 * 3_600_000);

    // Nonexistent wall-clock time 02:30 on spring-forward Sunday -> next valid instant 03:00 CEST
    const springGap = resolveWallClockInstant(
      "2026-03-29",
      2,
      30,
      "Europe/Rome",
    );
    expect(springGap.toISOString()).toBe("2026-03-29T01:00:00.000Z");

    // Fall back: 2026-10-25 clocks repeat 02:00..02:59 (25-hour day)
    const beforeFall = resolveWallClockInstant(
      "2026-10-24",
      8,
      0,
      "Europe/Rome",
    );
    const onFall = resolveWallClockInstant("2026-10-25", 8, 0, "Europe/Rome");
    expect(beforeFall.toISOString()).toBe("2026-10-24T06:00:00.000Z");
    expect(onFall.toISOString()).toBe("2026-10-25T07:00:00.000Z");
    expect(onFall.getTime() - beforeFall.getTime()).toBe(25 * 3_600_000);

    // Ambiguous fall-back time 02:30 on 2026-10-25 -> first valid instant 02:30 CEST (00:30Z)
    const fallOverlap = resolveWallClockInstant(
      "2026-10-25",
      2,
      30,
      "Europe/Rome",
    );
    expect(fallOverlap.toISOString()).toBe("2026-10-25T00:30:00.000Z");
  });

  it("recomputes local calendar day and wall-clock trigger when time zone changes", () => {
    const now = new Date("2026-06-15T01:30:00Z");
    // In Europe/Rome (UTC+2), it is 2026-06-15 03:30; in America/New_York (UTC-4), it is 2026-06-14 21:30
    expect(getLocalDayInTimeZone(now, "Europe/Rome")).toBe("2026-06-15");
    expect(getLocalDayInTimeZone(now, "America/New_York")).toBe("2026-06-14");

    const item = makeActivity({
      id: "00000000-0000-4000-8000-000000000009",
      title: "Check moisture",
      due_on: "2026-06-15",
    });

    const romePlan = buildReminderPlan(
      makePage([item], { today: "2026-06-15", today_count: 1 }),
      enabledSettings,
      { now, timeZone: "Europe/Rome" },
    );
    const nyPlan = buildReminderPlan(
      makePage([item], { today: "2026-06-14", today_count: 0 }),
      enabledSettings,
      { now, timeZone: "America/New_York" },
    );

    expect(romePlan.notifications[0]?.schedule?.at).toBe(
      "2026-06-15T06:00:00.000Z",
    );
    expect(nyPlan.notifications[0]?.schedule?.at).toBe(
      "2026-06-15T12:00:00.000Z",
    );
  });

  it("validates route allowlist, title sanitizer, and owned ID range", () => {
    expect(validateReminderRoute("#/schedule?window=today")).toBe(
      "#/schedule?window=today",
    );
    expect(validateReminderRoute("#/schedule?window=overdue")).toBe(
      "#/schedule?window=overdue",
    );
    expect(validateReminderRoute("#/schedule?window=next_seven_days")).toBe(
      "#/schedule?window=next_seven_days",
    );
    expect(
      validateReminderRoute("#/schedule/12345678-1234-4123-8123-1234567890ab"),
    ).toBe("#/schedule/12345678-1234-4123-8123-1234567890ab");
    expect(validateReminderRoute("#/settings")).toBe(REMINDER_DEFAULT_ROUTE);
    expect(validateReminderRoute("javascript:alert(1)")).toBe(
      REMINDER_DEFAULT_ROUTE,
    );
    expect(validateReminderRoute(null)).toBe(REMINDER_DEFAULT_ROUTE);

    expect(sanitizeReminderTitle("  \x07Repot\r\nficus  ")).toBe("Repot ficus");

    expect(isOwnedReminderId(REMINDER_ID_BASE - 1)).toBe(false);
    expect(isOwnedReminderId(REMINDER_ID_BASE)).toBe(true);
    expect(isOwnedReminderId(REMINDER_ID_MAX)).toBe(true);
    expect(isOwnedReminderId(REMINDER_ID_MAX + 1)).toBe(false);
    expect(isOwnedReminderId(41000.5)).toBe(false);
  });
});
