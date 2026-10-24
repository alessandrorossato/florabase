import { browserBack } from "../test/history";
import { openFormSection } from "../test/formSections";
import { selectDirectoryFilter } from "../test/directoryFilters";
import {
  act,
  fireEvent,
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
// These cases exercise SeedLot interactions; App.lazy.test.tsx owns chunk loading.
import "./SeedLotScreen";

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
    if (path.startsWith("/api/v1/orders?"))
      return json({ items: [], total: 0, offset: 0, limit: 50 });
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
  await user.click(
    within(
      await screen.findByRole("navigation", { name: "Primary navigation" }),
    ).getByRole("link", { name: "Seeds" }),
  );
  await screen.findByRole("heading", { name: "Seeds", level: 2 });
  return user;
}

async function openSection(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
) {
  const tab = screen.queryByRole("tab", { name });
  if (tab) await user.click(tab);
  else
    expect(screen.getByRole("button", { name: "Add seed lot" })).toBeVisible();
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
  await openSection(user, section);
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
  expect(
    within(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).getByRole("link", { name: "Seeds" }),
  ).toHaveAttribute("aria-current", "page");
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
  const newLot = screen.getByRole("button", { name: "New seed lot" });
  expect(newLot).toHaveAttribute("aria-expanded", "false");
  expect(
    screen.queryByRole("combobox", { name: "Botanical identity" }),
  ).not.toBeInTheDocument();
  await user.click(newLot);
  expect(
    screen.queryByRole("button", { name: "New seed lot" }),
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
  expect(screen.getByRole("button", { name: "New seed lot" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  expect(screen.getByRole("button", { name: "New seed lot" })).toHaveFocus();
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

  await selectDirectoryFilter(user, "Lifecycle", "history");
  expect(screen.getByText("Solanum quitoense")).toBeInTheDocument();
  expect(screen.queryByText("Clitoria ternatea")).not.toBeInTheDocument();
  await selectDirectoryFilter(user, "Lifecycle", "all");
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
  await selectDirectoryFilter(user, "Lifecycle", "all");
  await user.type(screen.getByLabelText("Search seed inventory"), "Blue");
  await user.click(
    within(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).getByRole("link", { name: "Seeds" }),
  );
  expect(window.location.hash).toBe("#/seeds");
  expect(await screen.findByLabelText("Search seed inventory")).toHaveValue("");
  expect(
    screen.getByRole("button", { name: "Remove lifecycle filter" }),
  ).toHaveTextContent("Active");
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
  await user.type(screen.getByLabelText("Lot label"), " changed");
  await user.click(
    within(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).getByRole("link", { name: "Seeds" }),
  );
  expect(confirm).toHaveBeenCalledOnce();
  expect(screen.getByLabelText("Lot label")).toHaveValue("Blue packet changed");
  confirm.mockReturnValue(true);
  await user.click(
    within(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).getByRole("link", { name: "Seeds" }),
  );
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
  await selectDirectoryFilter(user, "Lifecycle", "all");
  const list = await screen.findByRole("list", { name: "Seed inventory" });
  expect(
    within(list).getByRole("button", { name: /Blue packet/ }),
  ).toHaveTextContent("50 seeds remaining");
  expect(
    within(list).getByRole("button", { name: /Approximate packet/ }),
  ).toHaveTextContent("About 25 seeds");
  expect(
    within(list).getByRole("button", { name: /Unknown packet/ }),
  ).toHaveTextContent("Quantity unknown");
  expect(
    within(list).getByRole("button", { name: /Exhausted packet/ }),
  ).toHaveTextContent("0 seedsRecorded quantity");
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
  expect(screen.getByRole("button", { name: "New seed lot" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
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
  expect(screen.queryByRole("button", { name: "Save changes" })).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Next" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Edit Blue packet" }).closest("header"),
  ).toHaveTextContent("Clitoria ternatea");
  expect(screen.getByLabelText("Lifecycle")).toHaveValue("active");
  expect(
    screen.getByRole("textbox", { name: "Notes", hidden: true }),
  ).not.toBeVisible();
  for (const label of [
    "Essentials",
    "Inventory",
    "Acquisition",
    "Origin",
    "Seed details",
  ]) {
    await user.click(screen.getByRole("tab", { name: label }));
    expect(screen.getByRole("button", { name: "Save changes" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeVisible();
  }
  await openSection(user, "Origin");
  expect(screen.getByLabelText("Material provenance")).toHaveValue(
    place.display_path,
  );
  await openSection(user, "Inventory");
  expect(screen.getByLabelText("Storage location")).toHaveValue(
    location.display_path,
  );
  await openSection(user, "Seed details");
  await user.type(
    screen.getByLabelText("Notes", { selector: "textarea" }),
    "Edit retained note",
  );
  await openSection(user, "Origin");
  await openSection(user, "Seed details");
  expect(screen.getByLabelText("Notes", { selector: "textarea" })).toHaveValue(
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
  await openFormSection(user, "Material & location");
  await user.type(screen.getByLabelText("Amount"), "3");
  await openFormSection(user, "Notes");
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
  await openFormSection(user, "Material & location");
  await user.clear(screen.getByLabelText("Amount"));
  await openFormSection(user, "Material & location");
  await user.type(screen.getByLabelText("Amount"), "10");
  await openFormSection(user, "Notes");
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
  await openFormSection(user, "Material & location");
  await user.type(screen.getByLabelText("Amount"), "3");
  await openFormSection(user, "Notes");
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
  await openFormSection(user, "Notes");
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
  await user.click(await screen.findByRole("button", { name: "New seed lot" }));

  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toHaveAccessibleDescription(/does not establish lineage/i);
  await openSection(user, "Inventory");
  expect(
    screen.getByRole("group", { name: /Quantity/ }),
  ).toHaveAccessibleDescription(
    /leave the quantity empty rather than guessing/i,
  );
  await openSection(user, "Acquisition");
  expect(
    screen.getByRole("combobox", { name: "Supplier" }),
  ).toHaveAccessibleDescription(/does not establish its biological origin/i);
  await openSection(user, "Inventory");
  expect(
    screen.getByRole("combobox", { name: "Storage location" }),
  ).toHaveAccessibleDescription(/currently kept.*not where it originated/i);

  expect(
    screen.getByText(/one seed lot represents one physical packet or bag/i),
  ).toBeInTheDocument();

  await openSection(user, "Seed details");
  await openSection(user, "Origin");
  expect(
    screen.getByRole("combobox", { name: "Material provenance" }),
  ).toHaveAccessibleDescription(
    /not its Supplier or current storage location/i,
  );
  await openSection(user, "Acquisition");
  const acquisitionDate = screen.getByRole("group", {
    name: "Acquisition date",
  });
  expect(
    within(acquisitionDate).getByLabelText("Precision"),
  ).toHaveAccessibleDescription(/do not invent a missing month or day/i);
  expect(
    screen.getByLabelText("Notes", { selector: "textarea" }),
  ).not.toHaveAttribute("aria-describedby");
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
    name: "New seed lot",
  });
  await user.click(newLot);
  expect(
    screen.queryByRole("button", { name: "New seed lot" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toHaveFocus();
  expect(
    screen.queryByRole("tablist", { name: "Form sections" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Next" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Back" }),
  ).not.toBeInTheDocument();
  for (const name of [
    "Identity",
    "Inventory",
    "Acquisition",
    "Origin",
    "Seed details",
  ])
    expect(screen.getByRole("heading", { name })).toBeVisible();
  expect(screen.getByLabelText("Lot label")).toBeVisible();
  expect(
    screen.getByLabelText("Notes", { selector: "textarea" }),
  ).toBeVisible();
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
  await screen.findByText("Seed lot was added to the collection.");
  expect(submitted).toMatchObject({
    botanical_identity_id: identity.id,
    lifecycle: "active",
    source_kind: "unknown",
    quantity: null,
    acquisition_date: null,
  });
  expect(
    screen.queryByRole("button", { name: "New seed lot" }),
  ).not.toBeInTheDocument();
  await waitFor(() => {
    expect(
      screen.getByRole("heading", { name: "Butterfly pea" }),
    ).toHaveFocus();
  });
  expect(
    within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole(
      "link",
      { name: "Seeds" },
    ),
  ).toHaveAttribute("href", "#/seeds");
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
  await user.click(await screen.findByRole("button", { name: "New seed lot" }));
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await user.type(screen.getByLabelText("Lot label"), "Fresh blue");
  await openSection(user, "Inventory");
  await user.type(screen.getByLabelText("Quantity value"), "2.5");
  await openSection(user, "Inventory");
  await user.selectOptions(screen.getByLabelText("Quantity unit"), "g");
  await openSection(user, "Inventory");
  await user.click(screen.getByLabelText("Approximately"));
  await openSection(user, "Seed details");
  await user.selectOptions(screen.getByLabelText("Source"), "other");
  await openSection(user, "Acquisition");
  await user.type(screen.getByLabelText("Source detail"), "Community swap");
  await chooseReference(user, "Supplier", "Rare Seed House");
  await chooseReference(user, "Storage location", "Seed cabinet → Drawer A");
  await openSection(user, "Seed details");
  await chooseReference(user, "Material provenance", place.display_path);
  await openSection(user, "Acquisition");
  await user.selectOptions(
    screen.getByLabelText("Precision", { selector: "#acquisition-precision" }),
    "year",
  );
  await openSection(user, "Acquisition");
  await user.clear(
    screen.getByLabelText("Year", { selector: "#acquisition-year" }),
  );
  await openSection(user, "Acquisition");
  await user.type(
    screen.getByLabelText("Year", { selector: "#acquisition-year" }),
    "2024",
  );
  await openSection(user, "Acquisition");
  await user.selectOptions(
    screen.getByLabelText("Precision", { selector: "#harvest-precision" }),
    "month",
  );
  await openSection(user, "Seed details");
  await user.clear(
    screen.getByLabelText("Year", { selector: "#harvest-year" }),
  );
  await openSection(user, "Seed details");
  await user.type(
    screen.getByLabelText("Year", { selector: "#harvest-year" }),
    "2023",
  );
  await openSection(user, "Seed details");
  await user.selectOptions(
    screen.getByLabelText("Precision", { selector: "#viability-precision" }),
    "day",
  );
  await openSection(user, "Seed details");
  await user.type(
    screen.getByLabelText("Notes", { selector: "textarea" }),
    "Cool dry storage",
  );
  await openSection(user, "Essentials");
  expect(
    screen.getByLabelText("Notes", { selector: "textarea" }),
  ).toBeVisible();
  await openSection(user, "Seed details");
  expect(screen.getByLabelText("Notes", { selector: "textarea" })).toHaveValue(
    "Cool dry storage",
  );
  expect(
    screen.getByLabelText("Precision", { selector: "#acquisition-precision" }),
  ).toHaveValue("year");
  expect(
    screen.getByLabelText("Year", { selector: "#acquisition-year" }),
  ).toHaveValue(2024);
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
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
  await user.click(await screen.findByRole("button", { name: "New seed lot" }));
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await openSection(user, "Inventory");
  await user.type(screen.getByLabelText("Quantity value"), "125");
  await openSection(user, "Inventory");
  await user.selectOptions(screen.getByLabelText("Quantity unit"), "mg");
  await openSection(user, "Acquisition");
  await user.selectOptions(screen.getByLabelText("Source"), "other");
  await openSection(user, "Acquisition");
  await user.type(screen.getByLabelText("Source detail"), "Old note");
  await openSection(user, "Acquisition");
  await user.selectOptions(screen.getByLabelText("Source"), "purchased");
  expect(screen.queryByLabelText("Source detail")).not.toBeInTheDocument();
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
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
  await user.click(await screen.findByRole("button", { name: "New seed lot" }));
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await openSection(user, "Inventory");
  await user.type(screen.getByLabelText("Quantity value"), "0");
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "only valid for an exhausted lot",
  );
  expect(
    screen.queryByRole("button", { name: "New seed lot" }),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("Quantity value")).toHaveValue("0");
  expect(postCalls).toBe(0);
  await openSection(user, "Seed details");
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "exhausted");
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
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
  await selectDirectoryFilter(user, "Lifecycle", "history");
  await user.click(
    await screen.findByRole("button", { name: /Clitoria ternatea/ }),
  );
  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "active");
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await screen.findByText("Seed lot changes were saved.");
  expect(updates[0]).toMatchObject({ lifecycle: "active", quantity: null });

  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "exhausted");
  await openSection(user, "Inventory");
  await user.clear(screen.getByLabelText("Quantity value"));
  await openSection(user, "Inventory");
  await user.type(screen.getByLabelText("Quantity value"), "0");
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "active");
  await openSection(user, "Inventory");
  await user.clear(screen.getByLabelText("Quantity value"));
  await openSection(user, "Inventory");
  await user.type(screen.getByLabelText("Quantity value"), "15");
  await openSection(user, "Seed details");
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
  await user.click(await screen.findByRole("button", { name: "New seed lot" }));
  await user.type(screen.getByLabelText("Lot label"), "Unsaved packet");

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
  expect(screen.getByLabelText("Lot label")).toHaveValue("Unsaved packet");

  await openSection(user, "Acquisition");
  const supplierPicker = screen.getByRole("combobox", {
    name: "Supplier",
  });
  await user.type(supplierPicker, "Local swap");
  await user.click(
    screen.getByRole("button", { name: /Create supplier “Local swap”/ }),
  );
  await user.click(screen.getByRole("button", { name: "Create and select" }));
  await waitFor(() => {
    expect(supplierPicker).toHaveValue("Local swap");
  });

  await openSection(user, "Inventory");
  const locationPicker = screen.getByRole("combobox", {
    name: "Storage location",
  });
  await user.type(locationPicker, "Drawer B");
  await user.click(
    screen.getByRole("button", { name: /Create location “Drawer B”/ }),
  );
  await user.click(screen.getByRole("button", { name: "Create and select" }));
  await waitFor(() => {
    expect(locationPicker).toHaveValue("Seed cabinet → Drawer B");
  });

  await openSection(user, "Seed details");
  await openSection(user, "Origin");
  const provenancePicker = screen.getByRole("combobox", {
    name: "Material provenance",
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

  await openSection(user, "Acquisition");
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
  await user.click(await screen.findByRole("button", { name: "New seed lot" }));
  await user.type(screen.getByLabelText("Lot label"), "Still here");
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
  await openSection(user, "Acquisition");
  await user.type(
    screen.getByRole("combobox", { name: "Supplier" }),
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
  expect(screen.getByLabelText("Lot label")).toHaveValue("Still here");
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
  await selectDirectoryFilter(user, "Lifecycle", "history");
  await user.click(
    await screen.findByRole("button", { name: /Clitoria ternatea/ }),
  );
  await user.click(screen.getByRole("button", { name: "Edit seed lot" }));
  await openSection(user, "Acquisition");
  expect(screen.getByRole("combobox", { name: "Supplier" })).toHaveValue(
    supplier.name,
  );
  expect(screen.getByLabelText("Supplier")).toHaveAccessibleDescription(
    /retired/i,
  );
  await openSection(user, "Inventory");
  expect(screen.getByLabelText("Storage location")).toHaveAccessibleDescription(
    /retired/i,
  );
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
  await user.click(await screen.findByRole("button", { name: "New seed lot" }));
  await chooseReference(user, "Botanical identity", "Clitoria ternatea");
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("zero quantity");
  await waitFor(() => {
    expect(screen.getByLabelText("Quantity value")).toHaveFocus();
  });
  mode = "forbidden";
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not authorize",
  );
  mode = "network";
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Check the connection",
  );
  mode = "session";
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Add seed lot" }));
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
  await user.clear(screen.getByLabelText("Lot label"));
  await user.type(screen.getByLabelText("Lot label"), "Unsaved correction");
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Storage location no longer exists",
  );
  expect(screen.getByLabelText("Lot label")).toHaveValue("Unsaved correction");
  responseKind = "server";
  await openSection(user, "Seed details");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not save or refresh",
  );
});

test("reference combobox supports keyboard selection with accessible names", async () => {
  mockApi(directoryHandler([]));
  const user = await openSeeds();
  await user.click(await screen.findByRole("button", { name: "New seed lot" }));
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
  expect(screen.getByLabelText("Current inventory")).toBeInTheDocument();
  expect(
    within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole(
      "link",
      { name: "Seeds" },
    ),
  ).toBeInTheDocument();
});

test("BULK-001 seed selection is transient, visible-only and reset by search", async () => {
  mockApi(
    directoryHandler([lot(), lot({ id: "second", label: "Second packet" })]),
  );
  const user = await openSeeds();
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "2 records",
  );
  expect(
    screen.getByRole("button", { name: "Select records" }).parentElement,
  ).toBe(screen.getByLabelText("Directory results").parentElement);
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Select records" }));
  await user.click(screen.getByRole("button", { name: "Select visible" }));
  expect(screen.getByText("2 selected")).toBeVisible();
  expect(
    screen.getByRole("checkbox", { name: /Select Seed Lot.*Blue packet/i }),
  ).toBeChecked();
  await user.type(
    screen.getByRole("searchbox", { name: "Search seed inventory" }),
    "Blue",
  );
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Directory results")).toHaveTextContent(
    "1 record",
  );
  expect(screen.getByRole("button", { name: "Select records" })).toBeEnabled();
});

