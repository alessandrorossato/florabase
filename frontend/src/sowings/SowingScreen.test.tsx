import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "../App";

const identityId = "01900000-0000-7000-8000-000000000101";
const seedLotId = "01900000-0000-7000-8000-000000000201";
const inactiveSeedLotId = "01900000-0000-7000-8000-000000000202";
const locationId = "01900000-0000-7000-8000-000000000301";
const sowingId = "01900000-0000-7000-8000-000000000401";

const identity = {
  id: identityId,
  scientific_name: "Clitoria ternatea",
  cultivar_name: null,
  common_name: "Butterfly pea",
  display_label: "Clitoria ternatea",
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};

function seedLot(id = seedLotId, lifecycle = "active") {
  return {
    id,
    botanical_identity_id: identityId,
    botanical_identity: {
      id: identityId,
      display_label: identity.display_label,
    },
    label: id === seedLotId ? "Blue packet" : "Archive packet",
    source_kind: "unknown",
    source_detail: null,
    supplier_id: null,
    supplier: null,
    material_provenance_place_id: null,
    material_provenance: null,
    acquisition_date: null,
    harvest_date: null,
    quantity: null,
    expected_viability_until: null,
    location_id: null,
    location: null,
    lifecycle,
    notes: null,
    created_at: "2026-08-31T10:00:00Z",
    updated_at: "2026-08-31T10:00:00Z",
  };
}

const location = {
  id: locationId,
  name: "Tray shelf",
  parent_id: null,
  display_path: "Greenhouse → Tray shelf",
  retired_at: null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};

function sowing(overrides: Record<string, unknown> = {}) {
  return {
    id: sowingId,
    seed_lot_id: seedLotId,
    seed_lot: {
      id: seedLotId,
      label: "Blue packet",
      lifecycle: "active",
      botanical_identity_id: identityId,
      botanical_identity_display_label: "Clitoria ternatea",
    },
    label: "Tray A",
    sowing_date: { precision: "month", year: 2026, month: 8 },
    quantity: {
      kind: "seed_count",
      value: "20",
      unit: null,
      is_approximate: false,
    },
    germinated_count: 12,
    location_id: locationId,
    location: { id: locationId, display_path: location.display_path },
    substrate: "Coco coir",
    method_container: "Covered tray",
    pretreatment: "Scarified",
    temperature_min_c: "20.5",
    temperature_max_c: "28",
    environment: "Bright shade",
    lifecycle: "active",
    notes: "Check daily.",
    created_at: "2026-08-31T10:00:00Z",
    updated_at: "2026-08-31T10:00:00Z",
    ...overrides,
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

type Handler = (
  path: string,
  init?: RequestInit,
) => Response | Promise<Response> | undefined;

function body(init?: RequestInit): Record<string, unknown> {
  if (typeof init?.body !== "string") throw new Error("Expected JSON body");
  return JSON.parse(init.body) as Record<string, unknown>;
}

function mockApi(handler: Handler) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        json({
          user_id: "user",
          login_name: "owner",
          display_name: "Owner",
          owner: true,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(json({ csrf_token: "csrf" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    if (path === "/api/v1/botanical-identities")
      return Promise.resolve(json([identity]));
    const response = handler(path, init);
    if (!response)
      throw new Error(`Unhandled request: ${path} ${init?.method ?? "GET"}`);
    return Promise.resolve(response);
  });
}

function sowingHandler(sowings: unknown[], custom?: Handler): Handler {
  return (path, init) => {
    const customResponse = custom?.(path, init);
    if (customResponse !== undefined) return customResponse;
    if (path === "/api/v1/sowings" && (!init?.method || init.method === "GET"))
      return json(sowings);
    if (
      path.startsWith("/api/v1/sowings/") &&
      (!init?.method || init.method === "GET")
    ) {
      const id = path.split("/").at(-1);
      const match = sowings.find(
        (item) =>
          typeof item === "object" &&
          item !== null &&
          "id" in item &&
          item.id === id,
      );
      return match ? json(match) : json({ detail: "not found" }, 404);
    }
    if (path === "/api/v1/seed-lots")
      return json([seedLot(), seedLot(inactiveSeedLotId, "discarded")]);
    if (path === "/api/v1/locations") return json([location]);
    return undefined;
  };
}

async function openSowings() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "Sowings" }));
  return user;
}

