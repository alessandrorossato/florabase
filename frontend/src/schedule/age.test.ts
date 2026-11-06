import { expect, test } from "vitest";
import type { Activity } from "./api";
import { activityAge, activityTone } from "./state";

const base = {
  status: "planned",
  due_on: "2026-11-05",
} as unknown as Activity;
const at = (due_on: string, status = "planned") =>
  ({ ...base, due_on, status }) as Activity;

test("planning distance is said in whole calendar days and only for planned work", () => {
  expect(activityAge(at("2026-11-05"), "2026-11-05")).toBe("Due today");
  expect(activityAge(at("2026-11-04"), "2026-11-05")).toBe("1 day overdue");
  expect(activityAge(at("2026-11-01"), "2026-11-05")).toBe("4 days overdue");
  expect(activityAge(at("2026-11-06"), "2026-11-05")).toBe("in 1 day");
  expect(activityAge(at("2027-01-02"), "2026-12-31")).toBe("in 2 days");
  expect(activityAge(at("2026-11-01", "completed"), "2026-11-05")).toBeNull();
  expect(activityAge(at("2026-11-01", "cancelled"), "2026-11-05")).toBeNull();
  expect(activityTone(at("2026-11-01"), "2026-11-05")).toBe("overdue");
  expect(activityTone(at("2026-11-05"), "2026-11-05")).toBe("today");
  expect(activityTone(at("2026-11-09"), "2026-11-05")).toBe("upcoming");
  expect(activityTone(at("2026-11-01", "completed"), "2026-11-05")).toBe(
    "completed",
  );
});