test("BULK-001 successful move refreshes the directory, clears preview and retains filters", async () => {
  const target = {
    ...location,
    id: "01900000-0000-7000-8000-000000000999",
    display_path: "Greenhouse → New bench",
    usage_scopes: ["seed_lots"],
  };
  const rows = [
    lot(),
    lot({
      id: "01900000-0000-7000-8000-000000000502",
      label: "Blue second packet",
      location_id: target.id,
      location: { id: target.id, display_path: target.display_path },
    }),
  ];
  let reads = 0;
  mockApi(
    directoryHandler(rows, (path, init) => {
      if (path === "/api/v1/seed-lots" && !init?.method) {
        reads += 1;
        return json(rows);
      }
      if (path === "/api/v1/locations") return json([target]);
      if (path === "/api/v1/bulk/location/preview") {
        const payload = JSON.parse(requestBody(init)) as {
          records: { kind: string; id: string }[];
        };
        expect(payload.records).toEqual(
          rows.map((row) => ({ kind: "seed_lot", id: row.id })),
        );
        return json({
          target_location_id: target.id,
          target_location: target.display_path,
          target_updated_at: target.updated_at,
          selected_count: 2,
          move_count: 1,
          unchanged_count: 1,
          can_apply: true,
          rows: rows.map((row, index) => ({
            kind: "seed_lot",
            id: row.id,
            label: row.label,
            current_location_id: row.location_id,
            current_location: row.location.display_path,
            updated_at: row.updated_at,
            status: index ? "unchanged" : "move",
            code: null,
            message: null,
          })),
        });
      }
      if (path === "/api/v1/bulk/location/apply") {
        rows[0] = lot({
          location_id: target.id,
          location: { id: target.id, display_path: target.display_path },
        });
        return json({ moved_count: 1, unchanged_count: 1 });
      }
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.type(
    screen.getByRole("searchbox", { name: "Search seed inventory" }),
    "Blue",
  );
  const hash = window.location.hash;
  await user.click(screen.getByRole("button", { name: "Select records" }));
  await user.click(screen.getByRole("button", { name: "Select visible" }));
  await user.click(screen.getByRole("button", { name: "Bulk actions" }));
  await user.click(screen.getByRole("button", { name: "Move to location" }));
  const dialog = screen.getByRole("dialog", { name: "Move to location" });
  await user.click(
    await within(dialog).findByRole("combobox", { name: "Target Location" }),
  );
  await user.click(
    within(dialog).getByRole("button", { name: target.display_path }),
  );
  await user.click(
    within(dialog).getByRole("button", { name: "Preview move" }),
  );
  await user.click(
    await within(dialog).findByRole("button", { name: "Apply move (1)" }),
  );
  await waitFor(() => {
    expect(reads).toBeGreaterThan(1);
  });
  expect(await screen.findByText("1 moved · 1 already there.")).toBeVisible();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("complementary", { name: "Quick preview" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("searchbox", { name: "Search seed inventory" }),
  ).toHaveValue("Blue");
  expect(window.location.hash).toBe(hash);
  const refreshed = screen.getByRole("button", { name: /Blue packet/ });
  expect(refreshed).toBeVisible();
  expect(refreshed).not.toHaveTextContent("New bench");
  setViewportMatches(false);
  await user.click(refreshed);
  expect(
    await screen.findByRole("complementary", { name: "Quick preview" }),
  ).toHaveTextContent("New bench");
});

const purchaseOrder = {
  id: "01900000-0000-7000-8000-000000000951",
  supplier_id: supplier.id,
  supplier: { id: supplier.id, name: supplier.name },
  order_reference: "PO-SEEDS",
  ordered_on: { precision: "year", year: 2026 },
  total_price: "18.00",
  currency: "EUR",
  seed_lot_count: 0,
  notes: null,
  created_at: supplier.created_at,
  updated_at: supplier.updated_at,
  seed_lots: [],
  seed_lots_total: 0,
  seed_lots_offset: 0,
  seed_lots_limit: 50,
};

test.each([
  [409, "order_supplier_conflict", "Supplier must match the Order Supplier"],
  [409, "order_source_conflict", "Only purchased or purchased-fruit"],
  [404, "order_not_found", "selected Order no longer exists"],
])(
  "Order refusal %s %s reveals Acquisition and preserves the SeedLot draft",
  async (status, code, message) => {
    const linked = lot({ order_id: purchaseOrder.id });
    mockApi(
      directoryHandler([linked], (path, init) => {
        if (path.includes("/api/v1/seed-lots/") && init?.method === "PUT")
          return json({ detail: { code, message: "Domain conflict" } }, status);
        if (path.startsWith(`/api/v1/orders/${purchaseOrder.id}`))
          return json(purchaseOrder);
        if (path.startsWith("/api/v1/orders?"))
          return json({
            items: [purchaseOrder],
            total: 1,
            offset: 0,
            limit: 50,
          });
      }),
    );
    window.history.replaceState(null, "", `#/seeds/${linked.id}`);
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Edit seed lot" }),
    );
    await user.clear(screen.getByLabelText("Lot label"));
    await user.type(screen.getByLabelText("Lot label"), "Retained draft");
    await openSection(user, "Seed details");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Acquisition" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });
    expect(
      screen.getByLabelText("Order", { selector: "select" }),
    ).toHaveFocus();
    expect(screen.getByLabelText("Order", { selector: "select" })).toHaveValue(
      purchaseOrder.id,
    );
    expect(screen.getByLabelText("Lot label")).toHaveValue("Retained draft");
  },
);

test("create from Order prefills only truthful purchase context in the normal SeedLot form", async () => {
  window.history.replaceState(
    null,
    "",
    `#/seeds?action=create&order=${purchaseOrder.id}`,
  );
  mockApi(
    directoryHandler([], (path) => {
      if (path.endsWith("/purchase-context/preview"))
        return json({
          order: purchaseOrder,
          current: {
            source_kind: "unknown",
            supplier_id: null,
            order_id: null,
            acquisition_date: null,
          },
          seed_lot_id: null,
          seed_lot_updated_at: null,
          proposed_source: "purchased",
          supplier_action: "fill",
          date_action: "copy",
          can_apply: true,
          conflict: null,
        });
      if (path.endsWith("/purchase-context/apply"))
        return json({
          order: purchaseOrder,
          context: {
            source_kind: "purchased",
            supplier_id: supplier.id,
            order_id: purchaseOrder.id,
            acquisition_date: null,
          },
          confirmation: {
            context: { source_kind: "unknown" },
            expected_order_updated_at: purchaseOrder.updated_at,
            use_order_supplier: true,
            use_order_date: false,
          },
          seed_lot: null,
        });
      if (path.startsWith(`/api/v1/orders/${purchaseOrder.id}`))
        return json(purchaseOrder);
      if (path.startsWith("/api/v1/orders?"))
        return json({ items: [purchaseOrder], total: 1, offset: 0, limit: 50 });
    }),
  );
  const user = userEvent.setup();
  render(<App />);
  expect(
    await screen.findByRole("combobox", { name: "Botanical identity" }),
  ).toHaveValue("");
  await openSection(user, "Acquisition");
  expect(screen.getByLabelText("Source")).toHaveValue("purchased");
  expect(
    await screen.findByLabelText("Supplier from linked Order"),
  ).toHaveTextContent(supplier.name);
  expect(
    screen.queryByRole("combobox", { name: "Supplier" }),
  ).not.toBeInTheDocument();
  expect(
    await screen.findByLabelText("Order", { selector: "select" }),
  ).toHaveValue(purchaseOrder.id);
  expect(
    await screen.findByLabelText("Recorded seed lot knowledge"),
  ).toHaveTextContent("Acquisition date: Unknown");
  await openSection(user, "Origin");
  expect(
    screen.getByRole("combobox", { name: "Material provenance" }),
  ).toHaveValue("");
});

test("SeedLot detail keeps Order, Supplier, acquisition, provenance and Location separate", async () => {
  const linked = lot({
    order_id: purchaseOrder.id,
    order: {
      id: purchaseOrder.id,
      order_reference: "PO-SEEDS",
      ordered_on: purchaseOrder.ordered_on,
    },
  });
  mockApi(directoryHandler([linked]));
  window.history.replaceState(null, "", `#/seeds/${linked.id}`);
  render(<App />);
  expect(await screen.findByRole("link", { name: "PO-SEEDS" })).toHaveAttribute(
    "href",
    `#/orders/${purchaseOrder.id}`,
  );
  expect(
    screen.getAllByRole("link", { name: supplier.name }).length,
  ).toBeGreaterThan(0);
  expect(screen.getAllByText(place.display_path).length).toBeGreaterThan(0);
  expect(screen.getAllByText(location.display_path).length).toBeGreaterThan(0);
});

test("SeedLot selection previews without mutating; Apply updates acquisition only and preserves other drafts", async () => {
  const existing = lot({
    source_kind: "unknown",
    supplier_id: null,
    supplier: null,
    order_id: null,
    order: null,
    acquisition_date: null,
  });
  const authoritative = {
    ...existing,
    source_kind: "purchased",
    supplier_id: supplier.id,
    supplier: purchaseOrder.supplier,
    order_id: purchaseOrder.id,
    order: {
      id: purchaseOrder.id,
      order_reference: purchaseOrder.order_reference,
      ordered_on: purchaseOrder.ordered_on,
    },
    updated_at: "2026-10-08T10:00:00Z",
  };
  let applies = 0;
  mockApi(
    directoryHandler([existing], (path, init) => {
      if (path.endsWith("/purchase-context/preview"))
        return json({
          order: purchaseOrder,
          seed_lot_id: existing.id,
          seed_lot_updated_at: existing.updated_at,
          current: {
            source_kind: "unknown",
            supplier_id: null,
            order_id: null,
            acquisition_date: null,
          },
          current_supplier: null,
          proposed_source: "purchased",
          supplier_action: "fill",
          date_action: "copy",
          can_apply: true,
          conflict: null,
        });
      if (path.endsWith("/purchase-context/apply")) {
        applies++;
        return json({
          order: purchaseOrder,
          context: {
            source_kind: "purchased",
            supplier_id: supplier.id,
            order_id: purchaseOrder.id,
            acquisition_date: null,
          },
          confirmation: JSON.parse(requestBody(init)) as unknown,
          seed_lot: authoritative,
        });
      }
      if (path.startsWith(`/api/v1/orders/${purchaseOrder.id}`))
        return json(purchaseOrder);
      if (path.startsWith("/api/v1/orders?"))
        return json({ items: [purchaseOrder], total: 1, offset: 0, limit: 50 });
    }),
  );
  window.history.replaceState(null, "", `#/seeds/${existing.id}`);
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "Edit seed lot" }),
  );
  await user.clear(screen.getByLabelText("Lot label"));
  await user.type(screen.getByLabelText("Lot label"), "Unsaved identity draft");
  await openSection(user, "Acquisition");
  await screen.findByRole("option", { name: /PO-SEEDS/ });
  await user.selectOptions(
    screen.getByLabelText("Order", { selector: "select" }),
    purchaseOrder.id,
  );
  const purchaseDialog = await screen.findByRole("dialog", {
    name: "Review purchase context",
  });
  expect(applies).toBe(0);
  expect(screen.getByLabelText("Source")).toHaveValue("unknown");
  await user.click(
    within(purchaseDialog).getByRole("button", { name: "Cancel" }),
  );
  expect(screen.getByLabelText("Order", { selector: "select" })).toHaveValue(
    "",
  );
  expect(applies).toBe(0);
  await user.selectOptions(
    screen.getByLabelText("Order", { selector: "select" }),
    purchaseOrder.id,
  );
  await user.click(
    await screen.findByRole("button", { name: "Apply purchase context" }),
  );
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Review purchase context" }),
    ).not.toBeInTheDocument();
  });
  expect(applies).toBe(1);
  expect(screen.getByLabelText("Source")).toHaveValue("purchased");
  expect(screen.getByLabelText("Order", { selector: "select" })).toHaveValue(
    purchaseOrder.id,
  );
  expect(
    await screen.findByLabelText("Recorded seed lot knowledge"),
  ).toHaveTextContent("Acquisition date: Unknown");
  await openSection(user, "Essentials");
  expect(screen.getByLabelText("Lot label")).toHaveValue(
    "Unsaved identity draft",
  );
});

