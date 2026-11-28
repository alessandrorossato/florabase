import type { ReactElement } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import type { BotanicalIdentityResponse } from "../botanical-identities/api";
import type { LocationResponse } from "../locations/api";
import type { PlantGroupResponse, PlantResponse } from "../plants/api";
import type { SowingResponse } from "../sowings/api";
import { acquireTestAuth } from "../test/auth";
import { expandLabelPattern, previewLabelSample } from "./api";
import { PotOnDialog, PotOnLauncher } from "./PotOnDialog";

let auth: AuthContextValue;

function renderWithAuth(ui: ReactElement) {
  return render(<AuthContext.Provider value={auth}>{ui}</AuthContext.Provider>);
}

beforeEach(async () => {
  auth = (await acquireTestAuth({ csrfToken: "csrf-token" })).auth;
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const identity: BotanicalIdentityResponse = {
  id: "id-1",
  scientific_name: "Hoya carnosa",
  cultivar_name: null,
  common_name: "Wax plant",
  display_label: "Hoya carnosa",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const zeroCount = { active: 0, total: 0 };

const plantLocation: LocationResponse = {
  id: "loc-1",
  name: "Bench 2",
  parent_id: null,
  display_path: "Greenhouse → Bench 2",
  usage_scopes: ["plants", "sowings"],
  retired_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  usage: { plants: zeroCount, sowings: zeroCount, seed_lots: zeroCount },
  direct_usage: {
    plants: zeroCount,
    plant_groups: zeroCount,
    sowings: zeroCount,
    seed_lots: zeroCount,
    harvest_inventory: zeroCount,
  },
  usage_including_descendants: {
    plants: zeroCount,
    plant_groups: zeroCount,
    sowings: zeroCount,
    seed_lots: zeroCount,
    harvest_inventory: zeroCount,
  },
};

const sowingOnlyLocation: LocationResponse = {
  ...plantLocation,
  id: "loc-sow-only",
  name: "Heat mat",
  display_path: "Heat mat",
  usage_scopes: ["sowings"],
};

const baseSowing: SowingResponse = {
  id: "sowing-1",
  seed_lot_id: "lot-1",
  seed_lot: {
    id: "lot-1",
    label: "HOY-24-07",
    lifecycle: "active",
    botanical_identity_id: identity.id,
    botanical_identity_display_label: identity.display_label,
  },
  label: "HOY-24-07",
  sowing_date: { precision: "day", year: 2026, month: 7, day: 1 },
  quantity: {
    kind: "seed_count",
    value: "20",
    unit: null,
    is_approximate: false,
  },
  germinated_count: 12,
  location_id: plantLocation.id,
  location: { id: plantLocation.id, display_path: plantLocation.display_path },
  substrate: null,
  method_container: null,
  pretreatment: null,
  temperature_min_c: null,
  temperature_max_c: null,
  environment: null,
  lifecycle: "active",
  notes: null,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-11-24T10:00:00Z",
};

const baseGroup: PlantGroupResponse = {
  id: "group-1",
  primary_photo: null,
  botanical_identity_id: identity.id,
  botanical_identity: {
    id: identity.id,
    display_label: identity.display_label,
  },
  originating_sowing_id: null,
  originating_propagation_attempt_id: null,
  originating_sowing: null,
  direct_origin_kind: "purchased",
  direct_origin_detail: null,
  supplier_id: null,
  supplier: null,
  material_provenance_place_id: null,
  material_provenance: null,
  provenance_site_id: null,
  provenance_site: null,
  label: "HOY-GRP",
  collection_entry_date: null,
  location_id: plantLocation.id,
  location: { id: plantLocation.id, display_path: plantLocation.display_path },
  notes: null,
  quantity: { value: 20, is_approximate: false },
  lifecycle: "active",
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-11-24T10:00:00Z",
};

function makePlant(id: string, label: string): PlantResponse {
  return {
    id,
    primary_photo: null,
    botanical_identity_id: identity.id,
    botanical_identity: {
      id: identity.id,
      display_label: identity.display_label,
    },
    originating_sowing_id: baseSowing.id,
    originating_propagation_attempt_id: null,
    originating_sowing: null,
    originating_plant_group_id: null,
    originating_plant_group: null,
    direct_origin_kind: null,
    direct_origin_detail: null,
    supplier_id: null,
    supplier: null,
    material_provenance_place_id: null,
    material_provenance: null,
    provenance_site_id: null,
    provenance_site: null,
    label,
    collection_entry_date: { precision: "day", year: 2026, month: 11, day: 24 },
    location_id: plantLocation.id,
    location: {
      id: plantLocation.id,
      display_path: plantLocation.display_path,
    },
    notes: null,
    lifecycle: "active",
    created_at: "2026-11-24T10:01:00Z",
    updated_at: "2026-11-24T10:01:00Z",
  };
}

function requestPath(input: RequestInfo | URL): string {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.toString()
      : input.url;
}

function requestBody(init?: RequestInit): Record<string, unknown> {
  return JSON.parse(
    typeof init?.body === "string" ? init.body : "{}",
  ) as Record<string, unknown>;
}

describe("label pattern helpers", () => {
  test("expands counter with auto padding, previews first 3 and last, warns without {n}", () => {
    const expanded = expandLabelPattern("HOY-24-07-{n}", 12);
    expect(expanded.error).toBeUndefined();
    expect(expanded.duplicateWarning).toBe(false);
    expect(expanded.labels[0]).toBe("HOY-24-07-01");
    expect(expanded.labels[11]).toBe("HOY-24-07-12");

    const sample = previewLabelSample(expanded.labels);
    expect(sample.head).toEqual([
      "HOY-24-07-01",
      "HOY-24-07-02",
      "HOY-24-07-03",
    ]);
    expect(sample.tail).toBe("HOY-24-07-12");
    expect(sample.omitted).toBe(8);

    const dup = expandLabelPattern("HOY-24-07", 3);
    expect(dup.duplicateWarning).toBe(true);
    expect(dup.labels).toEqual(["HOY-24-07", "HOY-24-07", "HOY-24-07"]);

    const overflow = expandLabelPattern(`${"x".repeat(253)}{n}`, 1, 1, 3);
    expect(overflow.error).toMatch(/255/);
  });
});

describe("PotOnDialog", () => {
  test("sowing pot-on shows live preview, smart lifecycle default, preview sentence, and created links", async () => {
    const user = userEvent.setup();
    const posts: { path: string; body: Record<string, unknown> }[] = [];
    const createdPlants = Array.from({ length: 12 }, (_, idx) =>
      makePlant(
        `plant-${String(idx + 1)}`,
        `HOY-24-07-${String(idx + 1).padStart(2, "0")}`,
      ),
    );
    const updatedSowing: SowingResponse = {
      ...baseSowing,
      lifecycle: "completed",
      updated_at: "2026-11-24T10:05:00Z",
    };

    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const path = requestPath(input);
      if (
        init?.method === "POST" &&
        path === "/api/v1/sowings/sowing-1/pot-on"
      ) {
        posts.push({ path, body: requestBody(init) });
        return Promise.resolve(
          new Response(
            JSON.stringify({ sowing: updatedSowing, plants: createdPlants }),
            { status: 201, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      throw new Error(`Unexpected fetch: ${path}`);
    });

    const onSowingUpdated = vi.fn();
    renderWithAuth(
      <PotOnLauncher
        source={{ kind: "sowing", sowing: baseSowing }}
        identities={[identity]}
        locations={[plantLocation, sowingOnlyLocation]}
        onSowingUpdated={onSowingUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Pot on seedlings…" }));

    // Count defaults to germinated_count=12, sowing afterwards defaults to Completed,
    // and live preview shows first 3 + last.
    expect(screen.getByLabelText(/Number of seedlings/i)).toHaveValue(12);
    expect(
      screen.getByRole("radio", { name: "Complete Sowing" }),
    ).toBeChecked();
    expect(
      screen.getByText(
        "HOY-24-07-01, HOY-24-07-02, HOY-24-07-03, …, HOY-24-07-12",
      ),
    ).toBeInTheDocument();

    // Lowering count below germinated flips smart default to Keep active, then back to 12 flips to Completed.
    const countField = screen.getByLabelText(/Number of seedlings/i);
    await user.clear(countField);
    await user.type(countField, "5");
    expect(screen.getByRole("radio", { name: "Keep active" })).toBeChecked();
    await user.clear(countField);
    await user.type(countField, "12");
    expect(
      screen.getByRole("radio", { name: "Complete Sowing" }),
    ).toBeChecked();

    await user.click(screen.getByRole("button", { name: "Review & confirm" }));
    expect(
      screen.getByText(
        "Will create 12 Plants HOY-24-07-01 … HOY-24-07-12 in Greenhouse → Bench 2; sowing becomes Completed.",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm pot-on" }));

    await waitFor(() => {
      expect(
        screen.getByText("Created 12 Plants; Sowing is now Completed."),
      ).toBeInTheDocument();
    });
    expect(onSowingUpdated).toHaveBeenCalledWith(updatedSowing);
    expect(posts).toHaveLength(1);
    expect(posts[0]?.body).toMatchObject({
      count: 12,
      label_pattern: "HOY-24-07-{n}",
      botanical_identity_id: identity.id,
      location_id: plantLocation.id,
      resulting_sowing_lifecycle: "completed",
      expected_sowing_updated_at: baseSowing.updated_at,
    });
    expect(screen.getByRole("link", { name: "HOY-24-07-01" })).toHaveAttribute(
      "href",
      "#/plants/plant-1",
    );
    expect(screen.getByRole("link", { name: "HOY-24-07-12" })).toHaveAttribute(
      "href",
      "#/plants/plant-12",
    );
  });

  test("sowing group mode calls create-plant-group and warns when pattern omits {n}", async () => {
    const user = userEvent.setup();
    const posts: { path: string; body: Record<string, unknown> }[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const path = requestPath(input);
      if (
        init?.method === "POST" &&
        path === "/api/v1/sowings/sowing-1/create-plant-group"
      ) {
        posts.push({ path, body: requestBody(init) });
        return Promise.resolve(
          new Response(
            JSON.stringify({
              sowing: { ...baseSowing, lifecycle: "completed" },
              plant_group: {
                ...baseGroup,
                id: "created-grp",
                label: "HOY-24-07",
              },
            }),
            { status: 201, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      throw new Error(`Unexpected fetch: ${path}`);
    });

    renderWithAuth(
      <PotOnDialog
        source={{ kind: "sowing", sowing: baseSowing }}
        identities={[identity]}
        locations={[plantLocation]}
        onClose={vi.fn()}
      />,
    );

    const patternInput = screen.getByLabelText("Label pattern");
    await user.clear(patternInput);
    await user.type(patternInput, "SAME-LABEL");
    expect(
      screen.getByText(/all 12 plants will receive the same label/i),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("radio", { name: "One Plant group of N" }),
    );
    await user.click(screen.getByRole("button", { name: "Review & confirm" }));
    expect(
      screen.getByText(
        "Will create 1 Plant group of 12 HOY-24-07 in Greenhouse → Bench 2; sowing becomes Completed.",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm pot-on" }));
    await waitFor(() => {
      expect(
        screen.getByRole("link", { name: "Open HOY-24-07" }),
      ).toHaveAttribute("href", "#/plant-groups/created-grp");
    });
    expect(posts[0]?.body).toMatchObject({
      plant_group: {
        botanical_identity_id: identity.id,
        quantity: { value: 12, is_approximate: false },
      },
      resulting_sowing_lifecycle: "completed",
    });
  });

  test("handles 409 stale_preview with Refresh action and loading/error states", async () => {
    const user = userEvent.setup();
    const refreshedSowing: SowingResponse = {
      ...baseSowing,
      updated_at: "2026-11-24T10:09:00Z",
    };

    let refFetchFailedOnce = false;
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const path = requestPath(input);
      if (path === "/api/v1/botanical-identities") {
        if (!refFetchFailedOnce) {
          refFetchFailedOnce = true;
          return Promise.resolve(new Response("error", { status: 500 }));
        }
        return Promise.resolve(
          new Response(JSON.stringify([identity]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (path === "/api/v1/locations") {
        return Promise.resolve(
          new Response(JSON.stringify([plantLocation]), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (
        init?.method === "POST" &&
        path === "/api/v1/sowings/sowing-1/pot-on"
      ) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              detail: { code: "stale_preview", message: "Stale sowing" },
            }),
            { status: 409, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      if (path === "/api/v1/sowings/sowing-1") {
        return Promise.resolve(
          new Response(JSON.stringify(refreshedSowing), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      throw new Error(`Unexpected fetch: ${path}`);
    });

    const onSowingUpdated = vi.fn();
    renderWithAuth(
      <PotOnDialog
        source={{ kind: "sowing", sowing: baseSowing }}
        onClose={vi.fn()}
        onSowingUpdated={onSowingUpdated}
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/could not load botanical identities and locations/i),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => {
      expect(screen.getByLabelText(/Number of seedlings/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Review & confirm" }));
    await user.click(screen.getByRole("button", { name: "Confirm pot-on" }));

    await waitFor(() => {
      expect(
        screen.getByText(/This Sowing changed before confirmation/i),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Refresh Sowing" }));
    await waitFor(() => {
      expect(onSowingUpdated).toHaveBeenCalledWith(refreshedSowing);
    });
  });

  test("group split enforces exact max, warns on approximate, and posts extract-batch", async () => {
    const user = userEvent.setup();
    const createdPlants = Array.from({ length: 5 }, (_, idx) =>
      makePlant(`gp-${String(idx + 1)}`, `HOY-GRP-${String(idx + 1)}`),
    );
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const path = requestPath(input);
      if (
        init?.method === "POST" &&
        path === "/api/v1/plant-groups/group-1/extract-batch"
      ) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              plant_group: {
                ...baseGroup,
                quantity: { value: 15, is_approximate: false },
                updated_at: "2026-11-24T10:15:00Z",
              },
              plants: createdPlants,
              event_ids: ["ev-1", "ev-2", "ev-3", "ev-4", "ev-5"],
            }),
            { status: 201, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      throw new Error(`Unexpected fetch: ${path}`);
    });

    const onGroupUpdated = vi.fn();
    renderWithAuth(
      <PotOnDialog
        source={{ kind: "group", group: baseGroup }}
        identities={[identity]}
        locations={[plantLocation]}
        onClose={vi.fn()}
        onGroupUpdated={onGroupUpdated}
      />,
    );

    const countField = screen.getByLabelText(/Number of plants to split/i);
    await user.clear(countField);
    await user.type(countField, "21");
    await user.click(screen.getByRole("button", { name: "Review & confirm" }));
    expect(
      screen.getByText(/cannot exceed the exact group quantity of 20/i),
    ).toBeInTheDocument();

    await user.clear(countField);
    await user.type(countField, "5");
    await user.click(screen.getByRole("button", { name: "Review & confirm" }));
    expect(
      screen.getByText(
        "Will create 5 Plants HOY-GRP-1 … HOY-GRP-5 in Greenhouse → Bench 2; group quantity becomes 15.",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm split" }));
    await waitFor(() => {
      expect(
        screen.getByText(
          "Split 5 Plants from group. Group quantity is now 15.",
        ),
      ).toBeInTheDocument();
    });
    expect(onGroupUpdated).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("link", { name: "HOY-GRP-5" })).toHaveAttribute(
      "href",
      "#/plants/gp-5",
    );

    cleanup();
    renderWithAuth(
      <PotOnDialog
        source={{
          kind: "group",
          group: {
            ...baseGroup,
            quantity: { value: 10, is_approximate: true },
          },
        }}
        identities={[identity]}
        locations={[plantLocation]}
        onClose={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/approximate quantity \(~10\)/i),
    ).toBeInTheDocument();
  });

  test("creates a new botanical identity from the picker and pots on into it", async () => {
    const user = userEvent.setup();
    const created: BotanicalIdentityResponse = {
      ...identity,
      id: "identity-new",
      scientific_name: "Hoya kerrii",
      display_label: "Hoya kerrii",
    };
    const posts: { path: string; body: Record<string, unknown> }[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const path = requestPath(input);
      if (path.startsWith("/api/v1/explore/taxonomy/candidates"))
        return Promise.resolve(
          new Response("[]", {
            headers: { "Content-Type": "application/json" },
          }),
        );
      if (init?.method === "POST")
        posts.push({ path, body: requestBody(init) });
      if (init?.method === "POST" && path === "/api/v1/botanical-identities")
        return Promise.resolve(
          new Response(JSON.stringify(created), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          }),
        );
      if (init?.method === "POST" && path === "/api/v1/sowings/sowing-1/pot-on")
        return Promise.resolve(
          new Response(
            JSON.stringify({
              sowing: baseSowing,
              plants: [makePlant("p", "P")],
            }),
            { status: 201, headers: { "Content-Type": "application/json" } },
          ),
        );
      throw new Error(`Unexpected fetch: ${path}`);
    });
    renderWithAuth(
      <PotOnLauncher
        source={{ kind: "sowing", sowing: baseSowing }}
        identities={[identity]}
        locations={[plantLocation, sowingOnlyLocation]}
        onSowingUpdated={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Pot on seedlings…" }));
    const picker = screen.getByRole("combobox", { name: /Botanical identity/ });
    await user.clear(picker);
    await user.type(picker, "Hoya kerrii");
    await user.click(
      screen.getByRole("button", { name: "Create identity “Hoya kerrii”" }),
    );
    const dialog = screen.getByRole("dialog", {
      name: "Create botanical identity",
    });
    expect(dialog).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Create identity" }));
    await waitFor(() => {
      expect(
        screen.queryByRole("dialog", { name: "Create botanical identity" }),
      ).not.toBeInTheDocument();
    });
    // Focus returns to the identity picker, not the page body.
    expect(
      screen.getByRole("combobox", { name: /Botanical identity/ }),
    ).toHaveFocus();
    expect(posts[0]).toMatchObject({
      path: "/api/v1/botanical-identities",
      body: { scientific_name: "Hoya kerrii" },
    });
    await user.click(screen.getByRole("button", { name: "Review & confirm" }));
    await user.click(screen.getByRole("button", { name: "Confirm pot-on" }));
    await waitFor(() => {
      expect(posts).toHaveLength(2);
    });
    expect(posts[1]?.body).toMatchObject({
      botanical_identity_id: "identity-new",
    });
  });
});
