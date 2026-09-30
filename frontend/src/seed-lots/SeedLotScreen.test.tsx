import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "../App";
import type { GeographicPlaceResponse } from "../geographic-places/api";

const identity = {
  id: "01900000-0000-7000-8000-000000000101",
  scientific_name: "Clitoria ternatea",
  cultivar_name: null,
  common_name: "Butterfly pea",
  display_label: "Clitoria ternatea",
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};
const secondIdentity = {
  ...identity,
  id: "01900000-0000-7000-8000-000000000102",
  scientific_name: "Solanum quitoense",
  common_name: "Naranjilla",
  display_label: "Solanum quitoense",
};
const supplier = {
  id: "01900000-0000-7000-8000-000000000201",
  name: "Rare Seed House",
  kind: "seller" as const,
  website: null,
  email: null,
  phone: null,
  notes: null,
  retired_at: null as string | null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};
const location = {
  id: "01900000-0000-7000-8000-000000000301",
  name: "Drawer A",
  parent_id: null as string | null,
  display_path: "Seed cabinet → Drawer A",
  retired_at: null as string | null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};
const place = {
  id: "01900000-0000-7000-8000-000000000401",
  name: "Thailand",
  parent_id: null as string | null,
  display_path: "World → Asia → Southeast Asia → Thailand",
  place_kind: "canonical" as const,
  place_type: null,
  provenance_site_count: 0,
  native_range_count: 0,
  direct_usage_count: 0,
  source_name: "unicode_cldr",
  source_version: "48.2.1",
  source_code_type: "iso_3166_1_alpha_2",
  source_code: "TH",
  retired_at: null as string | null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};

function lot(overrides: Record<string, unknown> = {}) {
  return {
    id: "01900000-0000-7000-8000-000000000501",
    botanical_identity_id: identity.id,
    botanical_identity: {
      id: identity.id,
      display_label: identity.display_label,
    },
    label: "Blue packet",
    source_kind: "purchased",
    source_detail: null,
    supplier_id: supplier.id,
    supplier: { id: supplier.id, name: supplier.name },
    material_provenance_place_id: place.id,
    material_provenance: { id: place.id, display_path: place.display_path },
    acquisition_date: { precision: "year", year: 2024 },
    harvest_date: null,
    quantity: {
      value: "50",
      kind: "seed_count",
      unit: null,
      is_approximate: false,
    },
    expected_viability_until: null,
    location_id: location.id,
    location: { id: location.id, display_path: location.display_path },
    lifecycle: "active",
    notes: "Keep dry.",
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

function requestBody(init?: RequestInit): string {
  if (typeof init?.body !== "string") throw new Error("Expected JSON body");
  return init.body;
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
    if (path === "/api/v1/provenance-sites") return Promise.resolve(json([]));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    const response = handler(path, init);
    if (!response) throw new Error(`Unhandled request: ${path}`);
    return Promise.resolve(response);
  });
}

function directoryHandler(seedLots: unknown[], custom?: Handler): Handler {
  return (path, init) => {
    if (custom) {
      const result = custom(path, init);
      if (result !== undefined) return result;
    }
    if (
      path === "/api/v1/botanical-identities" &&
      (!init?.method || init.method === "GET")
    )
      return json([identity, secondIdentity]);
    if (
      path === "/api/v1/seed-lots" &&
      (!init?.method || init.method === "GET")
    )
      return json(seedLots);
    if (
      path === "/api/v1/suppliers" &&
      (!init?.method || init.method === "GET")
    )
      return json([supplier]);
    if (
      path === "/api/v1/locations" &&
      (!init?.method || init.method === "GET")
    )
      return json([location]);
    if (
      path === "/api/v1/geographic-places" &&
      (!init?.method || init.method === "GET")
    )
      return json([place]);
    throw new Error(`Unexpected request: ${path} ${init?.method ?? "GET"}`);
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

async function openSeeds() {
  // Existing interaction cases exercise the list-to-detail mobile path.
  setViewportMatches(true);
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "Seeds" }));
  await screen.findByRole("heading", { name: "Seeds", level: 2 });
  return user;
}

async function chooseReference(
  user: ReturnType<typeof userEvent.setup>,
  label: string,
  option: string,
) {
  const section = label.includes("Storage")
    ? "Inventory"
    : label.includes("Supplier")
      ? "Acquisition"
      : label.includes("provenance")
        ? "Origin"
        : "Essentials";
  await user.click(screen.getByRole("tab", { name: section }));
  const picker = screen.getByRole("combobox", { name: label });
  await user.click(picker);
  await user.click(await screen.findByRole("button", { name: option }));
}

beforeEach(() => {
  window.history.replaceState(null, "", "#/dashboard");
  localStorage.clear();
  sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  window.history.replaceState(null, "", "#/dashboard");
});