test("contextual edit retains Photos underneath, saves from any section and restores its trigger", async () => {
  let current = lot();
  let body: unknown;
  mockApi(
    directoryHandler([], (path, init) => {
      if (path === "/api/v1/seed-lots") return json([current]);
      if (path.includes("/photos")) return json([]);
      if (path.includes("/api/v1/seed-lots/") && init?.method === "PUT") {
        body = JSON.parse(requestBody(init)) as unknown;
        current = lot({ label: "Edited packet" });
        return json(current);
      }
    }),
  );
  window.history.replaceState(null, "", `#/seeds/${current.id}?tab=photos`);
  const user = userEvent.setup();
  render(<App />);
  const trigger = await screen.findByRole("button", { name: "Edit seed lot" });
  const background = document.querySelector("#panel-photos");
  await user.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Edit Blue packet" });
  expect(document.querySelector("#panel-photos")).toBe(background);
  expect(document.querySelector(".seed-context-page")).toHaveAttribute("inert");
  expect(document.querySelector(".seed-context-page")).toHaveAttribute(
    "aria-hidden",
    "true",
  );
  expect(window.location.hash).toBe(`#/seeds/${current.id}?tab=edit`);
  expect(dialog).toContainElement(document.activeElement as HTMLElement);
  await user.clear(within(dialog).getByLabelText("Lot label"));
  await user.type(within(dialog).getByLabelText("Lot label"), "Edited packet");
  for (const section of [
    "Essentials",
    "Inventory",
    "Acquisition",
    "Origin",
    "Seed details",
  ]) {
    await user.click(within(dialog).getByRole("tab", { name: section }));
    expect(
      within(dialog).getByRole("button", { name: "Save changes" }),
    ).toBeVisible();
    expect(
      within(dialog).queryByRole("button", { name: "Next" }),
    ).not.toBeInTheDocument();
  }
  await user.click(within(dialog).getByRole("tab", { name: "Acquisition" }));
  await user.click(
    within(dialog).getByRole("button", { name: "Save changes" }),
  );
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Edit Blue packet" }),
    ).not.toBeInTheDocument();
  });
  expect(window.location.hash).toBe(`#/seeds/${current.id}?tab=photos`);
  expect(screen.getByRole("tab", { name: "Photos" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(document.querySelector("#panel-photos")).toBe(background);
  expect(screen.getByRole("button", { name: "Edit seed lot" })).toHaveFocus();
  expect(body).toMatchObject({
    supplier_id: supplier.id,
    acquisition_date: { precision: "year", year: 2024 },
  });
  expect(screen.getByRole("status")).toHaveTextContent(
    "Seed lot changes were saved",
  );
});

test("directory modal cancellation retains search, inspector and focus; Escape protects dirty values", async () => {
  mockApi(directoryHandler([lot()]));
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const user = await openSeeds();
  setViewportMatches(false);
  await user.type(
    screen.getByRole("searchbox", { name: "Search seed inventory" }),
    "Blue",
  );
  await user.click(screen.getByRole("button", { name: /Blue packet/ }));
  const trigger = within(
    screen.getByRole("complementary", { name: "Quick preview" }),
  ).getByRole("button", { name: "Edit" });
  const oldHash = window.location.hash;
  await user.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Edit Blue packet" });
  const first = within(dialog).getByRole("link", { name: "Seeds" });
  expect(first).toHaveFocus();
  await user.keyboard("{Shift>}{Tab}{/Shift}");
  expect(
    within(dialog).getByRole("button", { name: "Save changes" }),
  ).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(first).toHaveFocus();
  await user.type(within(dialog).getByLabelText("Lot label"), " draft");
  await user.keyboard("{Escape}");
  expect(confirm).toHaveBeenCalledWith("Discard unsaved seed lot changes?");
  expect(within(dialog).getByLabelText("Lot label")).toHaveValue(
    "Blue packet draft",
  );
  confirm.mockReturnValue(true);
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Edit Blue packet" }),
    ).not.toBeInTheDocument();
  });
  expect(window.location.hash).toBe(oldHash);
  expect(
    screen.getByRole("searchbox", { name: "Search seed inventory" }),
  ).toHaveValue("Blue");
  expect(
    screen.getByRole("complementary", { name: "Quick preview" }),
  ).toBeVisible();
  expect(trigger).toHaveFocus();
});

