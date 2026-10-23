import { browserBack } from "../test/history";
import { openFormSection } from "../test/formSections";
import { selectDirectoryFilter } from "../test/directoryFilters";
import {
  act,
  fireEvent,
  waitFor,
  cleanup,
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "../App";
// These cases exercise Sowing interactions; App.lazy.test.tsx owns chunk loading.
import "./SowingScreen";

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

function setViewportMatches(matches: boolean) {
  vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

async function openSowings() {
  // Existing interaction cases exercise the list-to-detail mobile path.
  setViewportMatches(true);
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    within(
      await screen.findByRole("navigation", { name: "Primary navigation" }),
    ).getByRole("link", { name: "Sowings" }),
  );
  await screen.findByRole("heading", { name: "Sowings", level: 2 });
  return user;
}

beforeEach(() => {
  window.history.replaceState(null, "", "#/dashboard");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("germination tab keeps simple and dated totals distinct and supports correction", async () => {
  const observationId = "01900000-0000-7000-8000-000000000501";
  let observations: {
    id: string;
    observed_on: string;
    newly_germinated_count: number;
    created_at: string;
    updated_at: string;
  }[] = [];
  const germination = () => ({
    sowing_id: sowingId,
    sowing_date: { precision: "day", year: 2026, month: 4, day: 10 },
    quantity: {
      kind: "seed_count",
      value: "20",
      unit: null,
      is_approximate: false,
    },
    simple_germinated_count: 12,
    observations,
    summary: {
      observed_cumulative_count: observations[0]?.newly_germinated_count ?? 0,
      first_germination_on: observations[0]?.newly_germinated_count
        ? observations[0].observed_on
        : null,
      days_to_first_germination: observations[0]?.newly_germinated_count
        ? 4
        : null,
      last_observation_on: observations[0]?.observed_on ?? null,
      germination_percentage: observations.length ? "40" : null,
      cumulative_series: observations.map((item) => ({
        observed_on: item.observed_on,
        newly_germinated_count: item.newly_germinated_count,
        cumulative_germinated_count: item.newly_germinated_count,
        days_since_sowing: 4,
      })),
      t50_days: null,
    },
  });
  mockApi(
    sowingHandler([sowing()], (path, init) => {
      if (path === `/api/v1/sowings/${sowingId}/germination`)
        return json(germination());
      if (
        path === `/api/v1/sowings/${sowingId}/germination-observations` &&
        init?.method === "POST"
      ) {
        const payload = body(init);
        observations = [
          {
            id: observationId,
            observed_on: String(payload.observed_on),
            newly_germinated_count: Number(payload.newly_germinated_count),
            created_at: "2026-04-14T10:00:00Z",
            updated_at: "2026-04-14T10:00:00Z",
          },
        ];
        return json(germination(), 201);
      }
      if (
        path ===
          `/api/v1/sowings/${sowingId}/germination-observations/${observationId}` &&
        init?.method === "PUT"
      ) {
        observations = [
          {
            ...observations[0],
            newly_germinated_count: Number(body(init).newly_germinated_count),
          },
        ];
        return json(germination());
      }
      if (
        path ===
          `/api/v1/sowings/${sowingId}/germination-observations/${observationId}` &&
        init?.method === "DELETE"
      ) {
        observations = [];
        return json(germination());
      }
      return undefined;
    }),
  );
  const user = await openSowings();
  await user.click(
    await screen.findByRole("button", { name: /Tray A.*Clitoria ternatea/s }),
  );
  await user.click(screen.getByRole("tab", { name: "Germination" }));
  expect(await screen.findByText("No observations yet.")).toBeInTheDocument();
  expect(
    screen.getByText(/add dated observations to see observed germination/i),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Add observation" }));
  await user.type(screen.getByLabelText("Date"), "2026-04-14");
  await user.type(screen.getByLabelText("Newly germinated"), "8");
  await user.click(screen.getByRole("button", { name: "Save observation" }));
  expect(await screen.findByText("40%")).toBeInTheDocument();
  expect(screen.getByText("12")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Edit" }));
  await user.clear(screen.getByLabelText("Newly germinated"));
  await user.type(screen.getByLabelText("Newly germinated"), "0");
  await user.click(screen.getByRole("button", { name: "Save observation" }));
  expect((await screen.findAllByText("0")).length).toBeGreaterThanOrEqual(2);
  await user.click(screen.getByRole("button", { name: "Delete" }));
  expect(
    screen.getByText(/simple germinated total will not change/),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Delete observation" }));
  expect(await screen.findByText("No observations yet.")).toBeInTheDocument();
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
  expect(screen.getByRole("button", { name: "New sowing" })).toBeDisabled();
  expect(screen.getByText(/SeedLot is required/)).toBeInTheDocument();
});

test("Dashboard New sowing route opens the existing form with SeedLot selection", async () => {
  window.history.replaceState(null, "", "#/sowings?action=create");
  mockApi(sowingHandler([]));
  setViewportMatches(true);
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Record Sowing" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "New sowing" }),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("SeedLot")).toBeInTheDocument();
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
    name: /Tray A.*Clitoria ternatea.*12 of 20 germinated/s,
  });
  expect(screen.queryByText("GA3 test")).not.toBeInTheDocument();

  await selectDirectoryFilter(user, "Lifecycle", "completed");
  expect(screen.getByText("GA3 test")).toBeInTheDocument();
  expect(
    screen.getByText(/12 germinated · exact seed count unavailable/),
  ).toBeInTheDocument();
  await selectDirectoryFilter(user, "Lifecycle", "all");

  const search = screen.getByRole("searchbox", { name: "Search Sowings" });
  for (const query of ["Clitoria", "Tray A", "Tray shelf", "Blue packet"]) {
    await user.clear(search);
    await user.type(search, query);
    expect(screen.getByText("Tray A")).toBeInTheDocument();
  }
  await user.clear(search);
  const selectedRow = screen.getByRole("button", {
    name: /Tray A.*Clitoria ternatea.*12 of 20 germinated/s,
  });
  await user.click(selectedRow);
  expect(
    await screen.findByRole("heading", { name: "Source" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Coco coir")).toBeInTheDocument();
  expect(screen.getByText("20.5–28 °C")).toBeInTheDocument();
  expect(screen.getByText("Check daily.")).toBeInTheDocument();
  const back = screen.getByRole("button", { name: "← Back to Sowings" });
  await user.click(back);
  expect(selectedRow).toHaveFocus();
});

test("germination progress uses only an exact positive seed-count denominator", async () => {
  const records = [
    sowing(),
    sowing({
      id: "approx",
      label: "Estimated count",
      quantity: {
        kind: "seed_count",
        value: "20",
        unit: null,
        is_approximate: true,
      },
    }),
    sowing({
      id: "weight",
      label: "Weighed tray",
      quantity: {
        kind: "weight",
        value: "0.5",
        unit: "g",
        is_approximate: false,
      },
    }),
    sowing({ id: "unknown", label: "Unknown tray", quantity: null }),
    sowing({ id: "none", label: "No observations", germinated_count: null }),
    sowing({
      id: "zero",
      label: "Zero exact seeds",
      quantity: {
        kind: "seed_count",
        value: "0",
        unit: null,
        is_approximate: false,
      },
      germinated_count: 0,
    }),
  ];
  mockApi(
    sowingHandler(records, (path) =>
      path === "/api/v1/sowings/zero/germination"
        ? json({
            sowing_id: "zero",
            sowing_date: { precision: "month", year: 2026, month: 8 },
            quantity: {
              kind: "seed_count",
              value: "0",
              unit: null,
              is_approximate: false,
            },
            simple_germinated_count: 0,
            observations: [],
            summary: {
              observed_cumulative_count: 1,
              first_germination_on: "2026-08-15",
              days_to_first_germination: 1,
              last_observation_on: "2026-08-15",
              germination_percentage: "50",
              cumulative_series: [],
              t50_days: 1,
            },
          })
        : undefined,
    ),
  );
  const user = await openSowings();
  await screen.findByRole("list", { name: "Sowing collection" });
  await selectDirectoryFilter(user, "Lifecycle", "all");
  const list = await screen.findByRole("list", { name: "Sowing collection" });
  const row = (label: string) =>
    within(list).getByRole("button", { name: new RegExp(label) });
  expect(row("Tray A")).toHaveTextContent("12 of 20 germinated · 60%");
  expect(within(row("Tray A")).getByRole("progressbar")).toHaveAttribute(
    "value",
    "60",
  );
  for (const label of ["Estimated count", "Weighed tray", "Unknown tray"]) {
    expect(row(label)).toHaveTextContent(
      "12 germinated · exact seed count unavailable",
    );
    expect(
      within(row(label)).queryByRole("progressbar"),
    ).not.toBeInTheDocument();
  }
  expect(row("No observations")).toHaveTextContent("Germination not recorded");
  expect(row("Zero exact seeds")).toHaveTextContent(
    "0 germinated · 0 seeds recorded",
  );
  expect(
    within(row("Zero exact seeds")).queryByRole("progressbar"),
  ).not.toBeInTheDocument();
  await user.click(row("Zero exact seeds"));
  expect(
    await screen.findByRole("heading", { name: "Source" }),
  ).toBeInTheDocument();
  const detail = screen.getByRole("region", {
    name: "Sowing detail and editor",
  });
  expect(
    within(detail).getByText("0 germinated · 0 seeds recorded"),
  ).toBeInTheDocument();
  expect(within(detail).queryByRole("progressbar")).not.toBeInTheDocument();
  await user.click(within(detail).getByRole("tab", { name: "Germination" }));
  expect(
    await within(detail).findByText("Simple germinated total"),
  ).toBeInTheDocument();
  expect(within(detail).queryByText("50%")).not.toBeInTheDocument();
  expect(
    within(detail).queryByText(/Time to 50% \(T50\)/),
  ).not.toBeInTheDocument();
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
  const trigger = await screen.findByRole("button", { name: "New sowing" });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  await user.click(trigger);
  expect(
    screen.queryByRole("button", { name: "New sowing" }),
  ).not.toBeInTheDocument();
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
  await openFormSection(user, "Notes");
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
  await user.click(await screen.findByRole("button", { name: "New sowing" }));
  await openFormSection(user, "Essentials");
  await user.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
  await openFormSection(user, "Essentials");
  await user.type(screen.getByLabelText("Sowing label"), "Heat mat");
  await openFormSection(user, "Essentials");
  await user.selectOptions(
    screen.getByLabelText("Sowing date precision"),
    "year",
  );
  await openFormSection(user, "Essentials");
  await user.clear(screen.getByLabelText("Year"));
  await openFormSection(user, "Essentials");
  await user.type(screen.getByLabelText("Year"), "2024");
  await openFormSection(user, "Material & location");
  await user.selectOptions(
    screen.getByLabelText("Quantity sown kind"),
    "weight",
  );
  await openFormSection(user, "Material & location");
  await user.type(screen.getByLabelText("Amount"), "2.50");
  await openFormSection(user, "Material & location");
  await user.selectOptions(screen.getByLabelText("Unit"), "mg");
  await openFormSection(user, "Material & location");
  await user.click(screen.getByLabelText("Approximate"));
  await openFormSection(user, "Notes");
  await openFormSection(user, "Outcome & status");
  await user.type(screen.getByLabelText("Germinated count"), "12");
  await openFormSection(user, "Material & location");
  await user.selectOptions(
    screen.getByLabelText("Current location"),
    locationId,
  );
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Substrate"), "Sand");
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Method / container"), "Tray");
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Pretreatment"), "Soaked");
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Minimum °C"), "-2.5");
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Maximum °C"), "24");
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Environment / conditions"), "Outside");
  await openFormSection(user, "Outcome & status");
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "completed");
  await openFormSection(user, "Notes");
  await user.type(
    screen.getByLabelText("Notes", { selector: "textarea" }),
    "Historical entry",
  );
  await openFormSection(user, "Notes");
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
    await user.click(await screen.findByRole("button", { name: "New sowing" }));
    await openFormSection(user, "Essentials");
    await user.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
    await openFormSection(user, "Essentials");
    await user.selectOptions(
      screen.getByLabelText("Sowing date precision"),
      precision,
    );
    await openFormSection(user, "Essentials");
    await user.clear(screen.getByLabelText("Year"));
    await openFormSection(user, "Essentials");
    await user.type(screen.getByLabelText("Year"), "2024");
    await openFormSection(user, "Notes");
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
  await user.click(await screen.findByRole("button", { name: "New sowing" }));
  await openFormSection(user, "Essentials");
  await user.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
  await openFormSection(user, "Material & location");
  await user.selectOptions(
    screen.getByLabelText("Quantity sown kind"),
    "seed_count",
  );
  await openFormSection(user, "Material & location");
  await user.type(screen.getByLabelText("Amount"), "10");
  await openFormSection(user, "Notes");
  await openFormSection(user, "Outcome & status");
  await user.type(screen.getByLabelText("Germinated count"), "12");
  await openFormSection(user, "Notes");
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "cannot exceed an exact seed count",
  );
  expect(posts).toBe(0);

  await openFormSection(user, "Material & location");
  await user.click(screen.getByLabelText("Approximate"));
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Minimum °C"), "30");
  await openFormSection(user, "Cultivation");
  await user.type(screen.getByLabelText("Maximum °C"), "20");
  await openFormSection(user, "Notes");
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Minimum temperature cannot be greater",
  );
  expect(posts).toBe(0);
  await openFormSection(user, "Cultivation");
  await user.clear(screen.getByLabelText("Minimum °C"));
  await openFormSection(user, "Notes");
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
    await screen.findByRole("button", { name: "New sowing" }),
  );
  await openFormSection(weightUser, "Essentials");
  await weightUser.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
  await openFormSection(weightUser, "Material & location");
  await weightUser.selectOptions(
    screen.getByLabelText("Quantity sown kind"),
    "weight",
  );
  await openFormSection(weightUser, "Material & location");
  await weightUser.type(screen.getByLabelText("Amount"), "2");
  await openFormSection(weightUser, "Notes");
  await openFormSection(weightUser, "Outcome & status");
  await weightUser.type(screen.getByLabelText("Germinated count"), "12");
  await openFormSection(weightUser, "Notes");
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
  await openFormSection(user, "Essentials");
  await user.clear(screen.getByLabelText("Sowing label"));
  await openFormSection(user, "Essentials");
  await user.type(screen.getByLabelText("Sowing label"), "Unsaved correction");
  await openFormSection(user, "Outcome & status");
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "failed");
  await openFormSection(user, "Notes");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not save or refresh",
  );
  expect(screen.getByLabelText("Sowing label")).toHaveValue(
    "Unsaved correction",
  );
  fail = false;
  await openFormSection(user, "Notes");
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
  await user.click(await screen.findByRole("button", { name: "New sowing" }));
  await openFormSection(user, "Essentials");
  await user.selectOptions(screen.getByLabelText("SeedLot"), seedLotId);
  await openFormSection(user, "Notes");
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Quantity sown must be greater than zero",
  );
  mode = "forbidden";
  await openFormSection(user, "Notes");
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not authorize",
  );
  mode = "session";
  await openFormSection(user, "Notes");
  await user.click(screen.getByRole("button", { name: "Record Sowing" }));
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/session expired/)).toBeInTheDocument();
});

