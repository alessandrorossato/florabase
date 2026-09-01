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
  await chooseReference(user, "Botanical identity", "Persea americana");
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
