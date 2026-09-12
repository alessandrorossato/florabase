import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";

const identityId = "01900000-0000-7000-8000-000000000101";
const lotId = "01900000-0000-7000-8000-000000000201";
const sowingId = "01900000-0000-7000-8000-000000000301";
const plantId = "01900000-0000-7000-8000-000000000401";
const groupId = "01900000-0000-7000-8000-000000000501";

const identity = {
  id: identityId,
  scientific_name: "Clitoria ternatea",
  cultivar_name: null,
  common_name: "Butterfly pea",
  display_label: "Clitoria ternatea",
  created_at: "2026-09-04T10:00:00Z",
  updated_at: "2026-09-04T10:00:00Z",
};

function lot(approximate = false, quantity: string | null = "120") {
  return {
    id: lotId,
    botanical_identity_id: identityId,
    botanical_identity: {
      id: identityId,
      display_label: identity.display_label,
    },
    label: "Blue packet",
    source_kind: "purchased",
    source_detail: null,
    supplier_id: null,
    supplier: null,
    material_provenance_place_id: null,
    material_provenance: null,
    acquisition_date: null,
    harvest_date: null,
    quantity:
      quantity === null
        ? null
        : {
            kind: "seed_count",
            value: quantity,
            unit: null,
            is_approximate: approximate,
          },
    expected_viability_until: null,
    location_id: null,
    location: null,
    lifecycle: "active",
    notes: null,
    created_at: "2026-09-04T10:00:00Z",
    updated_at: "2026-09-04T10:00:00Z",
  };
}