test("desktop Sowing selection stays compact until Open details", async () => {
  mockApi(sowingHandler([sowing()]));
  const user = await openSowings();
  setViewportMatches(false);
  await user.click(
    await screen.findByRole("button", { name: /Tray A.*Clitoria ternatea/ }),
  );
  const preview = await screen.findByRole("complementary", {
    name: "Quick preview",
  });
  expect(
    within(preview).getByRole("heading", { name: "Tray A" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("tab", { name: "Lineage" }),
  ).not.toBeInTheDocument();
  expect(
    within(preview).getByRole("button", { name: "Open details" }),
  ).not.toHaveClass("button--secondary");
  expect(
    within(preview).getByRole("link", { name: "Record germination" }),
  ).toHaveClass("button--secondary");
  expect(
    within(preview).getByRole("link", { name: "Create Plant" }),
  ).toHaveAttribute(
    "href",
    `#/plants?action=from-sowing&sowing=${sowing().id}&kind=plant`,
  );
  await user.click(
    within(preview).getByRole("button", { name: "Open details" }),
  );
  expect(
    screen.getByRole("heading", { name: "Tray A" }).closest("header"),
  ).toHaveTextContent("Clitoria ternatea");
  expect(screen.getByRole("tab", { name: "Lineage" })).toBeInTheDocument();
});

test("reselecting a previewed record after narrowing the viewport opens its detail", async () => {
  mockApi(sowingHandler([sowing()]));
  const user = await openSowings();
  setViewportMatches(false);
  await user.click(
    await screen.findByRole("button", { name: /Tray A.*Clitoria ternatea/ }),
  );
  expect(
    await screen.findByRole("complementary", { name: "Quick preview" }),
  ).toBeInTheDocument();
  setViewportMatches(true);
  await user.click(
    screen.getByRole("button", { name: /Tray A.*Clitoria ternatea/ }),
  );
  expect(
    await screen.findByRole("tab", { name: "Lineage" }),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Loading .* detail/)).not.toBeInTheDocument();
});

test("propagation paths distinguish direct results from retained extracted individuals", async () => {
  const directId = "direct-result";
  const groupId = "source-group";
  const extractedId = "extracted-result";
  mockApi(
    sowingHandler([sowing()], (path) => {
      if (path === `/api/v1/sowings/${sowingId}/propagation-summary`)
        return json({
          sowing_id: sowingId,
          lifecycle: "active",
          germinated_count: 12,
          exact_descendant_count: 1,
          approximate_plant_group_count: 0,
          unknown_plant_group_count: 0,
          plants: [
            {
              id: directId,
              botanical_identity_id: identityId,
              label: "Direct specimen",
              lifecycle: "active",
              originating_plant_group_id: null,
            },
            {
              id: extractedId,
              botanical_identity_id: identityId,
              label: "Historical extraction",
              lifecycle: "reintegrated",
              originating_plant_group_id: groupId,
            },
          ],
          plant_groups: [
            {
              id: groupId,
              botanical_identity_id: identityId,
              label: "Original group",
              lifecycle: "reversed",
              quantity: null,
            },
          ],
        });
      return undefined;
    }),
  );
  const user = await openSowings();
  await user.click(
    await screen.findByRole("button", { name: /Tray A.*Clitoria ternatea/s }),
  );
  expect(
    screen.queryByRole("region", { name: "Propagation path" }),
  ).not.toBeInTheDocument();
  expect(
    await screen.findByRole("region", { name: "Descendants" }),
  ).toHaveTextContent("1 exact individual");
  await user.click(screen.getByRole("link", { name: "View lineage →" }));
  const recorded = screen.getByRole("region", { name: "Recorded lineage" });
  const directLink = within(recorded).getByRole("link", {
    name: /Direct specimen/,
  });
  const extractedLink = within(recorded).getByRole("link", {
    name: /Historical extraction/,
  });
  expect(extractedLink).toHaveTextContent(
    "Plant extracted from Original group",
  );
  expect(extractedLink).toHaveTextContent("reintegrated");
  expect(directLink.closest("li")).not.toBe(extractedLink.closest("li"));
  expect(
    within(recorded).getByRole("link", { name: /Historical extraction/ }),
  ).toHaveTextContent("Plant extracted from Original group");
  expect(
    within(recorded).getByRole("link", {
      name: /Original group.*quantity unknown/s,
    }),
  ).toHaveTextContent("reversed");
});

test("BULK-001 Sowing selection excludes completed records and resets with filters", async () => {
  mockApi(
    sowingHandler([
      sowing(),
      sowing({
        id: "completed",
        label: "Completed tray",
        lifecycle: "completed",
      }),
    ]),
  );
  const user = await openSowings();
  await selectDirectoryFilter(user, "Lifecycle", "all");
  await user.click(screen.getByRole("button", { name: "Select records" }));
  await user.click(screen.getByRole("button", { name: "Select visible" }));
  expect(screen.getByText("1 selected")).toBeVisible();
  expect(
    screen.getByRole("checkbox", { name: /Completed tray/ }),
  ).toBeDisabled();
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "2 records",
  );
  await selectDirectoryFilter(user, "Lifecycle", "active");
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "1 record",
  );
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});