test("browser Back closes a clean edit before leaving its detail context", async () => {
  mockApi(directoryHandler([lot()]));
  window.history.replaceState(null, "", `#/seeds/${lot().id}`);
  const user = userEvent.setup();
  render(<App />);
  const trigger = await screen.findByRole("button", { name: "Edit seed lot" });
  await user.click(trigger);
  expect(
    screen.getByRole("dialog", { name: "Edit Blue packet" }),
  ).toBeVisible();
  act(() => {
    window.history.back();
  });
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Edit Blue packet" }),
    ).not.toBeInTheDocument();
  });
  expect(window.location.hash).toBe(`#/seeds/${lot().id}`);
  expect(screen.getByRole("region", { name: "Seed lot detail" })).toBeVisible();
  expect(trigger).toHaveFocus();
});

test.each(["tab=edit", "action=edit"])(
  "direct edit %s is the same full-page editor without a fabricated background",
  async (query) => {
    mockApi(directoryHandler([lot()]));
    window.history.replaceState(null, "", `#/seeds/${lot().id}?${query}`);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByLabelText("Lot label")).toHaveValue(
      "Blue packet",
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      document.querySelector(".edit-workspace-fallback"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(
      await screen.findByRole("button", { name: "Edit seed lot" }),
    ).toBeVisible();
    expect(window.location.hash).toBe(`#/seeds/${lot().id}`);
  },
);

test.each(["known", "unknown", "no-order"])(
  "Acquisition adapts Supplier for %s Order without changing persisted knowledge or dates",
  async (mode) => {
    const order = {
      ...purchaseOrder,
      supplier_id: mode === "known" ? supplier.id : null,
      supplier: mode === "known" ? purchaseOrder.supplier : null,
      ordered_on: null,
    };
    let current = lot({ order_id: mode === "no-order" ? null : order.id });
    let body: unknown;
    mockApi(
      directoryHandler([], (path, init) => {
        if (path === "/api/v1/seed-lots") return json([current]);
        if (path.startsWith(`/api/v1/orders/${order.id}`)) return json(order);
        if (path.startsWith("/api/v1/orders?"))
          return json({ items: [order], total: 1, offset: 0, limit: 50 });
        if (path.includes("/api/v1/seed-lots/") && init?.method === "PUT") {
          body = JSON.parse(requestBody(init)) as unknown;
          current = lot({ order_id: null });
          return json(current);
        }
      }),
    );
    window.history.replaceState(null, "", `#/seeds/${current.id}?tab=edit`);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Lot label");
    await openSection(user, "Acquisition");
    if (mode !== "no-order") {
      expect(
        await screen.findByLabelText("Supplier from linked Order"),
      ).toHaveTextContent(mode === "known" ? supplier.name : "Not recorded");
      expect(
        screen.queryByRole("combobox", { name: "Supplier" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("group", { name: "Acquisition date" }),
      ).not.toBeInTheDocument();
      expect(
        screen.getByLabelText("Recorded seed lot knowledge"),
      ).toHaveTextContent(
        `Supplier: ${supplier.name} · Acquisition date: 2024`,
      );
    } else {
      expect(
        await screen.findByRole("combobox", { name: "Supplier" }),
      ).toHaveValue(supplier.name);
      expect(
        within(
          screen.getByRole("group", { name: "Acquisition date" }),
        ).getByLabelText("Year"),
      ).toHaveValue(2024);
    }
    if (mode !== "no-order") {
      expect(
        screen.getByRole("region", { name: "Order transaction information" }),
      ).toHaveTextContent("Date unknown");
      await user.selectOptions(
        screen.getByLabelText("Order", { selector: "select" }),
        "",
      );
      expect(screen.getByRole("combobox", { name: "Supplier" })).toHaveValue(
        supplier.name,
      );
      expect(
        within(
          screen.getByRole("group", { name: "Acquisition date" }),
        ).getByLabelText("Year"),
      ).toHaveValue(2024);
    }
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await screen.findByRole("button", { name: "Edit seed lot" });
    expect(body).toMatchObject({
      order_id: null,
      source_kind: "purchased",
      supplier_id: supplier.id,
      acquisition_date: { precision: "year", year: 2024 },
    });
  },
);

test("dirty browser Back refuses departure without losing the draft or adding a replacement entry", async () => {
  mockApi(directoryHandler([lot()]));
  window.history.replaceState(null, "", `#/seeds/${lot().id}`);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "Edit seed lot" }),
  );
  await user.type(screen.getByLabelText("Lot label"), " draft");
  const length = window.history.length;
  act(() => {
    window.history.back();
  });
  await waitFor(() => {
    expect(confirm).toHaveBeenCalledWith("Discard unsaved seed lot changes?");
  });
  await waitFor(() => {
    expect(window.location.hash).toBe(`#/seeds/${lot().id}?tab=edit`);
  });
  expect(window.history.length).toBe(length);
  expect(screen.getByLabelText("Lot label")).toHaveValue("Blue packet draft");
  confirm.mockReturnValue(true);
  act(() => {
    window.history.back();
  });
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Edit Blue packet" }),
    ).not.toBeInTheDocument();
  });
  expect(window.location.hash).toBe(`#/seeds/${lot().id}`);
});