const sowing = {
  id: sowingId,
  seed_lot_id: lotId,
  seed_lot: {
    id: lotId,
    label: "Blue packet",
    lifecycle: "active",
    botanical_identity_id: identityId,
    botanical_identity_display_label: identity.display_label,
  },
  label: "Tray A",
  sowing_date: { precision: "day", year: 2026, month: 9, day: 4 },
  quantity: {
    kind: "seed_count",
    value: "20",
    unit: null,
    is_approximate: false,
  },
  germinated_count: 13,
  location_id: null,
  location: null,
  substrate: null,
  method_container: null,
  pretreatment: null,
  temperature_min_c: null,
  temperature_max_c: null,
  environment: null,
  lifecycle: "active",
  notes: null,
  created_at: "2026-09-04T10:00:00Z",
  updated_at: "2026-09-04T10:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installApi(
  handler: (path: string, init?: RequestInit) => Response | undefined,
) {
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
          user_id: "owner",
          login_name: "owner",
          display_name: "Owner",
          owner: true,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(json({ csrf_token: "csrf" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    const response = handler(path, init);
    if (!response)
      throw new Error(`Unhandled request: ${path} ${init?.method ?? "GET"}`);
    return Promise.resolve(response);
  });
}

function requestBody(init?: RequestInit) {
  if (typeof init?.body !== "string") throw new Error("Expected body");
  return JSON.parse(init.body) as Record<string, unknown>;
}

beforeEach(() => {
  window.history.replaceState(null, "", "#/dashboard");
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("guided exact SeedLot usage previews and submits the authoritative partial transition once", async () => {
  let submitted: Record<string, unknown> | null = null;
  let submissions = 0;
  installApi((path, init) => {
    if (path === "/api/v1/seed-lots") return json([lot()]);
    if (path === "/api/v1/locations") return json([]);
    if (
      path === `/api/v1/seed-lots/${lotId}/create-sowing` &&
      init?.method === "POST"
    ) {
      submissions += 1;
      submitted = requestBody(init);
      return json({ sowing, seed_lot: lot(false, "100") }, 201);
    }
    return undefined;
  });
  window.location.hash = `/sowings?action=start&seedLot=${lotId}`;
  const user = userEvent.setup();
  await act(async () => {
    render(<App />);
    await Promise.resolve();
  });
  expect(
    screen.getByRole("heading", { name: "Start sowing" }),
  ).toBeInTheDocument();
  await user.type(screen.getByLabelText("Amount"), "20");
  await user.click(
    screen.getByRole("button", { name: "Continue to SeedLot usage" }),
  );
  expect(screen.getByText(/Subtract → 100 remaining/)).toBeInTheDocument();
  expect(
    screen.getByRole("radio", { name: /Subtract → 100 remaining/ }),
  ).toBeChecked();
  await user.dblClick(screen.getByRole("button", { name: "Create Sowing" }));
  expect(submissions).toBe(1);
  expect(submitted).toMatchObject({
    source_adjustment: { mode: "partial", resulting_quantity: null },
    sowing: {
      quantity: { kind: "seed_count", value: "20", is_approximate: false },
    },
  });
  expect(window.location.hash).toBe(`#/sowings/${sowingId}`);
});

test("exact use-all exhausts the source only when the Sowing amount matches", async () => {
  let submitted: Record<string, unknown> | null = null;
  installApi((path, init) => {
    if (path === "/api/v1/seed-lots") return json([lot()]);
    if (path === "/api/v1/locations") return json([]);
    if (
      path === `/api/v1/seed-lots/${lotId}/create-sowing` &&
      init?.method === "POST"
    ) {
      submitted = requestBody(init);
      return json(
        {
          sowing: { ...sowing, quantity: { ...sowing.quantity, value: "120" } },
          seed_lot: { ...lot(false, "0"), lifecycle: "exhausted" },
        },
        201,
      );
    }
    return undefined;
  });
  window.location.hash = `/sowings?action=start&seedLot=${lotId}`;
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Start sowing" });
  await user.type(screen.getByLabelText("Amount"), "120");
  await user.click(
    screen.getByRole("button", { name: "Continue to SeedLot usage" }),
  );
  const useAll = screen.getByRole("radio", { name: /Use all/ });
  expect(useAll).toBeEnabled();
  await user.click(useAll);
  await user.click(screen.getByRole("button", { name: "Create Sowing" }));
  expect(submitted).toMatchObject({ source_adjustment: { mode: "use_all" } });
});

test("oversubscription is visible, disables arithmetic, and still permits no adjustment", async () => {
  let submitted: Record<string, unknown> | null = null;
  installApi((path, init) => {
    if (path === "/api/v1/seed-lots") return json([lot()]);
    if (path === "/api/v1/locations") return json([]);
    if (
      path === `/api/v1/seed-lots/${lotId}/create-sowing` &&
      init?.method === "POST"
    ) {
      submitted = requestBody(init);
      return json({ sowing, seed_lot: lot() }, 201);
    }
    return undefined;
  });
  window.location.hash = `/sowings?action=start&seedLot=${lotId}`;
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Start sowing" });
  await user.type(screen.getByLabelText("Amount"), "130");
  await user.click(
    screen.getByRole("button", { name: "Continue to SeedLot usage" }),
  );
  expect(screen.getByRole("alert")).toHaveTextContent(
    "exceeds the exact source quantity",
  );
  expect(
    screen.queryByRole("radio", { name: /Subtract/ }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("radio", { name: /Use all/ })).toBeDisabled();
  expect(
    screen.getByRole("radio", { name: /Do not change SeedLot quantity/ }),
  ).toBeChecked();
  await user.click(screen.getByRole("button", { name: "Create Sowing" }));
  expect(submitted).toMatchObject({ source_adjustment: { mode: "none" } });
});

test("BotanicalIdentity contextual SeedLot creation preselects the identity", async () => {
  installApi((path) => {
    if (path === "/api/v1/seed-lots") return json([]);
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (
      path === "/api/v1/suppliers" ||
      path === "/api/v1/locations" ||
      path === "/api/v1/geographic-places" ||
      path === "/api/v1/provenance-sites"
    )
      return json([]);
    return undefined;
  });
  window.location.hash = `/seeds?action=create&identity=${identityId}`;
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Add seed lot" }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Botanical identity")).toHaveValue(
    identity.display_label,
  );
});

test("an approximate source offers an editable approximate remainder", async () => {
  installApi((path) => {
    if (path === "/api/v1/seed-lots") return json([lot(true, "100")]);
    if (path === "/api/v1/locations") return json([]);
    return undefined;
  });
  window.location.hash = `/sowings?action=start&seedLot=${lotId}`;
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Start sowing" });
  await user.type(screen.getByLabelText("Amount"), "20");
  await user.click(
    screen.getByRole("button", { name: "Continue to SeedLot usage" }),
  );
  expect(screen.getByText("Suggested remainder: ~80")).toBeInTheDocument();
  const remainder = screen.getByLabelText("Resulting estimate");
  await user.clear(remainder);
  await user.type(remainder, "75");
  expect(remainder).toHaveValue("75");
  expect(screen.getByText(/remains approximate/)).toBeInTheDocument();
});

test("an approximate source can be explicitly exhausted without inventing exact zero", async () => {
  let submitted: Record<string, unknown> | null = null;
  installApi((path, init) => {
    if (path === "/api/v1/seed-lots") return json([lot(true, "100")]);
    if (path === "/api/v1/locations") return json([]);
    if (
      path === `/api/v1/seed-lots/${lotId}/create-sowing` &&
      init?.method === "POST"
    ) {
      submitted = requestBody(init);
      return json(
        {
          sowing,
          seed_lot: { ...lot(true, "100"), lifecycle: "exhausted" },
        },
        201,
      );
    }
    return undefined;
  });
  window.location.hash = `/sowings?action=start&seedLot=${lotId}`;
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Start sowing" });
  await user.type(screen.getByLabelText("Amount"), "20");
  await user.click(
    screen.getByRole("button", { name: "Continue to SeedLot usage" }),
  );
  await user.click(screen.getByRole("radio", { name: /Use all/ }));
  await user.click(screen.getByRole("button", { name: "Create Sowing" }));
  expect(submitted).toMatchObject({ source_adjustment: { mode: "use_all" } });
});

test("an unknown source remains unknown after partial use", async () => {
  let submitted: Record<string, unknown> | null = null;
  installApi((path, init) => {
    if (path === "/api/v1/seed-lots") return json([lot(false, null)]);
    if (path === "/api/v1/locations") return json([]);
    if (
      path === `/api/v1/seed-lots/${lotId}/create-sowing` &&
      init?.method === "POST"
    ) {
      submitted = requestBody(init);
      return json(
        { sowing: { ...sowing, quantity: null }, seed_lot: lot(false, null) },
        201,
      );
    }
    return undefined;
  });
  window.location.hash = `/sowings?action=start&seedLot=${lotId}`;
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Start sowing" });
  await user.selectOptions(screen.getByLabelText("Kind"), "unknown");
  await user.click(
    screen.getByRole("button", { name: "Continue to SeedLot usage" }),
  );
  expect(
    screen.getByText(
      (_, element) =>
        element?.tagName === "P" &&
        element.textContent === "Current source: Quantity unknown",
    ),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Create Sowing" }));
  expect(submitted).toMatchObject({
    sowing: { quantity: null },
    source_adjustment: { mode: "partial", resulting_quantity: null },
  });
});

test("incompatible units suppress arithmetic and a conflict preserves entered details", async () => {
  installApi((path, init) => {
    if (path === "/api/v1/seed-lots") return json([lot()]);
    if (path === "/api/v1/locations") return json([]);
    if (
      path === `/api/v1/seed-lots/${lotId}/create-sowing` &&
      init?.method === "POST"
    )
      return json({ detail: { code: "seed_lot_changed" } }, 409);
    return undefined;
  });
  window.location.hash = `/sowings?action=start&seedLot=${lotId}`;
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Start sowing" });
  await user.type(screen.getByLabelText("Label (optional)"), "Keep this");
  await user.selectOptions(screen.getByLabelText("Kind"), "weight");
  await user.type(screen.getByLabelText("Amount"), "2");
  await user.click(
    screen.getByRole("button", { name: "Continue to SeedLot usage" }),
  );
  expect(
    screen.queryByRole("radio", { name: /Subtract/ }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("radio", { name: /Use all/ })).toBeDisabled();
  expect(
    screen.getByText(/incompatible dimensions or units/),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("radio", { name: /Do not change SeedLot quantity/ }),
  );
  await user.click(screen.getByRole("button", { name: "Create Sowing" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "source SeedLot changed",
  );
  await user.click(screen.getByRole("button", { name: "Back to details" }));
  expect(screen.getByLabelText("Label (optional)")).toHaveValue("Keep this");
});

test("creating a Plant from a Sowing defaults active and makes completion outcome deliberate", async () => {
  let submitted: Record<string, unknown> | null = null;
  installApi((path, init) => {
    if (path === `/api/v1/sowings/${sowingId}`) return json(sowing);
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === "/api/v1/locations") return json([]);
    if (
      path === `/api/v1/sowings/${sowingId}/create-plant` &&
      init?.method === "POST"
    ) {
      submitted = requestBody(init);
      return json(
        {
          plant: { id: plantId },
          sowing: { ...sowing, lifecycle: "completed" },
        },
        201,
      );
    }
    return undefined;
  });
  window.location.hash = `/plants?action=from-sowing&sowing=${sowingId}&kind=plant`;
  const user = userEvent.setup();
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Create Plant" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("radio", { name: /Keep active/ })).toBeChecked();
  await user.click(screen.getByRole("radio", { name: /Complete Sowing/ }));
  expect(screen.getByText("Not germinated")).toBeInTheDocument();
  expect(screen.getByText("7")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Create Plant" }));
  expect(submitted).toMatchObject({
    resulting_sowing_lifecycle: "completed",
    plant: { botanical_identity_id: identityId },
  });
  expect(window.location.hash).toBe(`#/plants/${plantId}`);
});

test.each([
  [
    "approximate",
    {
      kind: "seed_count",
      value: "20",
      unit: null,
      is_approximate: true,
    },
    /approximate quantity/,
  ],
  ["unknown", null, /unknown quantity/],
  [
    "weight-based",
    { kind: "weight", value: "2", unit: "g", is_approximate: false },
    /recorded weight/,
  ],
])(
  "%s Sowing completion does not fabricate a not-germinated remainder",
  async (_case, quantity, expectedExplanation) => {
    const uncertainSowing = { ...sowing, quantity };
    installApi((path) => {
      if (path === `/api/v1/sowings/${sowingId}`) return json(uncertainSowing);
      if (path === "/api/v1/botanical-identities") return json([identity]);
      if (path === "/api/v1/locations") return json([]);
      return undefined;
    });
    window.location.hash = `/plants?action=from-sowing&sowing=${sowingId}&kind=plant`;
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Create Plant" });
    await user.click(screen.getByRole("radio", { name: /Complete Sowing/ }));
    expect(screen.getByText(expectedExplanation)).toBeInTheDocument();
    expect(screen.queryByText("Not germinated")).not.toBeInTheDocument();
  },
);

test("creating an approximate Plant group preserves uncertainty and the chosen lifecycle", async () => {
  let submitted: Record<string, unknown> | null = null;
  installApi((path, init) => {
    if (path === `/api/v1/sowings/${sowingId}`) return json(sowing);
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === "/api/v1/locations") return json([]);
    if (
      path === `/api/v1/sowings/${sowingId}/create-plant-group` &&
      init?.method === "POST"
    ) {
      submitted = requestBody(init);
      return json(
        {
          plant_group: { id: groupId },
          sowing: { ...sowing, lifecycle: "failed" },
        },
        201,
      );
    }
    return undefined;
  });
  window.location.hash = `/plants?action=from-sowing&sowing=${sowingId}&kind=group`;
  const user = userEvent.setup();
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Create Plant group" }),
  ).toBeInTheDocument();
  await user.selectOptions(
    screen.getAllByLabelText("Precision")[1],
    "approximate",
  );
  await user.type(screen.getByLabelText("Individuals"), "8");
  await user.click(screen.getByRole("radio", { name: /Mark failed/ }));
  await user.click(screen.getByRole("button", { name: "Create Plant group" }));
  expect(submitted).toMatchObject({
    resulting_sowing_lifecycle: "failed",
    plant_group: {
      botanical_identity_id: identityId,
      quantity: { value: 8, is_approximate: true },
    },
  });
  expect(window.location.hash).toBe(`#/plant-groups/${groupId}`);
});

test("Sowing detail consumes the stored propagation summary without converting uncertain groups", async () => {
  installApi((path) => {
    if (path === "/api/v1/sowings") return json([sowing]);
    if (path === `/api/v1/sowings/${sowingId}`) return json(sowing);
    if (path === `/api/v1/sowings/${sowingId}/propagation-summary`)
      return json({
        sowing_id: sowingId,
        lifecycle: "active",
        germinated_count: 13,
        plants: [
          {
            id: plantId,
            botanical_identity_id: identityId,
            label: "Plant A",
            lifecycle: "active",
          },
        ],
        plant_groups: [
          {
            id: "group",
            botanical_identity_id: identityId,
            label: "Community pot",
            lifecycle: "active",
            quantity: { value: 8, is_approximate: true },
          },
        ],
        exact_descendant_count: 1,
        approximate_plant_group_count: 1,
        unknown_plant_group_count: 0,
      });
    if (path === "/api/v1/seed-lots") return json([lot()]);
    if (path === "/api/v1/locations") return json([]);
    return undefined;
  });
  window.location.hash = `/sowings/${sowingId}`;
  render(<App />);
  expect(await screen.findByText("1 exact individual")).toBeInTheDocument();
  expect(screen.getByText("+ 1 approximate Plant group")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Plant A/ })).toHaveAttribute(
    "href",
    `#/plants/${plantId}`,
  );
  expect(screen.getByRole("link", { name: "Create Plant" })).toHaveAttribute(
    "href",
    `#/plants?action=from-sowing&sowing=${sowingId}&kind=plant`,
  );
});