test("contextual Sowing edit preserves directory, guards dismissal, traps focus and returns to its trigger", async () => {
  mockApi(sowingHandler([sowing()]));
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const user = await openSowings();
  setViewportMatches(false);
  const list = screen.getByRole("list", { name: "Sowing collection" });
  await user.click(within(list).getAllByRole("button")[0]);
  const preview = await screen.findByRole("complementary", {
    name: "Quick preview",
  });
  const trigger = within(preview).getByRole("button", {
    name: "Edit",
  });
  const oldHash = window.location.hash;
  await user.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Edit Sowing" });
  expect(document.querySelector(".collection-context-page")).toHaveAttribute(
    "inert",
  );
  const first = within(dialog).getByRole("link", {
    name: "Sowings",
  });
  expect(first).toHaveFocus();
  await user.keyboard("{Shift>}{Tab}{/Shift}");
  expect(
    within(dialog).getByRole("button", { name: "Save changes" }),
  ).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(first).toHaveFocus();
  const label = within(dialog).getByLabelText("Sowing label");
  const before = (label as HTMLInputElement).value;
  await user.type(label, " draft");
  await user.keyboard("{Escape}");
  expect(confirm).toHaveBeenCalledWith("Discard unsaved sowing changes?");
  expect(label).toHaveValue(before + " draft");
  // Backdrop and breadcrumb use the same guard.
  vi.spyOn(dialog, "getBoundingClientRect").mockReturnValue({
    left: 100,
    top: 100,
    right: 1060,
    bottom: 800,
    width: 960,
    height: 700,
    x: 100,
    y: 100,
    toJSON: () => ({}),
  });
  fireEvent.click(dialog, { clientX: 20, clientY: 20 });
  await user.click(first);
  expect(dialog).toBeInTheDocument();
  expect(window.location.hash).toContain("tab=edit");
  confirm.mockClear();
  act(() => {
    window.history.back();
  });
  await waitFor(() => {
    expect(confirm).toHaveBeenCalledWith("Discard unsaved sowing changes?");
  });
  await waitFor(() => {
    expect(window.location.hash).toContain("tab=edit");
  });
  expect(label).toHaveValue(before + " draft");
  confirm.mockReturnValue(true);
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  await waitFor(() => {
    expect(window.location.hash).toBe(oldHash);
  });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(
    screen.getByRole("complementary", { name: "Quick preview" }),
  ).toBeVisible();
  expect(trigger).toHaveFocus();
});

