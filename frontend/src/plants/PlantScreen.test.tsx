import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "../App";

const identityId = "01900000-0000-7000-8000-000000000101";
const otherIdentityId = "01900000-0000-7000-8000-000000000102";
const seedLotId = "01900000-0000-7000-8000-000000000201";
const supplierId = "01900000-0000-7000-8000-000000000301";
const locationId = "01900000-0000-7000-8000-000000000401";
const placeId = "01900000-0000-7000-8000-000000000501";
const sowingId = "01900000-0000-7000-8000-000000000601";
const plantId = "01900000-0000-7000-8000-000000000701";
const groupId = "01900000-0000-7000-8000-000000000702";
const eventId = "01900000-0000-7000-8000-000000000801";

const identities = [
  {
    id: identityId,
    scientific_name: "Persea americana",
    cultivar_name: null,
    common_name: "Avocado",
    display_label: "Persea americana",
    created_at: "2026-08-31T10:00:00Z",
    updated_at: "2026-08-31T10:00:00Z",
  },
  {
    id: otherIdentityId,
    scientific_name: "Cyphomandra betacea",
    cultivar_name: null,
    common_name: "Tamarillo",
    display_label: "Cyphomandra betacea",
    created_at: "2026-08-31T10:00:00Z",
    updated_at: "2026-08-31T10:00:00Z",
  },
];

const supplier = {
  id: supplierId,
  name: "Rossi Nursery",
  kind: "nursery",
  website: null,
  email: null,
  phone: null,
  notes: null,
  retired_at: null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};
const location = {
  id: locationId,
  name: "Bench 4",
  parent_id: null,
  display_path: "Greenhouse → Bench 4",
  retired_at: null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};
const place = {
  id: placeId,
  name: "Sicily",
  parent_id: "world",
  display_path: "World → Europe → Italy → Sicily",
  place_kind: "custom",
  source_name: null,
  source_version: null,
  source_code_type: null,
  source_code: null,
  retired_at: null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};
const sowing = {
  id: sowingId,
  seed_lot_id: seedLotId,
  seed_lot: {
    id: seedLotId,
    label: "Tamarillo packet",
    lifecycle: "active",
    botanical_identity_id: otherIdentityId,
    botanical_identity_display_label: "Cyphomandra betacea",
  },
  label: "Tray A",
  sowing_date: { precision: "month", year: 2026, month: 4 },
  quantity: null,
  germinated_count: 12,
  location_id: null,
  location: null,
  substrate: null,
  method_container: null,
  pretreatment: null,
  temperature_min_c: null,
  temperature_max_c: null,
  environment: null,
  lifecycle: "completed",
  notes: null,
  created_at: "2026-08-31T10:00:00Z",
  updated_at: "2026-08-31T10:00:00Z",
};

function plant(overrides: Record<string, unknown> = {}) {
  return {
    id: plantId,
    botanical_identity_id: identityId,
    botanical_identity: { id: identityId, display_label: "Persea americana" },
    label: "Avocado #1",
    originating_sowing_id: null,
    originating_sowing: null,
    originating_plant_group_id: null,
    originating_plant_group: null,
    direct_origin_kind: "purchased",
    direct_origin_detail: null,
    supplier_id: supplierId,
    supplier: { id: supplierId, name: supplier.name },
    material_provenance_place_id: placeId,
    material_provenance: { id: placeId, display_path: place.display_path },
    location_id: locationId,
    location: { id: locationId, display_path: location.display_path },
    collection_entry_date: { precision: "year", year: 2025 },
    lifecycle: "active",
    notes: "Grafted specimen.",
    created_at: "2026-08-31T10:00:00Z",
    updated_at: "2026-08-31T10:00:00Z",
    ...overrides,
  };
}

function group(overrides: Record<string, unknown> = {}) {
  return {
    id: groupId,
    botanical_identity_id: otherIdentityId,
    botanical_identity: {
      id: otherIdentityId,
      display_label: "Cyphomandra betacea",
    },
    label: "Seedlings 2026",
    originating_sowing_id: sowingId,
    originating_sowing: {
      id: sowingId,
      label: "Tray A",
      lifecycle: "completed",
      seed_lot_id: seedLotId,
      botanical_identity_id: otherIdentityId,
      botanical_identity_display_label: "Cyphomandra betacea",
    },
    direct_origin_kind: null,
    direct_origin_detail: null,
    supplier_id: null,
    supplier: null,
    material_provenance_place_id: null,
    material_provenance: null,
    location_id: null,
    location: null,
    collection_entry_date: null,
    lifecycle: "completed",
    quantity: { value: 0, is_approximate: false },
    notes: null,
    created_at: "2026-08-31T10:00:00Z",
    updated_at: "2026-08-31T10:00:00Z",
    ...overrides,
  };
}

function journalEvent(kind: string, overrides: Record<string, unknown> = {}) {
  return {
    id: `${eventId.slice(0, -2)}${String(Object.keys(eventKinds).indexOf(kind) + 1).padStart(2, "0")}`,
    target: {
      type: "plant",
      id: plantId,
      label: "Avocado #1",
      lifecycle: "active",
    },
    kind,
    occurred_on: null,
    notes: null,
    destination_location_id: null,
    destination_location: null,
    created_at: "2026-09-02T10:00:00Z",
    updated_at: "2026-09-02T10:00:00Z",
    ...overrides,
  };
}

const eventKinds: Record<string, string> = {
  observation: "Observation",
  movement: "Movement",
  repotting: "Repotting",
  flowering: "Flowering",
  fruiting: "Fruiting",
  pruning: "Pruning",
  treatment: "Treatment",
  harvest: "Harvest",
  death: "Death",
  loss: "Loss",
  discarded: "Discarded",
  other: "Other",
};

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

