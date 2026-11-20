import { afterEach, expect, test, vi } from "vitest";
import { acquireTestAuth } from "../test/auth";
import { listSchedule, listCalendar, type SchedulePage } from "./api";
import { readScheduleState } from "./state";

afterEach(() => {
  vi.restoreAllMocks();
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });
}

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
  const { capability } = await acquireTestAuth();
  const first = page(0, 101);
  first.items = Array.from(
    { length: 100 },
    (_, n) => ({ id: String(n) }) as SchedulePage["items"][number],
  );
  const second = page(100, 101);
  second.items = [{ id: "100" } as SchedulePage["items"][number]];
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(jsonResponse(first))
    .mockResolvedValueOnce(jsonResponse(second));
  const controller = new AbortController();
  const signal = controller.signal;
  const result = await listCalendar(
    readScheduleState(
      "#/schedule?view=calendar&month=2024-02&activity_kind=inspect&target_kind=location&q=bench",
    ),
    capability,
    signal,
  );
  expect(result.items).toHaveLength(101);
  expect(result.today).toBe("2024-02-29");
  expect(fetch).toHaveBeenCalledTimes(2);
  const urls = fetch.mock.calls.map(
    ([url]) =>
      new URL(
        typeof url === "string" ? url : url instanceof URL ? url.href : url.url,
        "http://localhost",
      ),
  );
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
  expect(fetch).toHaveBeenLastCalledWith(
    expect.any(String),
    expect.objectContaining({
      credentials: "same-origin",
      signal: expect.any(AbortSignal) as AbortSignal,
    }),
  );
  let abortableSignal: AbortSignal | undefined;
  fetch.mockImplementationOnce(
    (_url, init) =>
      new Promise<Response>((_resolve, reject) => {
        abortableSignal = init?.signal ?? undefined;
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      }),
  );
  const abortedCall = listCalendar(
    readScheduleState("#/schedule?view=calendar&month=2024-02"),
    capability,
    signal,
  ).catch(() => undefined);
  await Promise.resolve();
  expect(abortableSignal?.aborted).toBe(false);
  controller.abort();
  await abortedCall;
  expect(abortableSignal?.aborted).toBe(true);
});
test("invalid or failed period responses surface a recoverable error", async () => {
  const { capability } = await acquireTestAuth();
  const state = readScheduleState("#/schedule?view=calendar&month=2026-12");
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(jsonResponse({ total: -1, items: [] }))
    .mockRejectedValueOnce(new Error("Network"));
  await expect(listCalendar(state, capability)).rejects.toThrow(
    "Invalid Schedule response",
  );
  await expect(listCalendar(state, capability)).rejects.toThrow("Network");
  expect(fetch).toHaveBeenCalledTimes(2);
});

test("Schedule sends every selected value and unrestricted statuses as real stored enum values", async () => {
  const { capability } = await acquireTestAuth();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() => Promise.resolve(jsonResponse(page(0, 0))));
  await listCalendar(
    readScheduleState(
      "#/schedule?status=cancelled&status=planned&activity_kind=inspect&activity_kind=water&target_kind=plant&target_kind=seed_lot&window=today&q=needle&view=calendar&month=2024-02",
    ),
    capability,
  );
  let callUrl = fetch.mock.calls[0][0];
  let url = new URL(
    typeof callUrl === "string"
      ? callUrl
      : callUrl instanceof URL
        ? callUrl.href
        : callUrl.url,
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
    capability,
  );
  callUrl = fetch.mock.calls[1][0];
  url = new URL(
    typeof callUrl === "string"
      ? callUrl
      : callUrl instanceof URL
        ? callUrl.href
        : callUrl.url,
    "http://localhost",
  );
  expect(url.searchParams.getAll("status")).toEqual([
    "planned",
    "completed",
    "cancelled",
  ]);
  expect(url.searchParams.getAll("status")).not.toContain("all");
});

test("selected-day Agenda uses server bounds rather than filtering a loaded page", async () => {
  const { capability } = await acquireTestAuth();
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() => Promise.resolve(jsonResponse(page(0, 0))));
  await listSchedule(
    readScheduleState("#/schedule?date=2024-02-29&month=2024-02&q=aloe"),
    50,
    50,
    capability,
    undefined,
    "2024-02-29",
  );
  const rawCallUrl = fetch.mock.calls[0][0];
  const url = new URL(
    typeof rawCallUrl === "string"
      ? rawCallUrl
      : rawCallUrl instanceof URL
        ? rawCallUrl.href
        : rawCallUrl.url,
    "http://localhost",
  );
  expect(url.searchParams.get("due_from")).toBe("2024-02-29");
  expect(url.searchParams.get("due_to")).toBe("2024-02-29");
  expect(url.searchParams.get("offset")).toBe("50");
  expect(url.searchParams.get("q")).toBe("aloe");
});