test.each(["tab=edit", "action=edit"])(
  "direct Sowing edit %s retains the full-page fallback and dirty Cancel",
  async (query) => {
    mockApi(sowingHandler([sowing()]));
    window.history.replaceState(null, "", `#/sowings/${sowingId}?${query}`);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<App />);
    const label = await screen.findByLabelText("Sowing label");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      document.querySelector(".edit-workspace-fallback"),
    ).toBeInTheDocument();
    await user.type(label, " draft");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect((label as HTMLInputElement).value).toContain("draft");
    confirm.mockReturnValue(true);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(
      await screen.findByRole("button", { name: "Edit Sowing" }),
    ).toBeVisible();
    expect(window.location.hash).toBe(`#/sowings/${sowingId}`);
  },
);

test.each(["overview", "lineage"])(
  "Back from clean Sowing edit retains the %s detail tab and trigger",
  async (tab) => {
    mockApi(sowingHandler([sowing()]));
    window.history.replaceState(null, "", `#/sowings/${sowingId}?tab=${tab}`);
    const user = userEvent.setup();
    render(<App />);
    const trigger = await screen.findByRole("button", { name: "Edit Sowing" });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "Edit Sowing" })).toBeVisible();
    act(() => {
      window.history.back();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(
      screen.getByRole("tab", {
        name: tab === "overview" ? "Overview" : "Lineage",
      }),
    ).toHaveAttribute("aria-selected", "true");
    expect(trigger).toHaveFocus();
  },
);