test("an Order and SeedLot with unknown Supplier retain truthful absence", async () => {
  const order = {
    ...purchaseOrder,
    supplier_id: null,
    supplier: null,
    ordered_on: null,
  };
  const current = lot({
    supplier_id: null,
    supplier: null,
    order_id: order.id,
  });
  mockApi(
    directoryHandler([current], (path) => {
      if (path.startsWith(`/api/v1/orders/${order.id}`)) return json(order);
    }),
  );
  window.history.replaceState(null, "", `#/seeds/${current.id}?tab=edit`);
  const user = userEvent.setup();
  render(<App />);
  await screen.findByLabelText("Lot label");
  await openSection(user, "Acquisition");
  expect(
    await screen.findByLabelText("Supplier from linked Order"),
  ).toHaveTextContent("Not recorded");
  expect(
    screen.queryByRole("combobox", { name: "Supplier" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("region", { name: "Order transaction information" }),
  ).toHaveTextContent("Date unknown");
  expect(
    screen.getByLabelText("Recorded seed lot knowledge"),
  ).toHaveTextContent("Supplier: Not recorded · Acquisition date: 2024");
  expect(
    screen.queryByRole("group", { name: "Acquisition date" }),
  ).not.toBeInTheDocument();
});

test("hash-route departure also closes contextual edit and dirty editor links require confirmation", async () => {
  mockApi(directoryHandler([lot()]));
  window.history.replaceState(null, "", `#/seeds/${lot().id}`);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const user = userEvent.setup();
  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: "Edit seed lot" }),
  );
  const dialog = screen.getByRole("dialog", { name: "Edit Blue packet" });
  await user.type(within(dialog).getByLabelText("Lot label"), " draft");
  await user.click(within(dialog).getByRole("link", { name: "Seeds" }));
  expect(confirm).toHaveBeenCalledOnce();
  expect(window.location.hash).toBe(`#/seeds/${lot().id}?tab=edit`);
  expect(dialog).toBeVisible();
  await user.clear(within(dialog).getByLabelText("Lot label"));
  await user.type(within(dialog).getByLabelText("Lot label"), "Blue packet");
  act(() => {
    window.history.replaceState(null, "", `#/seeds/${lot().id}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Edit Blue packet" }),
    ).not.toBeInTheDocument();
  });
  expect(screen.getByRole("button", { name: "Edit seed lot" })).toHaveFocus();
});

test("successful edit closes immediately and restores its explicit invoker even without click focus or history events", async () => {
  const current = lot();
  mockApi(
    directoryHandler([current], (path, init) => {
      if (path.includes("/api/v1/seed-lots/") && init?.method === "PUT")
        return json(current);
    }),
  );
  window.history.replaceState(null, "", `#/seeds/${current.id}`);
  const user = userEvent.setup();
  render(<App />);
  const trigger = await screen.findByRole("button", { name: "Edit seed lot" });
  fireEvent.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Edit Blue packet" });
  const back = vi
    .spyOn(window.history, "back")
    .mockImplementation(() => undefined);
  await user.click(
    within(dialog).getByRole("button", { name: "Save changes" }),
  );
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Edit Blue packet" }),
    ).not.toBeInTheDocument();
  });
  expect(back).toHaveBeenCalledOnce();
  expect(
    document.querySelector(".edit-workspace-fallback"),
  ).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
  expect(document.querySelector(".seed-context-page")).not.toHaveAttribute(
    "inert",
  );
});