test("Seeds navigation exposes the collection loading and global empty states", async () => {
  mockApi((path, init) => {
    if (
      path === "/api/v1/botanical-identities" &&
      (!init?.method || init.method === "GET")
    )
      return json([]);
    if (path === "/api/v1/seed-lots")
      return new Promise<Response>(() => undefined);
    if (
      path === "/api/v1/suppliers" ||
      path === "/api/v1/locations" ||
      path === "/api/v1/geographic-places"
    )
      return json([]);
    throw new Error(`Unexpected request: ${path}`);
  });
  await openSeeds();
  expect(screen.getByRole("button", { name: "Seeds" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(await screen.findByText("Loading seed inventory…")).toHaveAttribute(
    "role",
    "status",
  );

  cleanup();
  vi.restoreAllMocks();
  mockApi(directoryHandler([]));
  const user = await openSeeds();
  expect(
    await screen.findByRole("heading", { name: "No seeds recorded yet" }),
  ).toBeInTheDocument();
  const newLot = screen.getByRole("button", { name: "+ New seed lot" });
  expect(newLot).toHaveAttribute("aria-expanded", "false");
  expect(
    screen.queryByRole("combobox", { name: "Botanical identity" }),
  ).not.toBeInTheDocument();
  await user.click(newLot);
  expect(
    screen.queryByRole("button", { name: "+ New seed lot" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toHaveFocus();
  const creationPanel = screen.getByRole("region", {
    name: "Seed lot detail and editor",
  });
  expect(creationPanel).toHaveClass("seed-creation-panel");
  expect(creationPanel.parentElement).toHaveClass("seed-master-detail");
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(
    screen.getByRole("button", { name: "+ New seed lot" }),
  ).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByRole("button", { name: "+ New seed lot" })).toHaveFocus();
});

test("inventory preserves API ordering and composes active/history/all with useful text search", async () => {
  const exhausted = lot({
    id: "01900000-0000-7000-8000-000000000502",
    botanical_identity_id: secondIdentity.id,
    botanical_identity: {
      id: secondIdentity.id,
      display_label: secondIdentity.display_label,
    },
    label: "Old harvest",
    lifecycle: "exhausted",
    quantity: { value: "0", kind: "weight", unit: "g", is_approximate: false },
  });
  mockApi(directoryHandler([lot(), exhausted]));
  const user = await openSeeds();
  const list = await screen.findByRole("list", { name: "Seed inventory" });
  expect(within(list).getAllByRole("button")[0]).toHaveTextContent(
    "Clitoria ternatea",
  );
  expect(screen.queryByText("Solanum quitoense")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "History" }));
  expect(screen.getByText("Solanum quitoense")).toBeInTheDocument();
  expect(screen.queryByText("Clitoria ternatea")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "All" }));
  await user.type(
    screen.getByLabelText("Search seed inventory"),
    "Rare Seed House",
  );
  expect(screen.getByText("Clitoria ternatea")).toBeInTheDocument();
  await user.clear(screen.getByLabelText("Search seed inventory"));
  await user.type(
    screen.getByLabelText("Search seed inventory"),
    "does-not-exist",
  );
  expect(
    screen.getByRole("heading", { name: "No matching seed lots" }),
  ).toBeInTheDocument();
});

test("reselecting Seeds clears selection, search and lifecycle filter without reloading", async () => {
  mockApi(directoryHandler([lot()]));
  const user = await openSeeds();
  setViewportMatches(false);
  await user.click(await screen.findByRole("button", { name: /Blue packet/ }));
  expect(
    screen.getByRole("complementary", { name: "Quick preview" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "All" }));
  await user.type(screen.getByLabelText("Search seed inventory"), "Blue");
  await user.click(screen.getByRole("button", { name: "Seeds" }));
  expect(window.location.hash).toBe("#/seeds");
  expect(await screen.findByLabelText("Search seed inventory")).toHaveValue("");
  expect(screen.getByRole("button", { name: "Active" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(
    screen.queryByRole("complementary", { name: "Quick preview" }),
  ).not.toBeInTheDocument();
});

test("reselecting Seeds protects an edited form until changes are discarded", async () => {
  mockApi(directoryHandler([lot()]));
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const user = await openSeeds();
  await user.click(await screen.findByRole("button", { name: /Blue packet/ }));
  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  await user.type(screen.getByLabelText("Lot label (optional)"), " changed");
  await user.click(screen.getByRole("button", { name: "Seeds" }));
  expect(confirm).toHaveBeenCalledOnce();
  expect(screen.getByLabelText("Lot label (optional)")).toHaveValue(
    "Blue packet changed",
  );
  confirm.mockReturnValue(true);
  await user.click(screen.getByRole("button", { name: "Seeds" }));
  expect(window.location.hash).toBe("#/seeds");
  expect(
    screen.queryByRole("button", { name: "Save changes" }),
  ).not.toBeInTheDocument();
});

test("inventory and preview distinguish exact, approximate, unknown and exhausted quantities", async () => {
  const records = [
    lot(),
    lot({
      id: "approx",
      label: "Approximate packet",
      quantity: {
        value: "25",
        kind: "seed_count",
        unit: null,
        is_approximate: true,
      },
    }),
    lot({ id: "unknown", label: "Unknown packet", quantity: null }),
    lot({
      id: "exhausted",
      label: "Exhausted packet",
      lifecycle: "exhausted",
      quantity: {
        value: "0",
        kind: "seed_count",
        unit: null,
        is_approximate: false,
      },
    }),
  ];
  mockApi(directoryHandler(records));
  const user = await openSeeds();
  setViewportMatches(false);
  await user.click(screen.getByRole("button", { name: "All" }));
  const list = await screen.findByRole("list", { name: "Seed inventory" });
  expect(
    within(list).getByRole("button", { name: /Blue packet/ }),
  ).toHaveTextContent("Remaining50 seeds");
  expect(
    within(list).getByRole("button", { name: /Approximate packet/ }),
  ).toHaveTextContent("About 25 seeds");
  expect(
    within(list).getByRole("button", { name: /Unknown packet/ }),
  ).toHaveTextContent("Quantity unknown");
  expect(
    within(list).getByRole("button", { name: /Exhausted packet/ }),
  ).toHaveTextContent("Recorded quantity0 seeds");
  expect(list).not.toHaveTextContent(/% used/);
  await user.click(within(list).getByRole("button", { name: /Blue packet/ }));
  const preview = screen.getByRole("complementary", { name: "Quick preview" });
  expect(within(preview).getByText("50 seeds")).toBeInTheDocument();
  expect(
    within(preview).getByRole("link", { name: "Start sowing" }),
  ).toHaveAttribute("href", `#/sowings?action=start&seedLot=${lot().id}`);
  await user.click(
    within(list).getByRole("button", { name: /Exhausted packet/ }),
  );
  expect(
    within(
      screen.getByRole("complementary", { name: "Quick preview" }),
    ).queryByRole("link", { name: "Start sowing" }),
  ).not.toBeInTheDocument();
});

test("selection shows complete details without internal identifiers and opens coherent editing", async () => {
  mockApi(directoryHandler([lot()]));
  const user = await openSeeds();
  const inventory = await screen.findByRole("region", {
    name: "Seed lot inventory",
  });
  const detailPane = screen.getByRole("region", {
    name: "Seed lot detail and editor",
  });
  expect(inventory).toHaveClass("seed-master");
  expect(detailPane).toHaveClass("seed-detail-pane");
  expect(inventory.parentElement).toHaveClass("seed-master-detail");
  expect(
    screen.getByRole("button", { name: "+ New seed lot" }),
  ).toHaveAttribute("aria-expanded", "false");
  const selectedRow = screen.getByRole("button", {
    name: /Clitoria ternatea/,
  });
  await user.click(selectedRow);
  expect(selectedRow).toHaveAttribute("aria-pressed", "true");
  const detail = screen
    .getByRole("heading", { name: "Blue packet" })
    .closest("section");
  const header = screen
    .getByRole("heading", { name: "Blue packet" })
    .closest("header");
  if (!header) throw new Error("The record heading must belong to its header.");
  expect(
    within(header).getByRole("link", { name: "Clitoria ternatea" }),
  ).toHaveAttribute("href", `#/identities/${lot().botanical_identity.id}`);
  expect(
    screen.getByRole("navigation", { name: "Breadcrumb" }),
  ).not.toHaveTextContent("Clitoria ternatea");
  expect(detail).toHaveTextContent("Purchased");
  expect(detail).toHaveTextContent("Rare Seed House");
  expect(detail).toHaveTextContent("World → Asia");
  expect(detail).toHaveTextContent("2024");
  expect(detail).not.toHaveTextContent("01900000");
  expect(screen.getByRole("link", { name: "Start sowing" })).toHaveAttribute(
    "href",
    `#/sowings?action=start&seedLot=${lot().id}`,
  );
  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  expect(
    screen.queryByRole("button", { name: "Save changes" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Edit Blue packet" }).closest("header"),
  ).toHaveTextContent("Clitoria ternatea");
  expect(screen.getByLabelText("Lifecycle")).toHaveValue("active");
  expect(screen.getByLabelText("Notes (optional)")).not.toBeVisible();
  for (const label of [
    "Essentials",
    "Inventory",
    "Acquisition",
    "Origin",
    "Seed details",
  ])
    expect(screen.getByRole("tab", { name: label })).toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Origin" }));
  expect(screen.getByLabelText("Material provenance (optional)")).toHaveValue(
    place.display_path,
  );
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  expect(screen.getByLabelText("Storage location (optional)")).toHaveValue(
    location.display_path,
  );
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.type(
    screen.getByLabelText("Notes (optional)"),
    "Edit retained note",
  );
  await user.click(screen.getByRole("button", { name: "Back" }));
  await user.click(screen.getByRole("button", { name: "Next" }));
  expect(screen.getByLabelText("Notes (optional)")).toHaveValue(
    "Keep dry.Edit retained note",
  );
});

test("authenticated SeedLot deep link opens existing detail with its label action", async () => {
  const record = lot();
  window.location.hash = `#/seeds/${record.id}`;
  mockApi(directoryHandler([record]));
  render(<App />);
  expect(
    await screen.findByRole("link", { name: "Print label" }),
  ).toHaveAttribute("href", `#/labels?kind=seed-lot&record=${record.id}`);
  expect(screen.getByRole("button", { name: "Edit seed lot" })).toBeVisible();
});

test("guided sowing distinguishes no adjustment, exact partial use and use-all", async () => {
  const record = lot({
    quantity: {
      value: "10",
      kind: "seed_count",
      unit: null,
      is_approximate: false,
    },
  });
  window.location.hash = `#/sowings?action=start&seedLot=${record.id}`;
  mockApi(directoryHandler([record]));
  const user = userEvent.setup();
  render(<App />);
  expect(
    await screen.findByRole(
      "heading",
      { name: "Source seed lot" },
      { timeout: 10_000 },
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("10 seeds")).toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Material & location" }));
  await user.type(screen.getByLabelText("Amount"), "3");
  await user.click(screen.getByRole("tab", { name: /^Notes$/ }));
  await user.click(screen.getByRole("button", { name: "Review seed usage" }));
  expect(
    screen.getByRole("radio", { name: /Keep inventory unchanged/ }),
  ).toBeChecked();
  expect(
    screen.getByText("The source quantity and lifecycle will stay unchanged."),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("radio", { name: /Use part of the lot/ }));
  expect(
    screen.getByText(/7 seeds will remain in the source lot/),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("radio", { name: /Use the whole lot/ }),
  ).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Back to details" }));
  await user.click(screen.getByRole("tab", { name: "Material & location" }));
  await user.clear(screen.getByLabelText("Amount"));
  await user.click(screen.getByRole("tab", { name: "Material & location" }));
  await user.type(screen.getByLabelText("Amount"), "10");
  await user.click(screen.getByRole("tab", { name: /^Notes$/ }));
  await user.click(screen.getByRole("button", { name: "Review seed usage" }));
  await user.click(screen.getByRole("radio", { name: /Use the whole lot/ }));
  expect(screen.getByText(/source will become exhausted/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start sowing" })).toBeEnabled();
});

test("guided sowing asks for a resulting estimate only after approximate partial use", async () => {
  const record = lot({
    quantity: {
      value: "25",
      kind: "seed_count",
      unit: null,
      is_approximate: true,
    },
  });
  window.location.hash = `#/sowings?action=start&seedLot=${record.id}`;
  mockApi(directoryHandler([record]));
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole(
    "heading",
    { name: "Source seed lot" },
    { timeout: 10_000 },
  );
  await user.click(screen.getByRole("tab", { name: "Material & location" }));
  await user.type(screen.getByLabelText("Amount"), "3");
  await user.click(screen.getByRole("tab", { name: /^Notes$/ }));
  await user.click(screen.getByRole("button", { name: "Review seed usage" }));
  expect(screen.queryByLabelText("Resulting estimate")).not.toBeInTheDocument();
  await user.click(screen.getByRole("radio", { name: /Use part of the lot/ }));
  expect(screen.getByLabelText("Resulting estimate")).toHaveValue("25");
  expect(
    screen.getByText(
      /resulting source estimate must be confirmed as about 25 seeds/,
    ),
  ).toBeInTheDocument();
  expect(screen.queryByText(/% used/)).not.toBeInTheDocument();
});

test("guided sowing leaves unknown source quantity unknown", async () => {
  const record = lot({ quantity: null });
  window.location.hash = `#/sowings?action=start&seedLot=${record.id}`;
  mockApi(directoryHandler([record]));
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole(
    "heading",
    { name: "Source seed lot" },
    { timeout: 10_000 },
  );
  await user.click(screen.getByRole("tab", { name: /^Notes$/ }));
  await user.click(screen.getByRole("button", { name: "Review seed usage" }));
  await user.click(
    screen.getByRole("radio", {
      name: /Record partial use; quantity stays unknown/,
    }),
  );
  expect(
    screen.getByText(/source quantity will remain unknown/),
  ).toBeInTheDocument();
  expect(screen.queryByLabelText("Resulting estimate")).not.toBeInTheDocument();
});

test("layered help explains ambiguous SeedLot fields without adding chrome to Notes", async () => {
  mockApi(directoryHandler([]));
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: "+ New seed lot" }),
  );

  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toHaveAccessibleDescription(/does not establish lineage/i);
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  expect(
    screen.getByRole("group", { name: /Quantity/ }),
  ).toHaveAccessibleDescription(
    /leave the quantity empty rather than guessing/i,
  );
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  expect(
    screen.getByRole("combobox", { name: "Supplier (optional)" }),
  ).toHaveAccessibleDescription(/does not establish its biological origin/i);
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  expect(
    screen.getByRole("combobox", { name: "Storage location (optional)" }),
  ).toHaveAccessibleDescription(/currently kept.*not where it originated/i);

  expect(
    screen.getByText(/one seed lot represents one physical packet or bag/i),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("tab", { name: "Origin" }));
  expect(
    screen.getByRole("combobox", { name: "Material provenance (optional)" }),
  ).toHaveAccessibleDescription(
    /not its Supplier or current storage location/i,
  );
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  const acquisitionDate = screen.getByRole("group", {
    name: "Acquisition date",
  });
  expect(
    within(acquisitionDate).getByLabelText("Precision"),
  ).toHaveAccessibleDescription(/do not invent a missing month or day/i);
  expect(screen.getByLabelText("Notes (optional)")).not.toHaveAttribute(
    "aria-describedby",
  );
});

test("minimal fast entry submits only known user information and uses authoritative refresh", async () => {
  let submitted: unknown;
  const created = lot({
    label: null,
    quantity: null,
    source_kind: "unknown",
    supplier_id: null,
    supplier: null,
    material_provenance_place_id: null,
    material_provenance: null,
    acquisition_date: null,
    location_id: null,
    location: null,
    notes: null,
  });
  let lots: unknown[] = [];
  mockApi(
    directoryHandler(lots, (path, init) => {
      if (path === "/api/v1/seed-lots" && init?.method === "POST") {
        submitted = JSON.parse(requestBody(init));
        lots = [created];
        return json(created, 201);
      }
      if (
        path === "/api/v1/seed-lots" &&
        (!init?.method || init.method === "GET")
      )
        return json(lots);
      return undefined;
    }),
  );
  const user = await openSeeds();
  const newLot = await screen.findByRole("button", {
    name: "+ New seed lot",
  });
  await user.click(newLot);
  expect(
    screen.queryByRole("button", { name: "+ New seed lot" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toHaveFocus();
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  await screen.findByText("Seed lot was added to the collection.");
  expect(submitted).toMatchObject({
    botanical_identity_id: identity.id,
    lifecycle: "active",
    source_kind: "unknown",
    quantity: null,
    acquisition_date: null,
  });
  expect(
    screen.getByRole("button", { name: "+ New seed lot" }),
  ).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByRole("button", { name: "+ New seed lot" })).toHaveFocus();
});

test("full entry maps count, approximate g/mg quantity, Other source, references, and every date precision", async () => {
  const payloads: Record<string, unknown>[] = [];
  let lots: unknown[] = [];
  mockApi(
    directoryHandler(lots, (path, init) => {
      if (path === "/api/v1/seed-lots" && init?.method === "POST") {
        const body = JSON.parse(requestBody(init)) as Record<string, unknown>;
        payloads.push(body);
        const created = lot({
          ...body,
          id: `lot-${String(payloads.length)}`,
        });
        lots = [created];
        return json(created, 201);
      }
      if (
        path === "/api/v1/seed-lots" &&
        (!init?.method || init.method === "GET")
      )
        return json(lots);
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: "+ New seed lot" }),
  );
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await user.type(screen.getByLabelText("Lot label (optional)"), "Fresh blue");
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.type(screen.getByLabelText("Quantity value"), "2.5");
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.selectOptions(screen.getByLabelText("Quantity unit"), "g");
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.click(screen.getByLabelText("Approximately"));
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.selectOptions(screen.getByLabelText("Source"), "other");
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.type(
    screen.getByLabelText("Source detail (optional)"),
    "Community swap",
  );
  await chooseReference(user, "Supplier (optional)", "Rare Seed House");
  await chooseReference(
    user,
    "Storage location (optional)",
    "Seed cabinet → Drawer A",
  );
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await chooseReference(
    user,
    "Material provenance (optional)",
    place.display_path,
  );
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.selectOptions(
    screen.getByLabelText("Precision", { selector: "#acquisition-precision" }),
    "year",
  );
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.clear(
    screen.getByLabelText("Year", { selector: "#acquisition-year" }),
  );
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.type(
    screen.getByLabelText("Year", { selector: "#acquisition-year" }),
    "2024",
  );
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.selectOptions(
    screen.getByLabelText("Precision", { selector: "#harvest-precision" }),
    "month",
  );
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.clear(
    screen.getByLabelText("Year", { selector: "#harvest-year" }),
  );
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.type(
    screen.getByLabelText("Year", { selector: "#harvest-year" }),
    "2023",
  );
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.selectOptions(
    screen.getByLabelText("Precision", { selector: "#viability-precision" }),
    "day",
  );
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.type(
    screen.getByLabelText("Notes (optional)"),
    "Cool dry storage",
  );
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  expect(screen.getByLabelText("Notes (optional)")).not.toBeVisible();
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  expect(screen.getByLabelText("Notes (optional)")).toHaveValue(
    "Cool dry storage",
  );
  expect(
    screen.getByLabelText("Precision", { selector: "#acquisition-precision" }),
  ).toHaveValue("year");
  expect(
    screen.getByLabelText("Year", { selector: "#acquisition-year" }),
  ).toHaveValue(2024);
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  await screen.findByText("Seed lot was added to the collection.");
  expect(screen.getByRole("link", { name: "Rare Seed House" })).toHaveAttribute(
    "href",
    `#/suppliers/${supplier.id}`,
  );
  expect(payloads[0]).toMatchObject({
    quantity: { value: "2.5", kind: "weight", unit: "g", is_approximate: true },
    source_kind: "other",
    source_detail: "Community swap",
    supplier_id: supplier.id,
    location_id: location.id,
    material_provenance_place_id: place.id,
    acquisition_date: { precision: "year", year: 2024 },
    harvest_date: { precision: "month", year: 2023, month: 1 },
  });
});

test("milligram weight maps cleanly and leaving Other clears its detail", async () => {
  let submitted: Record<string, unknown> | null = null;
  let lots: unknown[] = [];
  mockApi(
    directoryHandler(lots, (path, init) => {
      if (path === "/api/v1/seed-lots" && init?.method === "POST") {
        submitted = JSON.parse(requestBody(init)) as Record<string, unknown>;
        const created = lot({ ...submitted, id: "mg-lot" });
        lots = [created];
        return json(created, 201);
      }
      if (
        path === "/api/v1/seed-lots" &&
        (!init?.method || init.method === "GET")
      )
        return json(lots);
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: "+ New seed lot" }),
  );
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.type(screen.getByLabelText("Quantity value"), "125");
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.selectOptions(screen.getByLabelText("Quantity unit"), "mg");
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.selectOptions(screen.getByLabelText("Source"), "other");
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.type(
    screen.getByLabelText("Source detail (optional)"),
    "Old note",
  );
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.selectOptions(screen.getByLabelText("Source"), "purchased");
  expect(
    screen.queryByLabelText("Source detail (optional)"),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  await screen.findByText("Seed lot was added to the collection.");
  expect(submitted).toMatchObject({
    quantity: {
      value: "125",
      kind: "weight",
      unit: "mg",
      is_approximate: false,
    },
    source_kind: "purchased",
    source_detail: null,
  });
});

test("historical exhausted zero is valid while active zero is explained before submission", async () => {
  let postCalls = 0;
  let lots: unknown[] = [];
  const exhausted = lot({
    lifecycle: "exhausted",
    quantity: {
      value: "0",
      kind: "seed_count",
      unit: null,
      is_approximate: false,
    },
  });
  mockApi(
    directoryHandler(lots, (path, init) => {
      if (path === "/api/v1/seed-lots" && init?.method === "POST") {
        postCalls += 1;
        lots = [exhausted];
        return json(exhausted, 201);
      }
      if (
        path === "/api/v1/seed-lots" &&
        (!init?.method || init.method === "GET")
      )
        return json(lots);
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: "+ New seed lot" }),
  );
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.type(screen.getByLabelText("Quantity value"), "0");
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "only valid for an exhausted lot",
  );
  expect(
    screen.queryByRole("button", { name: "+ New seed lot" }),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("Quantity value")).toHaveValue("0");
  expect(postCalls).toBe(0);
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "exhausted");
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  await screen.findByText("Seed lot was added to the collection.");
  expect(postCalls).toBe(1);
});

test("one PUT supports lost to active and exhausted zero to active positive corrections", async () => {
  const updates: Record<string, unknown>[] = [];
  let current = lot({ lifecycle: "lost", quantity: null });
  mockApi(
    directoryHandler([current], (path, init) => {
      if (path.includes("/api/v1/seed-lots/") && init?.method === "PUT") {
        const body = JSON.parse(requestBody(init)) as Record<string, unknown>;
        updates.push(body);
        current = lot({ ...body });
        return json(current);
      }
      if (
        path === "/api/v1/seed-lots" &&
        (!init?.method || init.method === "GET")
      )
        return json([current]);
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.click(await screen.findByRole("button", { name: "History" }));
  await user.click(
    await screen.findByRole("button", { name: /Clitoria ternatea/ }),
  );
  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "active");
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await screen.findByText("Seed lot changes were saved.");
  expect(updates[0]).toMatchObject({ lifecycle: "active", quantity: null });

  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "exhausted");
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.clear(screen.getByLabelText("Quantity value"));
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.type(screen.getByLabelText("Quantity value"), "0");
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "active");
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.clear(screen.getByLabelText("Quantity value"));
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  await user.type(screen.getByLabelText("Quantity value"), "15");
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(updates[1]).toMatchObject({
    lifecycle: "active",
    quantity: { value: "15", kind: "seed_count" },
  });
});

test("contextual creators auto-select references, preserve unsaved lot data, and return focus on Escape", async () => {
  let identities = [identity, secondIdentity];
  let suppliers = [supplier];
  let locations = [location];
  let places: GeographicPlaceResponse[] = [place];
  mockApi((path, init) => {
    if (path === "/api/v1/botanical-identities" && init?.method === "POST") {
      const created = {
        ...identity,
        id: "new-identity",
        display_label: "Passiflora edulis",
        scientific_name: "Passiflora edulis",
      };
      identities = [...identities, created];
      return json(created, 201);
    }
    if (path === "/api/v1/suppliers" && init?.method === "POST") {
      const created = { ...supplier, id: "new-supplier", name: "Local swap" };
      suppliers = [...suppliers, created];
      return json(created, 201);
    }
    if (path === "/api/v1/locations" && init?.method === "POST") {
      const created = {
        ...location,
        id: "new-location",
        name: "Drawer B",
        display_path: "Seed cabinet → Drawer B",
      };
      locations = [...locations, created];
      return json(created, 201);
    }
    if (path === "/api/v1/geographic-places" && init?.method === "POST") {
      const created = {
        ...place,
        id: "new-place",
        name: "Chiang Mai",
        display_path: `${place.display_path} → Chiang Mai`,
        place_kind: "custom" as const,
      };
      places = [...places, created];
      return json(created, 201);
    }
    if (path === "/api/v1/botanical-identities") return json(identities);
    if (path === "/api/v1/seed-lots") return json([]);
    if (path === "/api/v1/suppliers") return json(suppliers);
    if (path === "/api/v1/locations") return json(locations);
    if (path === "/api/v1/geographic-places") return json(places);
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: "+ New seed lot" }),
  );
  await user.type(
    screen.getByLabelText("Lot label (optional)"),
    "Unsaved packet",
  );

  const identityPicker = screen.getByRole("combobox", {
    name: "Botanical identity",
  });
  await user.type(identityPicker, "Passiflora edulis");
  await user.click(
    screen.getByRole("button", { name: /Create identity “Passiflora edulis”/ }),
  );
  expect(screen.getByLabelText("Scientific name")).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "Create and select" }));
  await waitFor(() => {
    expect(identityPicker).toHaveValue("Passiflora edulis");
  });
  expect(screen.getByLabelText("Lot label (optional)")).toHaveValue(
    "Unsaved packet",
  );

  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  const supplierPicker = screen.getByRole("combobox", {
    name: "Supplier (optional)",
  });
  await user.type(supplierPicker, "Local swap");
  await user.click(
    screen.getByRole("button", { name: /Create supplier “Local swap”/ }),
  );
  await user.click(screen.getByRole("button", { name: "Create and select" }));
  await waitFor(() => {
    expect(supplierPicker).toHaveValue("Local swap");
  });

  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  const locationPicker = screen.getByRole("combobox", {
    name: "Storage location (optional)",
  });
  await user.type(locationPicker, "Drawer B");
  await user.click(
    screen.getByRole("button", { name: /Create location “Drawer B”/ }),
  );
  await user.click(screen.getByRole("button", { name: "Create and select" }));
  await waitFor(() => {
    expect(locationPicker).toHaveValue("Seed cabinet → Drawer B");
  });

  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("tab", { name: "Origin" }));
  const provenancePicker = screen.getByRole("combobox", {
    name: "Material provenance (optional)",
  });
  await user.type(provenancePicker, "Chiang Mai");
  await user.click(
    screen.getByRole("button", { name: /Create local place “Chiang Mai”/ }),
  );
  await chooseReference(user, "Parent", place.display_path);
  await user.click(screen.getByRole("button", { name: "Create and select" }));
  await waitFor(() => {
    expect(provenancePicker).toHaveValue(`${place.display_path} → Chiang Mai`);
  });

  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.click(supplierPicker);
  await user.click(screen.getByRole("button", { name: /Create supplier/ }));
  const dialogInput = screen.getByRole("dialog").querySelector("input");
  expect(dialogInput).toHaveFocus();
  await user.keyboard("{Shift>}{Tab}{/Shift}");
  expect(
    within(screen.getByRole("dialog")).getByRole("button", { name: "Cancel" }),
  ).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(dialogInput).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(supplierPicker).toHaveFocus();
}, 30_000);

test("duplicate and failed contextual creation keep the seed form intact", async () => {
  mockApi(
    directoryHandler([], (path, init) => {
      if (path === "/api/v1/botanical-identities" && init?.method === "POST")
        return json({ detail: { existing_id: identity.id } }, 409);
      if (path === `/api/v1/botanical-identities/${identity.id}`)
        return json(identity);
      if (path === "/api/v1/suppliers" && init?.method === "POST")
        throw new TypeError("network down");
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: "+ New seed lot" }),
  );
  await user.type(screen.getByLabelText("Lot label (optional)"), "Still here");
  await user.type(
    screen.getByRole("combobox", { name: "Botanical identity" }),
    "Clitoria ternatea",
  );
  await user.click(screen.getByRole("button", { name: /Create identity/ }));
  const identityDialog = await screen.findByRole("dialog", {
    name: "Create botanical identity",
  });
  await user.click(
    within(identityDialog).getByRole("button", { name: "Create and select" }),
  );
  await waitFor(() => {
    expect(
      screen.getByRole("combobox", { name: "Botanical identity" }),
    ).toHaveValue("Clitoria ternatea");
  });
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  await user.type(
    screen.getByRole("combobox", { name: "Supplier (optional)" }),
    "Broken supplier",
  );
  await user.click(screen.getByRole("button", { name: /Create supplier/ }));
  const supplierDialog = await screen.findByRole("dialog", {
    name: "Create supplier",
  });
  await user.click(
    within(supplierDialog).getByRole("button", { name: "Create and select" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "seed lot details are still here",
  );
  expect(screen.getByLabelText("Lot label (optional)")).toHaveValue(
    "Still here",
  );
});

test("retired current references remain visible in edit while ordinary retired choices are omitted", async () => {
  const retiredSupplier = { ...supplier, retired_at: "2026-08-30T00:00:00Z" };
  const retiredLocation = { ...location, retired_at: "2026-08-30T00:00:00Z" };
  const historical = lot({ lifecycle: "discarded" });
  mockApi((path, init) => {
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === "/api/v1/seed-lots") return json([historical]);
    if (path === "/api/v1/suppliers") return json([retiredSupplier]);
    if (path === "/api/v1/locations") return json([retiredLocation]);
    if (path === "/api/v1/geographic-places") return json([place]);
    throw new Error(`Unexpected request: ${path} ${init?.method ?? "GET"}`);
  });
  const user = await openSeeds();
  await user.click(await screen.findByRole("button", { name: "History" }));
  await user.click(
    await screen.findByRole("button", { name: /Clitoria ternatea/ }),
  );
  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  await user.click(screen.getByRole("tab", { name: "Acquisition" }));
  expect(
    screen.getByRole("combobox", { name: "Supplier (optional)" }),
  ).toHaveValue(supplier.name);
  expect(
    screen.getByLabelText("Supplier (optional)"),
  ).toHaveAccessibleDescription(/retired/i);
  await user.click(screen.getByRole("tab", { name: "Inventory" }));
  expect(
    screen.getByLabelText("Storage location (optional)"),
  ).toHaveAccessibleDescription(/retired/i);
});

test("load, validation, forbidden, update, network, and session-expiry failures are explicit", async () => {
  mockApi((path) => {
    if (path === "/api/v1/botanical-identities") return json([]);
    if (path === "/api/v1/seed-lots") return json({ detail: "failed" }, 500);
    if (
      path === "/api/v1/suppliers" ||
      path === "/api/v1/locations" ||
      path === "/api/v1/geographic-places"
    )
      return json([]);
    throw new Error(`Unexpected request: ${path}`);
  });
  await openSeeds();
  expect(await screen.findByRole("alert")).toHaveTextContent("could not load");

  cleanup();
  vi.restoreAllMocks();
  let mode: "validation" | "forbidden" | "network" | "session" = "validation";
  mockApi(
    directoryHandler([], (path, init) => {
      if (path === "/api/v1/seed-lots" && init?.method === "POST") {
        if (mode === "validation")
          return json(
            {
              detail: [
                {
                  loc: ["body", "quantity"],
                  msg: "zero invalid",
                  type: "value_error",
                },
              ],
            },
            422,
          );
        if (mode === "forbidden") return json({ detail: "forbidden" }, 403);
        if (mode === "session") return json({ detail: "expired" }, 401);
        throw new TypeError("network unavailable");
      }
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: "+ New seed lot" }),
  );
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("zero quantity");
  await waitFor(() => {
    expect(screen.getByRole("tab", { name: "Inventory" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
  mode = "forbidden";
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not authorize",
  );
  mode = "network";
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Check the connection",
  );
  mode = "session";
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  expect(
    await screen.findByRole("button", { name: "Sign in" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Your session expired. Sign in again to continue."),
  ).toBeInTheDocument();
});

test("update and stale-reference failures retain the editable lot", async () => {
  let responseKind: "stale" | "server" = "stale";
  mockApi(
    directoryHandler([lot()], (path, init) => {
      if (path.includes("/api/v1/seed-lots/") && init?.method === "PUT") {
        if (responseKind === "stale")
          return json(
            {
              detail: [
                {
                  loc: ["body", "location_id"],
                  msg: "reference not found",
                  type: "value_error",
                },
              ],
            },
            422,
          );
        return json({ detail: "server failure" }, 500);
      }
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: /Clitoria ternatea/ }),
  );
  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  await user.clear(screen.getByLabelText("Lot label (optional)"));
  await user.type(
    screen.getByLabelText("Lot label (optional)"),
    "Unsaved correction",
  );
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Storage location no longer exists",
  );
  expect(screen.getByLabelText("Lot label (optional)")).toHaveValue(
    "Unsaved correction",
  );
  responseKind = "server";
  await user.click(screen.getByRole("tab", { name: "Seed details" }));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not save or refresh",
  );
});

test("reference combobox supports keyboard selection with accessible names", async () => {
  mockApi(directoryHandler([]));
  const user = await openSeeds();
  await user.click(
    await screen.findByRole("button", { name: "+ New seed lot" }),
  );
  const picker = screen.getByRole("combobox", { name: "Botanical identity" });
  expect(picker).toHaveAttribute("aria-controls");
  await user.type(picker, "Clit");
  await user.keyboard("{ArrowDown}{Enter}");
  expect(picker).toHaveValue("Clitoria ternatea");
});

test("desktop selection offers a compact preview before opening SeedLot detail", async () => {
  mockApi(directoryHandler([lot()]));
  const user = await openSeeds();
  setViewportMatches(false);
  await user.click(await screen.findByRole("button", { name: /Blue packet/ }));
  const preview = screen.getByRole("complementary", { name: "Quick preview" });
  expect(
    within(preview).getByRole("heading", { name: "Blue packet" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Inventory" }),
  ).not.toBeInTheDocument();
  await user.click(
    within(preview).getByRole("button", { name: "Open details" }),
  );
  expect(
    screen.getByRole("heading", { name: "Inventory" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "← Back to seed lots" }),
  ).toBeInTheDocument();
});
