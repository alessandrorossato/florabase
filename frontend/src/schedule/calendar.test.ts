import { expect, test } from "vitest";
import {
  calendarDate,
  dayLabel,
  localDay,
  monthDays,
  shiftMonth,
  validDay,
} from "./calendar";
import { readScheduleState, scheduleHash } from "./state";

test("local calendar arithmetic preserves leap days and month/year boundaries", () => {
  expect(monthDays("2024-02")).toHaveLength(29);
  expect(monthDays("2026-02")).toHaveLength(28);
  expect(monthDays("2024-02").at(-1)).toBe("2024-02-29");
  expect(shiftMonth("2026-12", 1)).toBe("2027-01");
  expect(shiftMonth("2027-01", -1)).toBe("2026-12");
  expect(localDay(calendarDate("2024-02-29"))).toBe("2024-02-29");
  expect(localDay(calendarDate("0001-01-01"))).toBe("0001-01-01");
  expect(monthDays("9999-12")).toHaveLength(31);
  expect(dayLabel("2024-03-31")).toBe("Sunday, 31 March 2024");
  expect(validDay("2026-02-29")).toBe(false);
});
test("calendar URL round-trips valid state and discards impossible/out-of-month selections", () => {
  const state = readScheduleState(
    "#/schedule?target_kind=location&status=completed&view=calendar&month=2024-02&date=2024-02-29",
  );
  expect(readScheduleState(scheduleHash(state))).toEqual(state);
  expect(
    readScheduleState("#/schedule?view=calendar&month=2024-02&date=2024-03-01")
      .date,
  ).toBe("");
  expect(
    readScheduleState("#/schedule?view=calendar&month=2026-02&date=2026-02-29")
      .date,
  ).toBe("");
  expect(readScheduleState("#/schedule?view=week&month=0000-13").view).toBe(
    "list",
  );
  expect(
    readScheduleState("#/schedule?view=calendar&month=0000-13").month,
  ).toBe(localDay().slice(0, 7));
});
