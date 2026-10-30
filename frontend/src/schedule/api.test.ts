import { beforeEach, expect, test, vi } from "vitest";
import { requestJson } from "../auth/api";
import { listSchedule, listCalendar, type SchedulePage } from "./api";
import { readScheduleState } from "./state";
vi.mock("../auth/api", () => ({ requestJson: vi.fn() }));
beforeEach(() => {
  vi.resetAllMocks();
});
function page(offset: number, total: number): SchedulePage {
  return {
    items: [],
    offset,
    total,
    limit: 100,
    today: "2024-02-29",
    today_count: 0,
    overdue_count: 0,
  };
}
test("bounded visible-month pages preserve filters, stable projection day and batched target labels", async () => {
  const first = page(0, 101);
  first.items = Array.from(
    { length: 100 },
    (_, n) => ({ id: String(n) }) as SchedulePage["items"][number],
  );
  const second = page(100, 101);
  second.items = [{ id: "100" } as SchedulePage["items"][number]];
  vi.mocked(requestJson)
    .mockResolvedValueOnce(first)
    .mockResolvedValueOnce(second);
  const signal = new AbortController().signal;
  const result = await listCalendar(
    readScheduleState(
      "#/schedule?view=calendar&month=2024-02&activity_kind=inspect&target_kind=location&q=bench",
    ),
    signal,
  );
  expect(result.items).toHaveLength(101);
  expect(result.today).toBe("2024-02-29");
  expect(requestJson).toHaveBeenCalledTimes(2);
  const urls = vi
    .mocked(requestJson)
    .mock.calls.map(([url]) => new URL(url, "http://localhost"));
  for (const url of urls) {
    expect(url.searchParams.get("due_from")).toBe("2024-02-01");
    expect(url.searchParams.get("due_to")).toBe("2024-02-29");
    expect(url.searchParams.get("limit")).toBe("100");
    expect(url.searchParams.get("target_kind")).toBe("location");
    expect(url.searchParams.get("activity_kind")).toBe("inspect");
    expect(url.searchParams.get("q")).toBe("bench");
    expect(url.searchParams.has("view")).toBe(false);
  }
  expect(urls[1]?.searchParams.get("offset")).toBe("100");
  expect(urls[0]?.searchParams.get("today")).toBe(
    urls[1]?.searchParams.get("today"),
  );
  expect(requestJson).toHaveBeenLastCalledWith(expect.any(String), { signal });
});
test("invalid or failed period responses surface a recoverable error", async () => {
  const state = readScheduleState("#/schedule?view=calendar&month=2026-12");
  vi.mocked(requestJson).mockResolvedValueOnce({ total: -1, items: [] });
  await expect(listCalendar(state)).rejects.toThrow(
    "Invalid Schedule response",
  );
  vi.mocked(requestJson).mockRejectedValueOnce(new Error("Network"));
  await expect(listCalendar(state)).rejects.toThrow("Network");
});

test("Schedule sends every selected value and unrestricted statuses as real stored enum values", async () => {
  vi.mocked(requestJson).mockResolvedValue(page(0, 0));
  await listCalendar(
    readScheduleState(
      "#/schedule?status=cancelled&status=planned&activity_kind=inspect&activity_kind=water&target_kind=plant&target_kind=seed_lot&window=today&q=needle&view=calendar&month=2024-02",
    ),
  );
  let url = new URL(
    vi.mocked(requestJson).mock.calls[0][0],
    "http://localhost",
  );
  expect(url.searchParams.getAll("status")).toEqual(["planned", "cancelled"]);
  expect(url.searchParams.getAll("activity_kind")).toEqual([
    "water",
    "inspect",
  ]);
  expect(url.searchParams.getAll("target_kind")).toEqual(["seed_lot", "plant"]);
  expect(url.searchParams.get("window")).toBe("today");
  expect(url.searchParams.get("q")).toBe("needle");
  await listCalendar(
    readScheduleState(
      "#/schedule?status=planned&status=completed&status=cancelled&view=calendar&month=2024-02",
    ),
  );
  url = new URL(vi.mocked(requestJson).mock.calls[1][0], "http://localhost");
  expect(url.searchParams.getAll("status")).toEqual([
    "planned",
    "completed",
    "cancelled",
  ]);
  expect(url.searchParams.getAll("status")).not.toContain("all");
});

test("selected-day Agenda uses server bounds rather than filtering a loaded page", async () => {
  vi.mocked(requestJson).mockResolvedValue(page(0, 0));
  await listSchedule(
    readScheduleState("#/schedule?date=2024-02-29&month=2024-02&q=aloe"),
    50,
    50,
    undefined,
    "2024-02-29",
  );
  const url = new URL(
    vi.mocked(requestJson).mock.calls[0][0],
    "http://localhost",
  );
  expect(url.searchParams.get("due_from")).toBe("2024-02-29");
  expect(url.searchParams.get("due_to")).toBe("2024-02-29");
  expect(url.searchParams.get("offset")).toBe("50");
  expect(url.searchParams.get("q")).toBe("aloe");
});