function mockApi(handler: Handler, identityRecords = identities) {
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
      return Promise.resolve(json(identityRecords));
    const response = handler(path, init);
    if (!response)
      throw new Error(`Unhandled request: ${path} ${init?.method ?? "GET"}`);
    return Promise.resolve(response);
  });
}

function plantHandler(
  plants: unknown[],
  groups: unknown[],
  custom?: Handler,
): Handler {
  return (path, init) => {
    const customResponse = custom?.(path, init);
    if (customResponse !== undefined) return customResponse;
    const reading = !init?.method || init.method === "GET";
    if (path === "/api/v1/plants" && reading) return json(plants);
    if (path === "/api/v1/plant-groups" && reading) return json(groups);
    if (path.endsWith("/events") && reading) return json([]);
    if (path.startsWith("/api/v1/plants/") && reading) {
      const match = plants.find(
        (item) =>
          typeof item === "object" &&
          item !== null &&
          "id" in item &&
          item.id === path.split("/").at(-1),
      );
      return match ? json(match) : json({ detail: "not found" }, 404);
    }
    if (path.startsWith("/api/v1/plant-groups/") && reading) {
      const match = groups.find(
        (item) =>
          typeof item === "object" &&
          item !== null &&
          "id" in item &&
          item.id === path.split("/").at(-1),
      );
      return match ? json(match) : json({ detail: "not found" }, 404);
    }
    if (path === "/api/v1/sowings") return json([sowing]);
    if (path === "/api/v1/suppliers") return json([supplier]);
    if (path === "/api/v1/geographic-places") return json([place]);
    if (path === "/api/v1/locations") return json([location]);
    return undefined;
  };
}

async function openPlants() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "Plants" }));
  return user;
}