test.each([false, true])(
  "backdrop uses the same dismissal guard and returns to Details (dirty=%s)",
  async (dirty) => {
    mockApi(directoryHandler([lot()]));
    window.history.replaceState(null, "", `#/seeds/${lot().id}?tab=photos`);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<App />);
    const trigger = await screen.findByRole("button", {
      name: "Edit seed lot",
    });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Edit Blue packet" });
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
    if (dirty)
      await user.type(within(dialog).getByLabelText("Lot label"), " draft");
    fireEvent.click(dialog, { clientX: 20, clientY: 20 });
    if (dirty) {
      expect(confirm).toHaveBeenCalledWith("Discard unsaved seed lot changes?");
      expect(dialog).toBeInTheDocument();
      expect(within(dialog).getByLabelText("Lot label")).toHaveValue(
        "Blue packet draft",
      );
      confirm.mockReturnValue(true);
      fireEvent.click(dialog, { clientX: 20, clientY: 20 });
    } else expect(confirm).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(screen.getByRole("tab", { name: "Photos" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(trigger).toHaveFocus();
  },
);

test("Overview keeps current-state facts and Sowings has one canonical start action", async () => {
  const record = lot({
    harvest_date: { precision: "month", year: 2024, month: 6 },
    expected_viability_until: { precision: "year", year: 2027 },
    provenance_site: {
      id: "site-id",
      name: "Garden bed",
      geographic_place_path: "Thailand",
    },
  });
  mockApi(
    directoryHandler([record], (path) =>
      path === "/api/v1/sowings"
        ? json([
            {
              id: "sowing-id",
              seed_lot_id: record.id,
              label: "Tray A",
              lifecycle: "active",
              sowing_date: { precision: "day", year: 2026, month: 10, day: 1 },
              quantity: {
                kind: "seed_count",
                value: "12",
                unit: null,
                is_approximate: false,
              },
              germinated_count: 7,
              location: null,
            },
          ])
        : undefined,
    ),
  );
  const user = await openSeeds();
  await user.click(await screen.findByRole("button", { name: /Blue packet/ }));
  const inventory = screen.getByLabelText("Current inventory");
  expect(screen.getByRole("heading", { name: "At a glance" })).toBeVisible();
  expect(
    within(inventory)
      .getAllByRole("term")
      .map((node) => node.textContent),
  ).toEqual(["Lifecycle", "Remaining", "Storage"]);
  expect(within(inventory).getAllByRole("definition")).toHaveLength(3);
  expect(screen.getByRole("region", { name: "Acquisition" })).toHaveTextContent(
    "Purchased",
  );
  expect(screen.getByRole("region", { name: "Origin" })).toHaveTextContent(
    "Thailand",
  );
  expect(inventory).toHaveTextContent("Active");
  expect(inventory).toHaveTextContent("50 seeds");
  expect(
    within(inventory).getByRole("link", { name: location.display_path }),
  ).toHaveAttribute("href", `#/locations/${location.id}`);
  expect(screen.getByRole("link", { name: supplier.name })).toHaveAttribute(
    "href",
    `#/suppliers/${supplier.id}`,
  );
  expect(
    screen.getByRole("link", { name: "Thailand → Garden bed" }),
  ).toHaveAttribute("href", "#/geography/site-id");
  expect(
    screen.getByRole("link", { name: place.display_path }),
  ).toHaveAttribute("href", `#/geography?place=${place.id}`);
  const dates = screen.getByRole("region", { name: "Dates & condition" });
  expect(
    within(dates)
      .getAllByRole("term")
      .map((node) => node.textContent),
  ).toEqual(["Acquired", "Harvested", "Expected viability"]);
  expect(
    within(dates)
      .getAllByRole("definition")
      .map((node) => node.textContent),
  ).toEqual(["2024", "2024-06", "2027"]);
  expect(screen.getByRole("region", { name: "Notes" })).toHaveTextContent(
    "Keep dry.",
  );
  expect(
    screen.getByRole("heading", { name: "Upcoming activities" }),
  ).toBeVisible();
  await user.click(screen.getByRole("tab", { name: "Sowings" }));
  expect(await screen.findByRole("link", { name: /Tray A/ })).toHaveAttribute(
    "href",
    "#/sowings/sowing-id",
  );
  expect(screen.getByRole("tabpanel")).toHaveTextContent("12 seeds used");
  expect(screen.getByRole("tabpanel")).toHaveTextContent("7 germinated");
  expect(screen.getAllByRole("link", { name: "Start sowing" })).toHaveLength(1);
  expect(
    screen.queryByRole("link", { name: "Start another sowing" }),
  ).not.toBeInTheDocument();
});

test("Details empty Sowings and Lineage are plain messages while Photos retains its workspace", async () => {
  mockApi(
    directoryHandler([lot()], (path) => {
      if (path === "/api/v1/sowings" || path.endsWith("/photos"))
        return json([]);
      if (path.endsWith("/lineage"))
        return json({
          subject: { kind: "seed_lot", id: lot().id },
          ancestors: [],
        });
      return undefined;
    }),
  );
  const user = await openSeeds();
  await user.click(await screen.findByRole("button", { name: /Blue packet/ }));
  await user.click(screen.getByRole("tab", { name: "Sowings" }));
  expect(
    (await screen.findByText("No sowings yet.")).closest(".empty-state"),
  ).toBeNull();
  expect(screen.getByRole("link", { name: "Start sowing" })).toBeVisible();
  await user.click(screen.getByRole("tab", { name: "Lineage" }));
  expect(
    (await screen.findByText("No recorded lineage.")).closest(".empty-state"),
  ).toBeNull();
  await user.click(screen.getByRole("tab", { name: "Photos" }));
  expect(
    (await screen.findByText("No photos yet.")).closest(
      ".detail-empty-message",
    ),
  ).toBeInTheDocument();
  for (const name of ["Add media", "Link existing", "External"])
    expect(screen.getByRole("button", { name })).toBeVisible();
});

test("Create labels expose the real required identity and keep optional acquisition facts optional", async () => {
  mockApi(directoryHandler([]));
  const user = await openSeeds();
  await user.click(screen.getByRole("button", { name: "New seed lot" }));
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toBeRequired();
  for (const label of ["Lot label", "Storage location", "Supplier", "Notes"])
    expect(screen.getByLabelText(label)).not.toBeRequired();
  expect(screen.queryByText(/\(optional\)/)).not.toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Source"), "purchased");
  expect(screen.getByRole("combobox", { name: "Supplier" })).not.toBeRequired();
  expect(
    screen.getByLabelText("Precision", { selector: "#acquisition-precision" }),
  ).not.toBeRequired();
  await user.selectOptions(
    screen.getByLabelText("Precision", { selector: "#acquisition-precision" }),
    "month",
  );
  expect(
    screen.getByLabelText("Year", { selector: "#acquisition-year" }),
  ).toBeRequired();
  expect(
    screen.getByLabelText("Month", { selector: "#acquisition-month" }),
  ).toBeRequired();
  expect(
    screen.queryByLabelText("Day", { selector: "#acquisition-day" }),
  ).not.toBeInTheDocument();
});

test("minimal Seed row retains quantity and moves storage context to Quick Preview", async () => {
  mockApi(directoryHandler([lot()]));
  const user = await openSeeds();
  setViewportMatches(false);
  const row = await screen.findByRole("button", { name: /Blue packet/ });
  expect(row).not.toHaveTextContent(location.display_path);
  expect(row).toHaveTextContent("remaining");
  await user.click(row);
  expect(
    screen.getByRole("complementary", { name: "Quick preview" }),
  ).toHaveTextContent(location.display_path);
});

test("New SeedLot Back keeps the Seeds parent and restores its create action", async () => {
  mockApi(directoryHandler([lot()]));
  const user = await openSeeds();
  await user.click(screen.getByRole("button", { name: "New seed lot" }));
  expect(window.location.hash).toBe("#/seeds?action=create");
  await browserBack();
  expect(window.location.hash).toBe("#/seeds");
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "New seed lot" })).toHaveFocus();
  });
  expect(
    screen.queryByRole("heading", { name: "Add seed lot" }),
  ).not.toBeInTheDocument();
});

