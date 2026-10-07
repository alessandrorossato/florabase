import { afterEach, expect, test, vi } from "vitest";
import { applyLocation, previewLocation, type BulkPreview } from "./api";
afterEach(() => {
  vi.restoreAllMocks();
});
test("bulk requests send only exact typed references and validated preview preconditions", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      Promise.resolve(
        new Response("{}", { headers: { "Content-Type": "application/json" } }),
      ),
    );
  await previewLocation(
    [
      { kind: "plant", id: "same-uuid" },
      { kind: "plant_group", id: "same-uuid" },
    ],
    "location",
    "csrf",
  );
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/bulk/location/preview");
  const request = fetch.mock.calls[0][1];
  expect(request?.credentials).toBe("same-origin");
  expect(new Headers(request?.headers).get("X-CSRF-Token")).toBe("csrf");
  expect(requestBody(request)).toEqual({
    target_location_id: "location",
    records: [
      { kind: "plant", id: "same-uuid" },
      { kind: "plant_group", id: "same-uuid" },
    ],
  });
  const preview = {
    target_location_id: "location",
    target_updated_at: "2026-10-06T00:00:00Z",
    rows: [
      {
        kind: "plant",
        id: "plant",
        updated_at: "2026-10-06T01:00:00Z",
        label: "Basil",
        status: "move",
      },
      {
        kind: "plant_group",
        id: "group",
        updated_at: "2026-10-06T02:00:00Z",
        label: "Basil group",
        status: "unchanged",
      },
    ],
  } as BulkPreview;
  await applyLocation(preview, "csrf");
  expect(fetch.mock.calls[1][0]).toBe("/api/v1/bulk/location/apply");
  expect(requestBody(fetch.mock.calls[1][1])).toEqual({
    target_location_id: "location",
    expected_target_updated_at: "2026-10-06T00:00:00Z",
    records: [
      {
        kind: "plant",
        id: "plant",
        expected_updated_at: "2026-10-06T01:00:00Z",
      },
      {
        kind: "plant_group",
        id: "group",
        expected_updated_at: "2026-10-06T02:00:00Z",
      },
    ],
  });
});

function requestBody(init?: RequestInit): unknown {
  if (typeof init?.body !== "string") throw new Error("Expected JSON body");
  return JSON.parse(init.body) as unknown;
}
