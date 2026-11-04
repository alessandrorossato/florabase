import { expect, test } from "vitest";

import {
  almanacWindow,
  dayPosition,
  partialMark,
  precisionGroups,
  type PartialDate,
} from "./almanac";

const day = (year: number, month: number, d: number): PartialDate => ({
  precision: "day",
  year,
  month,
  day: d,
});
const month = (year: number, m: number): PartialDate => ({
  precision: "month",
  year,
  month: m,
  day: null,
});
const year = (y: number): PartialDate => ({
  precision: "year",
  year: y,
  month: null,
  day: null,
});

test("the window ends at today or the latest entry and spans at most twelve months", () => {
  const range = almanacWindow(
    [month(2026, 9), null],
    ["2026-11-04"],
    "2026-11-04",
  );
  expect(range?.months.map((m) => m.label)).toEqual(["Sep", "Oct", "Nov"]);
  const long = almanacWindow([year(2020)], ["2026-12-01"], "2026-11-04");
  expect(long?.months).toHaveLength(12);
  expect(long?.months.at(-1)?.label).toBe("Dec");
  expect(almanacWindow([null], [], "2026-11-04")).toBeNull();
});

test("a day is a point; a month or year is a span; nothing is padded to a day", () => {
  const range = almanacWindow([], ["2026-12-31"], "2026-01-01");
  if (!range) throw new Error("window");
  expect(partialMark(range, day(2026, 1, 1))).toEqual({ kind: "day", left: 0 });
  expect(partialMark(range, month(2026, 6))).toEqual({
    kind: "span",
    left: (5 / 12) * 100,
    width: (1 / 12) * 100,
  });
  expect(partialMark(range, year(2026))).toEqual({
    kind: "span",
    left: 0,
    width: 100,
  });
  // Outside the window: not drawn (the list still shows it).
  expect(partialMark(range, day(2025, 12, 31))).toBeNull();
  expect(dayPosition(range, "2027-01-01")).toBeNull();
});

test("Journal entries group by the precision actually recorded, in API order", () => {
  const groups = precisionGroups([
    { id: "a", occurred_on: day(2026, 11, 4) },
    { id: "b", occurred_on: day(2026, 11, 1) },
    { id: "c", occurred_on: month(2026, 9) },
    { id: "d", occurred_on: year(2024) },
    { id: "e", occurred_on: null },
  ]);
  expect(groups.map((g) => [g.heading, g.entries.map((e) => e.id)])).toEqual([
    ["November 2026", ["a", "b"]],
    ["September 2026 · day not recorded", ["c"]],
    ["2024 · month not recorded", ["d"]],
    ["Date not recorded", ["e"]],
  ]);
});