test("identity-scoped Seeds survives URL reload, composes search and clears without losing lifecycle", async () => {
  const other = lot({
    id: "01900000-0000-7000-8000-000000000502",
    label: "Other packet",
    botanical_identity_id: secondIdentity.id,
    botanical_identity: {
      id: secondIdentity.id,
      display_label: secondIdentity.display_label,
    },
  });
  mockApi(directoryHandler([lot(), other]));
  const hash = `#/seeds?identity_id=${identity.id}&lifecycle=all&q=packet`;
  window.history.replaceState(null, "", hash);
  const user = userEvent.setup();
  const view = render(<App />);
  expect(
    await screen.findByRole("button", { name: /Blue packet/ }),
  ).toBeVisible();
  expect(screen.queryByRole("button", { name: /Other packet/ })).toBeNull();
  expect(
    screen.getByRole("button", { name: "Remove botanical identity filter" }),
  ).toHaveTextContent(identity.display_label);
  view.unmount();
  render(<App />);
  await screen.findByRole("button", { name: /Blue packet/ });
  await user.click(
    screen.getByRole("button", { name: "Remove botanical identity filter" }),
  );
  expect(
    await screen.findByRole("button", { name: /Other packet/ }),
  ).toBeVisible();
  expect(window.location.hash).toContain("lifecycle=all");
  expect(screen.getByLabelText("Search seed inventory")).toHaveValue("packet");
  await browserBack();
  await waitFor(() => {
    expect(screen.queryByRole("button", { name: /Other packet/ })).toBeNull();
  });
  expect(window.location.hash).toBe(hash);
});