beforeEach(() => {
  window.history.replaceState(null, "", "#/dashboard");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("navigation exposes loading, empty, and missing-SeedLot states", async () => {
  mockApi((path) => {
    if (path === "/api/v1/sowings")
      return new Promise<Response>(() => undefined);
    if (path === "/api/v1/seed-lots" || path === "/api/v1/locations")
      return json([]);
    return undefined;
  });
  await openSowings();
  expect(screen.getByRole("status")).toHaveTextContent("Loading Sowings");

  cleanup();
  vi.restoreAllMocks();
  mockApi(
    sowingHandler([], (path) =>
      path === "/api/v1/seed-lots" ? json([]) : undefined,
    ),
  );
  await openSowings();
  expect(
    await screen.findByRole("heading", { name: "No Sowings recorded yet" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "+ New Sowing" })).toBeDisabled();
  expect(screen.getByText(/SeedLot is required/)).toBeInTheDocument();
});

test("list failure is explicit and retryable", async () => {
  mockApi((path) => {
    if (path === "/api/v1/sowings") return json({ detail: "failed" }, 500);
    if (path === "/api/v1/seed-lots" || path === "/api/v1/locations")
      return json([]);
    return undefined;
  });
  await openSowings();
  expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

test("compact summaries, search fields, lifecycle views, selection, detail, and Back are accessible", async () => {
  const completed = sowing({
    id: "history",
    label: "GA3 test",
    lifecycle: "completed",
    seed_lot: {
      ...sowing().seed_lot,
      label: "Archive packet",
      botanical_identity_display_label: "Solanum quitoense",
    },
    location: { id: locationId, display_path: "Cold frame → West" },
    quantity: {
      kind: "seed_count",
      value: "20",
      unit: null,
      is_approximate: true,
    },
  });
  mockApi(sowingHandler([sowing(), completed]));
  const user = await openSowings();
  await screen.findByRole("button", {
    name: /Clitoria ternatea.*Tray A.*12 germinated \/ 20 sown/s,
  });
  expect(screen.queryByText("GA3 test")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "History" }));
  expect(screen.getByText("GA3 test")).toBeInTheDocument();
  expect(screen.getByText("12 germinated / ~20 sown")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "All" }));

  const search = screen.getByRole("searchbox", { name: "Search Sowings" });
  for (const query of ["Clitoria", "Tray A", "Tray shelf", "Blue packet"]) {
    await user.clear(search);
    await user.type(search, query);
    expect(screen.getByText("Tray A")).toBeInTheDocument();
  }
  await user.clear(search);
  const selectedRow = screen.getByRole("button", {
    name: /Clitoria ternatea.*Tray A.*12 germinated \/ 20 sown/s,
  });
  await user.click(selectedRow);
  expect(
    await screen.findByRole("heading", { name: "Clitoria ternatea" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Coco coir")).toBeInTheDocument();
  expect(screen.getByText("20.5–28 °C")).toBeInTheDocument();
  expect(screen.getByText("Check daily.")).toBeInTheDocument();
  const back = screen.getByRole("button", { name: "← Back to Sowings" });
  await user.click(back);
  expect(selectedRow).toHaveFocus();
});

test("detail loading and failure have semantic states", async () => {
  let rejectDetail = false;
  mockApi(
    sowingHandler([sowing()], (path) => {
      if (path === `/api/v1/sowings/${sowingId}`) {
        if (rejectDetail) return json({ detail: "failed" }, 500);
        return new Promise<Response>(() => undefined);
      }
      return undefined;
    }),
  );
  const user = await openSowings();
  await user.click(
    await screen.findByRole("button", { name: /Clitoria ternatea/ }),
  );
  expect(screen.getByRole("status")).toHaveTextContent("Loading Sowing detail");

  cleanup();
  vi.restoreAllMocks();
  rejectDetail = true;
  mockApi(
    sowingHandler([sowing()], (path) =>
      path === `/api/v1/sowings/${sowingId}`
        ? json({ detail: "failed" }, 500)
        : undefined,
    ),
  );
  const retryUser = await openSowings();
  await retryUser.click(
    await screen.findByRole("button", { name: /Clitoria ternatea/ }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not load this Sowing",
  );
  expect(
    screen.getByRole("button", { name: "Retry detail" }),
  ).toBeInTheDocument();
});

test("minimal creation requires only an understandable SeedLot choice", async () => {
  const payloads: Record<string, unknown>[] = [];
  let records: unknown[] = [];
  mockApi(
    sowingHandler(records, (path, init) => {
      if (path === "/api/v1/sowings" && init?.method === "POST") {
        payloads.push(body(init));
        const created = sowing({ ...payloads.at(-1), id: "created" });
        records = [created];
        expect(new Headers(init.headers).get("X-CSRF-Token")).toBe("csrf");
        return json(created, 201);
      }
      if (
        path === "/api/v1/sowings" &&
        (!init?.method || init.method === "GET")
      )
        return json(records);
      if (path === "/api/v1/sowings/created") return json(records[0]);
      return undefined;
    }),
  );
  const user = await openSowings();
  const trigger = await screen.findByRole("button", { name: "+ New Sowing" });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  await user.click(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  const selector = screen.getByLabelText("SeedLot");
  expect(
    within(selector).getByRole("option", {
      name: /Clitoria ternatea · Blue packet/,
    }),
  ).toBeInTheDocument();
  expect(
    within(selector).getByRole("option", {
      name: /Archive packet · discarded/,
    }),
  ).toBeInTheDocument();
  await user.selectOptions(selector, seedLotId);
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByText("Sowing was recorded.")).toBeInTheDocument();
  expect(payloads[0]).toMatchObject({
    seed_lot_id: seedLotId,
    label: null,
    sowing_date: null,
    quantity: null,
    germinated_count: null,
    lifecycle: "active",
  });
});

test("full creation preserves partial dates, quantity kinds, germination, location, and cultivation fields", async () => {
  const payloads: Record<string, unknown>[] = [];
  let records: unknown[] = [];
  mockApi(
    sowingHandler(records, (path, init) => {
      if (path === "/api/v1/sowings" && init?.method === "POST") {
        const payload = body(init);
        payloads.push(payload);
        const created = sowing({
          ...payload,
          id: `created-${String(payloads.length)}`,
        });
        records = [created];
        return json(created, 201);
      }
      if (
        path === "/api/v1/sowings" &&
        (!init?.method || init.method === "GET")
      )
        return json(records);
      if (path.startsWith("/api/v1/sowings/")) return json(records[0]);
      return undefined;
    }),
  );
  const user = await openSowings();
  await user.click(await screen.findByRole("button", { name: "+ New Sowing" }));
  await user.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
  await user.type(screen.getByLabelText("Sowing label (optional)"), "Heat mat");
  await user.selectOptions(screen.getByLabelText("Precision"), "year");
  await user.clear(screen.getByLabelText("Year"));
  await user.type(screen.getByLabelText("Year"), "2024");
  await user.selectOptions(screen.getByLabelText("Kind"), "weight");
  await user.type(screen.getByLabelText("Amount"), "2.50");
  await user.selectOptions(screen.getByLabelText("Unit"), "mg");
  await user.click(screen.getByLabelText("Approximate"));
  await user.click(screen.getByRole("button", { name: "More details" }));
  await user.type(screen.getByLabelText("Germinated count (optional)"), "12");
  await user.selectOptions(
    screen.getByLabelText("Current location (optional)"),
    locationId,
  );
  await user.type(screen.getByLabelText("Substrate (optional)"), "Sand");
  await user.type(
    screen.getByLabelText("Method / container (optional)"),
    "Tray",
  );
  await user.type(screen.getByLabelText("Pretreatment (optional)"), "Soaked");
  await user.type(screen.getByLabelText("Minimum °C"), "-2.5");
  await user.type(screen.getByLabelText("Maximum °C"), "24");
  await user.type(
    screen.getByLabelText("Environment / conditions (optional)"),
    "Outside",
  );
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "completed");
  await user.type(
    screen.getByLabelText("Notes (optional)"),
    "Historical entry",
  );
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  await screen.findByText("Sowing was recorded.");
  expect(payloads[0]).toMatchObject({
    label: "Heat mat",
    sowing_date: { precision: "year", year: 2024 },
    quantity: {
      kind: "weight",
      value: "2.50",
      unit: "mg",
      is_approximate: true,
    },
    germinated_count: 12,
    location_id: locationId,
    temperature_min_c: "-2.5",
    temperature_max_c: "24",
    lifecycle: "completed",
  });
});

test.each([
  ["year", { precision: "year", year: 2024 }],
  ["month", { precision: "month", year: 2024, month: 1 }],
  ["day", { precision: "day", year: 2024, month: 1, day: 1 }],
] as const)(
  "Sowing date preserves %s precision",
  async (precision, expected) => {
    let submitted: Record<string, unknown> | null = null;
    let records: unknown[] = [];
    mockApi(
      sowingHandler(records, (path, init) => {
        if (path === "/api/v1/sowings" && init?.method === "POST") {
          submitted = body(init);
          const created = sowing({ ...submitted, id: `created-${precision}` });
          records = [created];
          return json(created, 201);
        }
        if (
          path === "/api/v1/sowings" &&
          (!init?.method || init.method === "GET")
        )
          return json(records);
        if (path.startsWith("/api/v1/sowings/")) return json(records[0]);
        return undefined;
      }),
    );
    const user = await openSowings();
    await user.click(
      await screen.findByRole("button", { name: "+ New Sowing" }),
    );
    await user.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
    await user.selectOptions(screen.getByLabelText("Precision"), precision);
    await user.clear(screen.getByLabelText("Year"));
    await user.type(screen.getByLabelText("Year"), "2024");
    await user.click(screen.getByRole("button", { name: "Record Sowing" }));
    await screen.findByText("Sowing was recorded.");
    expect(submitted).toMatchObject({ sowing_date: expected });
  },
);

test("germination and temperature validation applies only to trustworthy bounds", async () => {
  let posts = 0;
  mockApi(
    sowingHandler([], (path, init) => {
      if (path === "/api/v1/sowings" && init?.method === "POST") {
        posts += 1;
        return json(
          sowing({ ...body(init), id: `created-${String(posts)}` }),
          201,
        );
      }
      return undefined;
    }),
  );
  const user = await openSowings();
  await user.click(await screen.findByRole("button", { name: "+ New Sowing" }));
  await user.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
  await user.selectOptions(screen.getByLabelText("Kind"), "seed_count");
  await user.type(screen.getByLabelText("Amount"), "10");
  await user.click(screen.getByRole("button", { name: "More details" }));
  await user.type(screen.getByLabelText("Germinated count (optional)"), "12");
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "cannot exceed an exact seed count",
  );
  expect(posts).toBe(0);

  await user.click(screen.getByLabelText("Approximate"));
  await user.type(screen.getByLabelText("Minimum °C"), "30");
  await user.type(screen.getByLabelText("Maximum °C"), "20");
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Minimum temperature cannot be greater",
  );
  expect(posts).toBe(0);
  await user.clear(screen.getByLabelText("Minimum °C"));
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(posts).toBe(1);

  cleanup();
  vi.restoreAllMocks();
  posts = 0;
  mockApi(
    sowingHandler([], (path, init) => {
      if (path === "/api/v1/sowings" && init?.method === "POST") {
        posts += 1;
        return json(sowing({ ...body(init), id: "weighted" }), 201);
      }
      return undefined;
    }),
  );
  const weightUser = await openSowings();
  await weightUser.click(
    await screen.findByRole("button", { name: "+ New Sowing" }),
  );
  await weightUser.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
  await weightUser.selectOptions(screen.getByLabelText("Kind"), "weight");
  await weightUser.type(screen.getByLabelText("Amount"), "2");
  await weightUser.click(screen.getByRole("button", { name: "More details" }));
  await weightUser.type(
    screen.getByLabelText("Germinated count (optional)"),
    "12",
  );
  await weightUser.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(posts).toBe(1);
});

test("the single full editor preserves exact values and failed edits, then changes lifecycle", async () => {
  const updates: Record<string, unknown>[] = [];
  let current = sowing();
  let fail = true;
  mockApi(
    sowingHandler([current], (path, init) => {
      if (path === `/api/v1/sowings/${sowingId}` && init?.method === "PUT") {
        updates.push(body(init));
        if (fail) return json({ detail: "failure" }, 500);
        current = sowing({ ...updates.at(-1) });
        return json(current);
      }
      if (
        path === "/api/v1/sowings" &&
        (!init?.method || init.method === "GET")
      )
        return json([current]);
      return undefined;
    }),
  );
  const user = await openSowings();
  await user.click(
    await screen.findByRole("button", { name: /Clitoria ternatea/ }),
  );
  await screen.findByRole("button", { name: "Edit Sowing" });
  await user.click(screen.getByRole("button", { name: "Edit Sowing" }));
  expect(screen.getByLabelText("Amount")).toHaveValue("20");
  expect(screen.getByLabelText("Minimum °C")).toHaveValue("20.5");
  await user.clear(screen.getByLabelText("Sowing label (optional)"));
  await user.type(
    screen.getByLabelText("Sowing label (optional)"),
    "Unsaved correction",
  );
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "failed");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not save or refresh",
  );
  expect(screen.getByLabelText("Sowing label (optional)")).toHaveValue(
    "Unsaved correction",
  );
  fail = false;
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(
    await screen.findByText("Sowing changes were saved."),
  ).toBeInTheDocument();
  expect(updates.at(-1)).toMatchObject({
    lifecycle: "failed",
    label: "Unsaved correction",
  });
  expect(screen.getAllByText("Failed").length).toBeGreaterThan(0);
});

test("validation, forbidden, and expired-session API failures remain explicit", async () => {
  let mode: "validation" | "forbidden" | "session" = "validation";
  mockApi(
    sowingHandler([], (path, init) => {
      if (path === "/api/v1/sowings" && init?.method === "POST") {
        if (mode === "validation")
          return json(
            {
              detail: [
                {
                  loc: ["body", "quantity"],
                  msg: "greater than 0",
                  type: "value_error",
                },
              ],
            },
            422,
          );
        if (mode === "forbidden") return json({ detail: "forbidden" }, 403);
        return json({ detail: "expired" }, 401);
      }
      return undefined;
    }),
  );
  const user = await openSowings();
  await user.click(await screen.findByRole("button", { name: "+ New Sowing" }));
  await user.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Quantity sown must be greater than zero",
  );
  mode = "forbidden";
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not authorize",
  );
  mode = "session";
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/session expired/)).toBeInTheDocument();
});