async function chooseReference(
  user: ReturnType<typeof userEvent.setup>,
  label: string,
  option: string,
) {
  await user.click(screen.getByRole("combobox", { name: label }));
  await user.click(screen.getByRole("button", { name: new RegExp(option) }));
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("Plants navigation exposes loading, empty, missing-identity, and failure states", async () => {
  mockApi((path) => {
    if (path === "/api/v1/plants" || path === "/api/v1/plant-groups")
      return new Promise<Response>(() => undefined);
    if (
      path === "/api/v1/sowings" ||
      path === "/api/v1/suppliers" ||
      path === "/api/v1/geographic-places" ||
      path === "/api/v1/locations"
    )
      return json([]);
    return undefined;
  });
  await openPlants();
  expect(screen.getByRole("status")).toHaveTextContent("Loading Plants");

  cleanup();
  vi.restoreAllMocks();
  mockApi(plantHandler([], []), []);
  await openPlants();
  expect(
    await screen.findByRole("heading", { name: "No Plants recorded yet" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "+ New" })).toBeDisabled();
  expect(
    screen.getByText(/Botanical identity is required/),
  ).toBeInTheDocument();

  cleanup();
  vi.restoreAllMocks();
  mockApi(
    plantHandler([], [], (path) =>
      path === "/api/v1/plants" ? json({ detail: "failed" }, 500) : undefined,
    ),
  );
  await openPlants();
  expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

test("unified rows, search, lifecycle and type filters, detail, and Back remain accessible", async () => {
  mockApi(plantHandler([plant()], [group()]));
  const user = await openPlants();
  const lifecycle = screen.getByRole("group", { name: "Lifecycle" });
  const recordType = screen.getByRole("group", { name: "Record type" });
  const plantRow = await screen.findByRole("button", {
    name: /Persea americana.*Avocado #1.*Plant.*Greenhouse → Bench 4.*Purchased · Rossi Nursery/s,
  });
  expect(within(plantRow).getByText("Plant")).toBeInTheDocument();
  expect(screen.queryByText("Seedlings 2026")).not.toBeInTheDocument();

  await user.click(within(lifecycle).getByRole("button", { name: "History" }));
  const groupRow = screen.getByRole("button", {
    name: /Cyphomandra betacea.*Seedlings 2026.*Group.*From sowing · Tray A.*0 plants/s,
  });
  expect(within(groupRow).getByText("Group")).toBeInTheDocument();
  await user.click(within(lifecycle).getByRole("button", { name: "All" }));

  const search = screen.getByRole("searchbox", { name: "Search Plants" });
  for (const query of ["Persea", "Avocado #1", "Bench 4", "Rossi Nursery"]) {
    await user.clear(search);
    await user.type(search, query);
    expect(screen.getByText("Avocado #1")).toBeInTheDocument();
  }
  await user.clear(search);
  await user.type(search, "Tray A");
  expect(screen.getByText("Seedlings 2026")).toBeInTheDocument();
  await user.clear(search);

  await user.click(within(recordType).getByRole("button", { name: "Plants" }));
  expect(screen.getByText("Avocado #1")).toBeInTheDocument();
  expect(screen.queryByText("Seedlings 2026")).not.toBeInTheDocument();
  await user.click(within(recordType).getByRole("button", { name: "Groups" }));
  expect(screen.getByText("Seedlings 2026")).toBeInTheDocument();
  expect(screen.queryByText("Avocado #1")).not.toBeInTheDocument();
  await user.click(within(lifecycle).getByRole("button", { name: "Active" }));
  expect(screen.getByText(/No Plants match/)).toBeInTheDocument();
  await user.click(within(lifecycle).getByRole("button", { name: "All" }));
  await user.click(within(recordType).getByRole("button", { name: "Plants" }));
  const selectedRow = screen.getByRole("button", { name: /Avocado #1/ });
  await user.click(selectedRow);
  expect(
    await screen.findByRole("heading", { name: "Persea americana" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Grafted specimen.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "← Back to Plants" }));
  expect(selectedRow).toHaveFocus();
});

test("one New disclosure chooses type and supports BotanicalIdentity-only Plant creation", async () => {
  const payloads: Record<string, unknown>[] = [];
  let plants: unknown[] = [];
  mockApi(
    plantHandler(plants, [], (path, init) => {
      if (path === "/api/v1/plants" && init?.method === "POST") {
        const payload = body(init);
        payloads.push(payload);
        const created = plant({
          ...payload,
          id: "created-plant",
          botanical_identity: {
            id: identityId,
            display_label: "Persea americana",
          },
          direct_origin_kind: payload.direct_origin_kind ?? "unknown",
          supplier: null,
          material_provenance: null,
          location: null,
          originating_sowing: null,
        });
        plants = [created];
        expect(new Headers(init.headers).get("X-CSRF-Token")).toBe("csrf");
        return json(created, 201);
      }
      if (path === "/api/v1/plants" && (!init?.method || init.method === "GET"))
        return json(plants);
      return undefined;
    }),
  );
  const user = await openPlants();
  const trigger = await screen.findByRole("button", { name: "+ New" });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  await user.click(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  expect(
    screen.getByRole("heading", { name: "What are you tracking?" }),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: /Plant.*One individually/s }),
  );
  const identity = screen.getByRole("combobox", {
    name: "Botanical identity",
  });
  await user.clear(identity);
  await user.type(identity, "Persea");
  await user.click(screen.getByRole("button", { name: "Persea americana" }));
  await user.click(screen.getByRole("button", { name: "Record Plant" }));
  expect(
    await screen.findByText("Plant was added to the collection."),
  ).toBeInTheDocument();
  expect(payloads[0]).toMatchObject({
    botanical_identity_id: identityId,
    label: null,
    originating_sowing_id: null,
    direct_origin_kind: "unknown",
    location_id: null,
    collection_entry_date: null,
    lifecycle: "active",
    notes: null,
  });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
});

test("minimal group creation keeps quantity unknown", async () => {
  const payloads: Record<string, unknown>[] = [];
  let groups: unknown[] = [];
  mockApi(
    plantHandler([], groups, (path, init) => {
      if (path === "/api/v1/plant-groups" && init?.method === "POST") {
        const payload = body(init);
        payloads.push(payload);
        const created = group({
          ...payload,
          id: "created-group",
          botanical_identity_id: identityId,
          botanical_identity: {
            id: identityId,
            display_label: "Persea americana",
          },
          quantity: null,
          originating_sowing: null,
          direct_origin_kind: "unknown",
        });
        groups = [created];
        return json(created, 201);
      }
      if (
        path === "/api/v1/plant-groups" &&
        (!init?.method || init.method === "GET")
      )
        return json(groups);
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: "+ New" }));
  await user.click(
    screen.getByRole("button", { name: /Plant group.*Multiple/s }),
  );
  await chooseReference(user, "Botanical identity", "Persea americana");
  expect(screen.getByLabelText("Kind")).toHaveValue("unknown");
  await user.click(screen.getByRole("button", { name: "Record Plant group" }));
  expect(payloads[0]).toMatchObject({
    botanical_identity_id: identityId,
    quantity: null,
    lifecycle: "active",
  });
});

test("direct origin, references, partial date, Location, lifecycle, notes, and stale Other detail map coherently", async () => {
  const payloads: Record<string, unknown>[] = [];
  let plants: unknown[] = [];
  mockApi(
    plantHandler(plants, [], (path, init) => {
      if (path === "/api/v1/plants" && init?.method === "POST") {
        const payload = body(init);
        payloads.push(payload);
        const created = plant({
          ...payload,
          id: "full",
          botanical_identity: {
            id: identityId,
            display_label: "Persea americana",
          },
        });
        plants = [created];
        return json(created, 201);
      }
      if (path === "/api/v1/plants" && (!init?.method || init.method === "GET"))
        return json(plants);
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: "+ New" }));
  await user.click(
    screen.getByRole("button", { name: /Plant.*One individually/s }),
  );
  await chooseReference(user, "Botanical identity", "Persea americana");
  await user.type(
    screen.getByLabelText("Label (optional)"),
    "Courtyard avocado",
  );
  await user.click(screen.getByRole("button", { name: "More details" }));
  await user.selectOptions(screen.getByLabelText("Direct origin"), "other");
  await user.type(
    screen.getByLabelText("Other origin detail"),
    "Market rescue",
  );
  await user.selectOptions(screen.getByLabelText("Direct origin"), "purchased");
  expect(
    screen.queryByLabelText("Other origin detail"),
  ).not.toBeInTheDocument();
  await user.selectOptions(
    screen.getByLabelText("Supplier (optional)"),
    supplierId,
  );
  await user.selectOptions(
    screen.getByLabelText("Material provenance (optional)"),
    placeId,
  );
  await user.selectOptions(
    screen.getByLabelText("Current location (optional)"),
    locationId,
  );
  await user.selectOptions(screen.getByLabelText("Precision"), "year");
  await user.clear(screen.getByLabelText("Year"));
  await user.type(screen.getByLabelText("Year"), "2024");
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "dead");
  await user.type(
    screen.getByLabelText("Notes (optional)"),
    "Retained history.",
  );
  await user.click(screen.getByRole("button", { name: "Record Plant" }));
  expect(payloads[0]).toMatchObject({
    label: "Courtyard avocado",
    direct_origin_kind: "purchased",
    direct_origin_detail: null,
    supplier_id: supplierId,
    material_provenance_place_id: placeId,
    location_id: locationId,
    collection_entry_date: { precision: "year", year: 2024 },
    lifecycle: "dead",
    notes: "Retained history.",
  });
});

test("known Sowing clears direct provenance and preserves an independently chosen identity", async () => {
  const payloads: Record<string, unknown>[] = [];
  let plants: unknown[] = [];
  mockApi(
    plantHandler(plants, [], (path, init) => {
      if (path === "/api/v1/plants" && init?.method === "POST") {
        const payload = body(init);
        payloads.push(payload);
        const created = plant({
          ...payload,
          id: "sowing-plant",
          botanical_identity: {
            id: identityId,
            display_label: "Persea americana",
          },
          originating_sowing: group().originating_sowing,
          supplier: null,
          material_provenance: null,
        });
        plants = [created];
        return json(created, 201);
      }
      if (path === "/api/v1/plants" && (!init?.method || init.method === "GET"))
        return json(plants);
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: "+ New" }));
  await user.click(
    screen.getByRole("button", { name: /Plant.*One individually/s }),
  );
  await chooseReference(user, "Botanical identity", "Persea americana");
  await user.click(screen.getByRole("button", { name: "More details" }));
  await user.selectOptions(screen.getByLabelText("Direct origin"), "purchased");
  await user.selectOptions(
    screen.getByLabelText("Supplier (optional)"),
    supplierId,
  );
  await user.click(screen.getByLabelText("Known Sowing"));
  expect(screen.queryByLabelText("Direct origin")).not.toBeInTheDocument();
  expect(
    screen.queryByLabelText("Supplier (optional)"),
  ).not.toBeInTheDocument();
  await chooseReference(user, "Originating Sowing", "Tray A");
  await user.click(
    screen.getByLabelText("Direct / origin not tracked through a Sowing"),
  );
  expect(screen.getByLabelText("Direct origin")).toHaveValue("unknown");
  expect(screen.queryByLabelText("Originating Sowing")).not.toBeInTheDocument();
  await user.click(screen.getByLabelText("Known Sowing"));
  await chooseReference(user, "Originating Sowing", "Tray A");
  await user.click(screen.getByRole("button", { name: "Record Plant" }));
  expect(payloads[0]).toMatchObject({
    botanical_identity_id: identityId,
    originating_sowing_id: sowingId,
    direct_origin_kind: null,
    direct_origin_detail: null,
    supplier_id: null,
    material_provenance_place_id: null,
  });
});

test("group count validation covers exact and approximate zero before valid atomic historical saves", async () => {
  const payloads: Record<string, unknown>[] = [];
  let groups: unknown[] = [];
  mockApi(
    plantHandler([], groups, (path, init) => {
      if (path === "/api/v1/plant-groups" && init?.method === "POST") {
        const payload = body(init);
        payloads.push(payload);
        const created = group({
          ...payload,
          id: `group-${String(payloads.length)}`,
          botanical_identity: {
            id: identityId,
            display_label: "Persea americana",
          },
          originating_sowing: null,
        });
        groups = [created];
        return json(created, 201);
      }
      if (
        path === "/api/v1/plant-groups" &&
        (!init?.method || init.method === "GET")
      )
        return json(groups);
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: "+ New" }));
  await user.click(
    screen.getByRole("button", { name: /Plant group.*Multiple/s }),
  );
  await chooseReference(user, "Botanical identity", "Persea americana");
  await user.selectOptions(screen.getByLabelText("Kind"), "exact");
  await user.type(screen.getByLabelText("Count"), "0");
  await user.click(screen.getByRole("button", { name: "Record Plant group" }));
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Exact zero is only valid",
  );
  await user.selectOptions(screen.getByLabelText("Kind"), "approximate");
  await user.click(screen.getByRole("button", { name: "Record Plant group" }));
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Approximate group count",
  );
  await user.click(screen.getByRole("button", { name: "More details" }));
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "lost");
  await user.selectOptions(screen.getByLabelText("Kind"), "exact");
  await user.click(screen.getByRole("button", { name: "Record Plant group" }));
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Exact zero is only valid",
  );
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "completed");
  await user.click(screen.getByRole("button", { name: "Record Plant group" }));
  expect(payloads[0]).toMatchObject({
    lifecycle: "completed",
    quantity: { value: 0, is_approximate: false },
  });
  await user.click(screen.getByRole("button", { name: "+ New" }));
  await user.click(
    screen.getByRole("button", { name: /Plant group.*Multiple/s }),
  );
  await chooseReference(user, "Botanical identity", "Persea americana");
  await user.selectOptions(screen.getByLabelText("Kind"), "approximate");
  await user.type(screen.getByLabelText("Count"), "30");
  await user.click(screen.getByRole("button", { name: "Record Plant group" }));
  expect(payloads[1]).toMatchObject({
    lifecycle: "active",
    quantity: { value: 30, is_approximate: true },
  });
});