test("direct Sowing edit waits for the routed record before loading its draft", async () => {
  const first = sowing({ label: "First record" });
  const second = sowing({ id: "second-record", label: "Second record" });
  mockApi(sowingHandler([first, second]));
  window.history.replaceState(null, "", `#/sowings/${sowingId}?tab=edit`);
  render(<App />);
  expect(await screen.findByLabelText("Sowing label")).toHaveValue(
    "First record",
  );
  act(() => {
    window.location.hash = "/sowings/second-record?tab=edit";
  });
  await waitFor(() => {
    expect(screen.getByLabelText("Sowing label")).toHaveValue("Second record");
  });
});

test("saving Sowing edit retains its detail tab and connected focus trigger across a new revision", async () => {
  let current = sowing();
  const custom: Handler = (path, init) => {
    if (path === `/api/v1/sowings/${sowingId}` && init?.method === "PUT") {
      current = sowing({ ...body(init), updated_at: "2026-10-16T12:30:00Z" });
      return json(current);
    }
    if (path === "/api/v1/sowings" && (!init?.method || init.method === "GET"))
      return json([current]);
    return undefined;
  };
  mockApi(sowingHandler([current], custom));
  window.history.replaceState(null, "", `#/sowings/${sowingId}?tab=lineage`);
  const user = userEvent.setup();
  render(<App />);
  const trigger = await screen.findByRole("button", { name: "Edit Sowing" });
  await user.click(trigger);
  const label = screen.getByLabelText("Sowing label");
  await user.clear(label);
  await user.type(label, "Saved correction");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await screen.findByText("Sowing changes were saved.");
  await waitFor(() => {
    expect(trigger).toHaveFocus();
  });
  expect(trigger.isConnected).toBe(true);
  expect(screen.getByRole("tab", { name: "Lineage" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(
    screen.getByRole("heading", { name: "Saved correction" }),
  ).toBeVisible();
});

test("minimal Sowing row keeps germination while Quick Preview retains source, date, location and paired actions", async () => {
  mockApi(sowingHandler([sowing()]));
  const user = await openSowings();
  setViewportMatches(false);
  const row = await screen.findByRole("button", {
    name: /Tray A.*Clitoria ternatea/s,
  });
  expect(row).not.toHaveTextContent("Blue packet");
  expect(row).not.toHaveTextContent(location.display_path);
  expect(row).not.toHaveTextContent("2026");
  expect(row).toHaveTextContent("germinated");
  await user.click(row);
  const preview = screen.getByRole("complementary", { name: "Quick preview" });
  expect(preview).toHaveTextContent("Blue packet");
  expect(preview).toHaveTextContent(location.display_path);
  expect(within(preview).getByText("Sown")).toBeVisible();
  const actions = within(preview).getByRole("group", {
    name: "Record maintenance",
  });
  expect(within(actions).getByRole("button", { name: "Edit" })).toBeVisible();
  expect(
    within(actions).getByRole("link", { name: "Record germination" }),
  ).toBeVisible();
  expect(
    within(preview).getByRole("link", { name: /^Create Plant$/ }),
  ).toBeVisible();
  expect(
    within(preview).getByRole("link", { name: "Create Plant group" }),
  ).toBeVisible();
  expect(
    within(preview).getByRole("button", { name: "Open details" }),
  ).toBeVisible();
});

test("old Sowing propagation URL opens the canonical Lineage tab and empty summary", async () => {
  mockApi(
    sowingHandler([sowing()], (path) =>
      path.endsWith("/propagation-summary")
        ? json({
            plants: [],
            plant_groups: [],
            exact_descendant_count: 0,
            approximate_plant_group_count: 0,
            unknown_plant_group_count: 0,
          })
        : undefined,
    ),
  );
  window.location.hash = `#/sowings/${sowingId}?tab=propagation`;
  render(<App />);
  expect(await screen.findByRole("tab", { name: "Lineage" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(window.location.hash).toBe(`#/sowings/${sowingId}?tab=lineage`);
  expect(
    await screen.findByText("No additional recorded lineage."),
  ).toBeVisible();
  const path = screen.getByRole("region", { name: "Recorded lineage" });
  expect(
    within(path).getByRole("link", { name: /Blue packet/ }),
  ).toHaveAttribute("href", `#/seeds/${seedLotId}`);
});

test("Sowing Details offers Undo creation in its header without an inline operation panel", async () => {
  mockApi(
    sowingHandler([sowing()], (path) =>
      path.endsWith("/creation-reversal")
        ? json({
            status: "blocked",
            reasons: [
              {
                code: "downstream_lineage",
                message: "A descendant depends on this Sowing.",
                entity_type: "plant",
                entity_id: "child",
              },
            ],
            retained_observation_ids: [],
          })
        : undefined,
    ),
  );
  const user = await openSowings();
  await user.click(
    await screen.findByRole("button", { name: /Tray A.*Clitoria ternatea/s }),
  );
  const more = screen.getByRole("button", { name: "More record actions" });
  expect(more.closest(".detail-header")).toBeInTheDocument();
  expect(screen.queryByText(/Creation operation/)).not.toBeInTheDocument();
  await user.click(more);
  await user.click(screen.getByRole("button", { name: "Undo creation" }));
  const dialog = screen.getByRole("dialog", { name: "Undo sowing creation" });
  expect(
    await within(dialog).findByText("A descendant depends on this Sowing."),
  ).toBeVisible();
  expect(
    within(dialog).getByRole("link", { name: "Open related record" }),
  ).toHaveAttribute("href", "#/plants/child");
});

test.each([false, true])(
  "New Sowing Back uses Sowings as parent (Dashboard entry=%s)",
  async (fromDashboard) => {
    mockApi(sowingHandler([sowing()]));
    const user = fromDashboard ? userEvent.setup() : await openSowings();
    if (fromDashboard) {
      render(<App />);
      await user.click(
        await screen.findByRole("button", { name: "Quick add" }),
      );
      await user.click(screen.getByRole("link", { name: "New sowing" }));
    } else await user.click(screen.getByRole("button", { name: "New sowing" }));
    await screen.findByRole("heading", { name: "Record Sowing" });
    expect(window.location.hash).toBe("#/sowings?action=create");
    await browserBack();
    expect(window.location.hash).toBe("#/sowings");
    expect(
      await screen.findByRole("button", { name: "New sowing" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "Record Sowing" }),
    ).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "New sowing" })).toHaveFocus();
    });
  },
);
