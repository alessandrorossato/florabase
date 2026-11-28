import { expect, test } from "vitest";

import { daysLabel, daysSince } from "./keyFactValues";

test("UI-POLISH-006 B2: day counts need a day-precise date and never go negative", () => {
  const today = new Date(2026, 10, 27);
  expect(
    daysSince({ precision: "day", year: 2026, month: 8, day: 7 }, today),
  ).toBe(112);
  expect(
    daysSince({ precision: "month", year: 2026, month: 8, day: null }, today),
  ).toBeNull();
  expect(daysSince(null, today)).toBeNull();
  expect(
    daysSince({ precision: "day", year: 2026, month: 12, day: 1 }, today),
  ).toBeNull();
  expect(daysLabel(1)).toBe("1 day");
  expect(daysLabel(112)).toBe("112 days");
});