test("full Plant and group PUT edits preserve form state on failure and apply coherent corrections", async () => {
  const puts: Record<string, unknown>[] = [];
  let failPlant = true;
  let plants: unknown[] = [plant()];
  let groups: unknown[] = [group()];
  mockApi(
    plantHandler(plants, groups, (path, init) => {
      if (path === `/api/v1/plants/${plantId}` && init?.method === "PUT") {
        if (failPlant) {
          failPlant = false;
          return json({ detail: "failed" }, 500);
        }
        const payload = body(init);
        puts.push(payload);
        const updated = plant({
          ...payload,
          location: null,
          supplier: null,
          material_provenance: null,
        });
        plants = [updated];
        return json(updated);
      }
      if (
        path === `/api/v1/plant-groups/${groupId}` &&
        init?.method === "PUT"
      ) {
        const payload = body(init);
        puts.push(payload);
        const updated = group({ ...payload, quantity: payload.quantity });
        groups = [updated];
        return json(updated);
      }
      if (path === "/api/v1/plants" && (!init?.method || init.method === "GET"))
        return json(plants);
      if (
        path === "/api/v1/plant-groups" &&
        (!init?.method || init.method === "GET")
      )
        return json(groups);
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: /Avocado #1/ }));
  await user.click(await screen.findByRole("button", { name: "Edit Plant" }));
  const label = screen.getByLabelText("Label (optional)");
  await user.clear(label);
  await user.type(label, "Corrected plant");
  await user.selectOptions(
    screen.getByLabelText("Current location (optional)"),
    "",
  );
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("could not save");
  expect(label).toHaveValue("Corrected plant");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(
    await screen.findByText("Plant changes were saved."),
  ).toBeInTheDocument();

  await user.click(
    within(screen.getByRole("group", { name: "Lifecycle" })).getByRole(
      "button",
      { name: "History" },
    ),
  );
  await user.click(screen.getByRole("button", { name: /Seedlings 2026/ }));
  await user.click(
    await screen.findByRole("button", { name: "Edit Plant group" }),
  );
  await user.selectOptions(screen.getByLabelText("Kind"), "exact");
  await user.clear(screen.getByLabelText("Count"));
  await user.type(screen.getByLabelText("Count"), "8");
  await user.selectOptions(screen.getByLabelText("Lifecycle"), "active");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(
    await screen.findByText("Plant group changes were saved."),
  ).toBeInTheDocument();
  expect(puts.at(-1)).toMatchObject({
    lifecycle: "active",
    quantity: { value: 8, is_approximate: false },
  });
});

test("detail loading, detail failure, authorization, and session expiry are explicit", async () => {
  mockApi(
    plantHandler([plant()], [], (path) =>
      path === `/api/v1/plants/${plantId}`
        ? json({ detail: "failed" }, 500)
        : undefined,
    ),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: /Avocado #1/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not load this record",
  );
  expect(
    screen.getByRole("button", { name: "Retry detail" }),
  ).toBeInTheDocument();

  cleanup();
  vi.restoreAllMocks();
  mockApi(
    plantHandler([], [], (path, init) =>
      path === "/api/v1/plants" && init?.method === "POST"
        ? json({ detail: "forbidden" }, 403)
        : undefined,
    ),
  );
  const forbiddenUser = await openPlants();
  await forbiddenUser.click(
    await screen.findByRole("button", { name: "+ New" }),
  );
  await forbiddenUser.click(
    screen.getByRole("button", { name: /Plant.*One individually/s }),
  );
  await chooseReference(
    forbiddenUser,
    "Botanical identity",
    "Persea americana",
  );
  await forbiddenUser.click(
    screen.getByRole("button", { name: "Record Plant" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not authorize",
  );

  cleanup();
  vi.restoreAllMocks();
  mockApi(
    plantHandler([], [], (path) =>
      path === "/api/v1/plants"
        ? json({ detail: "Authentication required" }, 401)
        : undefined,
    ),
  );
  await openPlants();
  expect(
    await screen.findByText("Your session expired. Sign in again to continue."),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
});

test("active group extraction is focused, updates exact quantity, opens the Plant, and keeps origin read-only", async () => {
  const activeGroup = group({
    lifecycle: "active",
    quantity: { value: 1, is_approximate: false },
    location_id: locationId,
    location: { id: locationId, display_path: location.display_path },
  });
  let plants: unknown[] = [];
  let groups: unknown[] = [activeGroup];
  let extractionPayload: Record<string, unknown> | undefined;
  mockApi(
    plantHandler(plants, groups, (path, init) => {
      if (
        path === `/api/v1/plant-groups/${groupId}/extract-plant` &&
        init?.method === "POST"
      ) {
        extractionPayload = body(init);
        const completedGroup = group({
          lifecycle: "completed",
          quantity: { value: 0, is_approximate: false },
        });
        const extracted = plant({
          id: "extracted-plant",
          botanical_identity_id: identityId,
          botanical_identity: {
            id: identityId,
            display_label: "Persea americana",
          },
          label: extractionPayload.label,
          location_id: extractionPayload.location_id,
          location: null,
          originating_plant_group_id: groupId,
          originating_plant_group: {
            id: groupId,
            label: "Seedlings 2026",
            lifecycle: "completed",
            botanical_identity: {
              id: otherIdentityId,
              display_label: "Cyphomandra betacea",
            },
            quantity: { value: 0, is_approximate: false },
          },
          direct_origin_kind: null,
          supplier_id: null,
          supplier: null,
          material_provenance_place_id: null,
          material_provenance: null,
        });
        plants = [extracted];
        groups = [completedGroup];
        return json({ plant: extracted, plant_group: completedGroup }, 201);
      }
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(
    await screen.findByRole("button", { name: /Seedlings 2026/ }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Extract plant" }),
  );
  expect(screen.getByRole("heading", { name: "Extract plant" })).toHaveFocus();
  expect(screen.getByText(/last exact member/)).toBeInTheDocument();
  expect(screen.queryByLabelText("Lifecycle")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Direct origin")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Originating Sowing")).not.toBeInTheDocument();
  expect(
    screen.getByRole("combobox", { name: "Botanical identity" }),
  ).toHaveValue("Cyphomandra betacea");
  expect(screen.getByLabelText("Current location (optional)")).toHaveValue(
    locationId,
  );
  const extractionIdentity = screen.getByRole("combobox", {
    name: "Botanical identity",
  });
  await user.clear(extractionIdentity);
  await user.type(extractionIdentity, "Persea");
  await user.click(screen.getByRole("button", { name: "Persea americana" }));
  await user.selectOptions(
    screen.getByLabelText("Current location (optional)"),
    "",
  );
  await user.type(screen.getByLabelText("Label (optional)"), "Chosen one");
  await user.selectOptions(screen.getByLabelText("Precision"), "day");
  await user.clear(screen.getByLabelText("Year"));
  await user.type(screen.getByLabelText("Year"), "2026");
  await user.clear(screen.getByLabelText("Month"));
  await user.type(screen.getByLabelText("Month"), "9");
  await user.clear(screen.getByLabelText("Day"));
  await user.type(screen.getByLabelText("Day"), "1");
  await user.type(
    screen.getByLabelText("Notes (optional)"),
    "Chosen for vigor.",
  );
  await user.click(screen.getByRole("button", { name: "Extract plant" }));
  expect(extractionPayload).toMatchObject({
    botanical_identity_id: identityId,
    location_id: null,
    label: "Chosen one",
    collection_entry_date: {
      precision: "day",
      year: 2026,
      month: 9,
      day: 1,
    },
    notes: "Chosen for vigor.",
  });
  expect(
    await screen.findByText("Plant was extracted from the group."),
  ).toBeInTheDocument();
  expect(screen.getByText("Extracted from group")).toBeInTheDocument();
  expect(screen.getByText("Seedlings 2026")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Edit Plant" }));
  expect(screen.getByText(/Origin is read-only/)).toBeInTheDocument();
  expect(screen.queryByLabelText("Direct origin")).not.toBeInTheDocument();
});

test("group extraction availability and quantity explanations cover inactive, exact, approximate, and unknown states", async () => {
  const scenarios = [
    {
      record: group({ lifecycle: "completed" }),
      explanation: "Plants can only be extracted from an active group.",
      actionable: false,
    },
    {
      record: group({
        lifecycle: "active",
        quantity: { value: 5, is_approximate: false },
      }),
      explanation: "Group count: 5 → 4",
      actionable: true,
    },
    {
      record: group({
        lifecycle: "active",
        quantity: { value: 5, is_approximate: true },
      }),
      explanation: "Approximate group quantity will remain unchanged.",
      actionable: true,
    },
    {
      record: group({ lifecycle: "active", quantity: null }),
      explanation: "Group quantity is unknown and will remain unknown.",
      actionable: true,
    },
  ];

  for (const scenario of scenarios) {
    mockApi(plantHandler([], [scenario.record]));
    const user = await openPlants();
    if (!scenario.actionable) {
      await user.click(
        within(screen.getByRole("group", { name: "Lifecycle" })).getByRole(
          "button",
          { name: "History" },
        ),
      );
    }
    await user.click(
      await screen.findByRole("button", { name: /Seedlings 2026/ }),
    );
    if (scenario.actionable) {
      const action = await screen.findByRole("button", {
        name: "Extract plant",
      });
      await user.click(action);
    } else {
      expect(
        screen.queryByRole("button", { name: "Extract plant" }),
      ).not.toBeInTheDocument();
    }
    expect(await screen.findByText(scenario.explanation)).toBeInTheDocument();
    cleanup();
    vi.restoreAllMocks();
  }
});

test("extraction conflict preserves the form, refreshes the group, and does not add a Plant", async () => {
  let currentGroup = group({
    lifecycle: "active",
    quantity: { value: 1, is_approximate: false },
  });
  let postCount = 0;
  mockApi(
    plantHandler([], [currentGroup], (path, init) => {
      if (
        path === `/api/v1/plant-groups/${groupId}/extract-plant` &&
        init?.method === "POST"
      ) {
        postCount += 1;
        currentGroup = group({
          lifecycle: "completed",
          quantity: { value: 0, is_approximate: false },
        });
        return json({ detail: { code: "plant_group_not_active" } }, 409);
      }
      if (
        path === `/api/v1/plant-groups/${groupId}` &&
        (!init?.method || init.method === "GET")
      )
        return json(currentGroup);
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(
    await screen.findByRole("button", { name: /Seedlings 2026/ }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Extract plant" }),
  );
  const label = screen.getByLabelText("Label (optional)");
  await user.type(label, "Keep this value");
  await user.click(screen.getByRole("button", { name: "Extract plant" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "current state has been refreshed",
  );
  expect(label).toHaveValue("Keep this value");
  expect(screen.getByText(/no longer active/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Extract plant" })).toBeDisabled();
  expect(postCount).toBe(1);
  expect(
    screen.queryByText("Plant was extracted from the group."),
  ).not.toBeInTheDocument();
});

test("source PlantGroup context is searchable for extracted Plants", async () => {
  const extracted = plant({
    originating_plant_group_id: groupId,
    originating_plant_group: {
      id: groupId,
      label: "Tamarillo extraction source",
      lifecycle: "active",
      botanical_identity: {
        id: otherIdentityId,
        display_label: "Cyphomandra betacea",
      },
      quantity: null,
    },
    direct_origin_kind: null,
    supplier_id: null,
    supplier: null,
    material_provenance_place_id: null,
    material_provenance: null,
  });
  mockApi(plantHandler([extracted], []));
  const user = await openPlants();
  await user.type(
    await screen.findByRole("searchbox", { name: "Search Plants" }),
    "Tamarillo extraction source",
  );
  const result = screen.getByRole("button", { name: /Avocado #1/ });
  expect(result).toHaveTextContent(
    "Extracted from group · Tamarillo extraction source",
  );
  await user.clear(screen.getByRole("searchbox", { name: "Search Plants" }));
  await user.type(
    screen.getByRole("searchbox", { name: "Search Plants" }),
    "Cyphomandra betacea",
  );
  expect(
    screen.getByRole("button", { name: /Avocado #1/ }),
  ).toBeInTheDocument();
});

test("Plant Event history preserves API order, every label and partial-date precision while filters stay predictable", async () => {
  const events = Object.keys(eventKinds).map((kind, index) =>
    journalEvent(kind, {
      occurred_on:
        index === 0
          ? { precision: "year", year: 2024 }
          : index === 1
            ? { precision: "month", year: 2025, month: 3 }
            : index === 2
              ? { precision: "day", year: 2026, month: 9, day: 2 }
              : null,
      notes:
        kind === "observation"
          ? "A long observation that must remain readable."
          : null,
      destination_location:
        kind === "movement"
          ? { id: locationId, display_path: location.display_path }
          : null,
      destination_location_id: kind === "movement" ? locationId : null,
    }),
  );
  mockApi(
    plantHandler([plant()], [], (path) =>
      path === `/api/v1/plants/${plantId}/events` ? json(events) : undefined,
    ),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: /Avocado #1/ }));
  const timeline = await screen.findByRole("list", { name: "Event history" });
  const items = within(timeline).getAllByRole("listitem");
  expect(items).toHaveLength(12);
  expect(
    items.map((item) => within(item).getByRole("heading").textContent),
  ).toEqual(Object.values(eventKinds));
  expect(items[0]).toHaveTextContent("2024");
  expect(items[1]).toHaveTextContent("2025-03");
  expect(items[2]).toHaveTextContent("2026-09-02");
  expect(items[3]).toHaveTextContent("Date unknown");
  expect(items[1]).toHaveTextContent("Destination: Greenhouse → Bench 4");
  expect(items[0].querySelector(".event-card")).toBeInTheDocument();
  expect(timeline).toHaveClass("event-timeline");

  const filters = screen.getByRole("group", { name: "Filter Events" });
  await user.click(
    within(filters).getByRole("button", { name: "Observations" }),
  );
  expect(within(timeline).getAllByRole("listitem")).toHaveLength(3);
  expect(within(timeline).queryByText("Other")).not.toBeInTheDocument();
  await user.click(
    within(filters).getByRole("button", { name: "Cultivation" }),
  );
  expect(within(timeline).getAllByRole("listitem")).toHaveLength(5);
  await user.click(within(filters).getByRole("button", { name: "Status" }));
  expect(within(timeline).getAllByRole("listitem")).toHaveLength(3);
  await user.click(within(filters).getByRole("button", { name: "All" }));
  expect(within(timeline).getAllByRole("listitem")).toHaveLength(12);
});

test("PlantGroup detail has the same responsive Event journal and a useful empty state", async () => {
  let groupEvents: unknown[] = [];
  mockApi(
    plantHandler([], [group()], (path) =>
      path === `/api/v1/plant-groups/${groupId}/events`
        ? json(groupEvents)
        : undefined,
    ),
  );
  const user = await openPlants();
  await user.click(
    within(screen.getByRole("group", { name: "Lifecycle" })).getByRole(
      "button",
      { name: "History" },
    ),
  );
  await user.click(
    await screen.findByRole("button", { name: /Seedlings 2026/ }),
  );
  expect(
    await screen.findByRole("heading", { name: "No Events recorded yet" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/observations, cultivation work/),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Add the first event" }),
  ).toBeInTheDocument();

  cleanup();
  vi.restoreAllMocks();
  groupEvents = [
    journalEvent("flowering", {
      target: {
        type: "plant_group",
        id: groupId,
        label: "Seedlings 2026",
        lifecycle: "completed",
      },
      notes: "First group bloom.",
    }),
  ];
  mockApi(
    plantHandler([], [group()], (path) =>
      path === `/api/v1/plant-groups/${groupId}/events`
        ? json(groupEvents)
        : undefined,
    ),
  );
  const parityUser = await openPlants();
  await parityUser.click(
    within(screen.getByRole("group", { name: "Lifecycle" })).getByRole(
      "button",
      { name: "History" },
    ),
  );
  await parityUser.click(
    await screen.findByRole("button", { name: /Seedlings 2026/ }),
  );
  expect(
    await screen.findByRole("heading", { name: "Flowering" }),
  ).toBeInTheDocument();
  expect(screen.getByText("First group bloom.")).toBeInTheDocument();
});

test("Event creation validates movement, explains side effects and authoritatively refreshes Plant state", async () => {
  const events: Record<string, unknown>[] = [];
  const plants = [plant({ location_id: null, location: null })];
  let targetReads = 0;
  mockApi(
    plantHandler(plants, [], (path, init) => {
      if (path === `/api/v1/plants/${plantId}/events`) {
        if (init?.method === "POST") {
          const payload = body(init);
          const created = journalEvent(String(payload.kind), {
            ...payload,
            id: `${eventId}-${String(events.length)}`,
            destination_location:
              payload.kind === "movement"
                ? { id: locationId, display_path: location.display_path }
                : null,
          });
          events.push(created);
          if (payload.kind === "movement")
            plants[0] = plant({
              location_id: locationId,
              location: { id: locationId, display_path: location.display_path },
            });
          if (["death", "loss", "discarded"].includes(String(payload.kind)))
            plants[0] = plant({
              ...plants[0],
              lifecycle: payload.kind === "death" ? "dead" : payload.kind,
            });
          return json(created, 201);
        }
        return json(events);
      }
      if (
        path === `/api/v1/plants/${plantId}` &&
        (!init?.method || init.method === "GET")
      ) {
        targetReads += 1;
        return json(plants[0]);
      }
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: /Avocado #1/ }));
  await user.click(await screen.findByRole("button", { name: "Add event" }));
  await user.type(screen.getByLabelText("Notes (optional)"), "New leaf.");
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add event",
    }),
  );
  expect(await screen.findByText("Event was added.")).toBeInTheDocument();
  expect(screen.getByText("New leaf.")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Add event" }));
  await user.selectOptions(screen.getByLabelText("Event kind"), "movement");
  expect(
    screen.getByText(/also changes the current Location/),
  ).toBeInTheDocument();
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add event",
    }),
  );
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Choose the destination Location",
  );
  await user.selectOptions(
    screen.getByLabelText("Destination Location"),
    locationId,
  );
  await user.selectOptions(screen.getByLabelText("Precision"), "month");
  await user.clear(screen.getByLabelText("Year"));
  await user.type(screen.getByLabelText("Year"), "2026");
  await user.clear(screen.getByLabelText("Month"));
  await user.type(screen.getByLabelText("Month"), "8");
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add event",
    }),
  );
  expect(await screen.findByText("2026-08")).toBeInTheDocument();
  expect(screen.getAllByText(location.display_path).length).toBeGreaterThan(0);

  await user.click(screen.getByRole("button", { name: "Add event" }));
  for (const kind of ["death", "loss", "discarded"]) {
    await user.selectOptions(screen.getByLabelText("Event kind"), kind);
    expect(
      screen.getByText(/also changes the current lifecycle/),
    ).toHaveTextContent(kind);
  }
  await user.selectOptions(screen.getByLabelText("Event kind"), "death");
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add event",
    }),
  );
  expect(await screen.findByText("Dead")).toBeInTheDocument();
  expect(targetReads).toBeGreaterThanOrEqual(4);
});

test("historical edit and delete warn and never synthesize target rollback", async () => {
  let events = [
    journalEvent("movement", {
      destination_location_id: locationId,
      destination_location: {
        id: locationId,
        display_path: location.display_path,
      },
      notes: "Moved for winter.",
    }),
  ];
  let targetReads = 0;
  mockApi(
    plantHandler([plant()], [], (path, init) => {
      if (path === `/api/v1/plants/${plantId}/events`) return json(events);
      if (
        path === `/api/v1/events/${events[0]?.id}` &&
        init?.method === "PUT"
      ) {
        const payload = body(init);
        events = [
          journalEvent(String(payload.kind), { ...events[0], ...payload }),
        ];
        return json(events[0]);
      }
      if (path.startsWith("/api/v1/events/") && init?.method === "DELETE") {
        events = [];
        return new Response(null, { status: 204 });
      }
      if (
        path === `/api/v1/plants/${plantId}` &&
        (!init?.method || init.method === "GET")
      ) {
        targetReads += 1;
        return json(plant());
      }
      return undefined;
    }),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: /Avocado #1/ }));
  await screen.findByText("Moved for winter.");
  const readsAfterOpen = targetReads;
  await user.click(screen.getByRole("button", { name: "Edit" }));
  expect(screen.getByText(/Editing changes history only/)).toHaveTextContent(
    "does not move the record again",
  );
  await user.selectOptions(screen.getByLabelText("Event kind"), "death");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(
    await screen.findByText("Event changes were saved."),
  ).toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: "Death" }),
  ).toBeInTheDocument();
  expect(targetReads).toBe(readsAfterOpen);

  await user.click(screen.getByRole("button", { name: "Delete" }));
  expect(screen.getByRole("dialog")).toHaveTextContent(
    "does not undo changes previously made",
  );
  await user.click(screen.getByRole("button", { name: "Delete event" }));
  expect(
    await screen.findByRole("heading", { name: "No Events recorded yet" }),
  ).toBeInTheDocument();
  expect(targetReads).toBe(readsAfterOpen);
});

test("Event loading, fetch failure and mutation failure remain explicit", async () => {
  let resolveEvents: ((response: Response) => void) | undefined;
  const pendingEvents = new Promise<Response>((resolve) => {
    resolveEvents = resolve;
  });
  mockApi(
    plantHandler([plant()], [], (path) =>
      path === `/api/v1/plants/${plantId}/events` ? pendingEvents : undefined,
    ),
  );
  const user = await openPlants();
  await user.click(await screen.findByRole("button", { name: /Avocado #1/ }));
  expect(await screen.findByRole("status", { name: "" })).toHaveTextContent(
    "Loading Events",
  );
  resolveEvents?.(json([]));
  expect(
    await screen.findByRole("heading", { name: "No Events recorded yet" }),
  ).toBeInTheDocument();

  cleanup();
  vi.restoreAllMocks();
  mockApi(
    plantHandler([plant()], [], (path) =>
      path === `/api/v1/plants/${plantId}/events`
        ? json({ detail: "failed" }, 500)
        : undefined,
    ),
  );
  const failingUser = await openPlants();
  await failingUser.click(
    await screen.findByRole("button", { name: /Avocado #1/ }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not load this Event history",
  );
  expect(
    screen.getByRole("button", { name: "Retry Events" }),
  ).toBeInTheDocument();

  cleanup();
  vi.restoreAllMocks();
  mockApi(
    plantHandler([plant()], [], (path, init) => {
      if (
        path === `/api/v1/plants/${plantId}/events` &&
        init?.method === "POST"
      )
        return json({ detail: "failed" }, 500);
      if (path === `/api/v1/plants/${plantId}/events`) return json([]);
      return undefined;
    }),
  );
  const mutationUser = await openPlants();
  await mutationUser.click(
    await screen.findByRole("button", { name: /Avocado #1/ }),
  );
  await mutationUser.click(
    await screen.findByRole("button", { name: "Add the first event" }),
  );
  await mutationUser.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add event",
    }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not save or refresh this Event",
  );
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});
