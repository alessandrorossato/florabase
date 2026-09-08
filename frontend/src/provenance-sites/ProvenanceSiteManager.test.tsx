import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import type { GeographicPlaceResponse } from "../geographic-places/api";
import { ProvenanceSiteManager } from "./ProvenanceSiteManager";
import type { ProvenanceSiteResponse } from "./api";

const world: GeographicPlaceResponse = {
  id: "01900000-0000-7000-8000-000000000001",
  name: "World",
  parent_id: null,
  display_path: "World",
  place_kind: "canonical",
  place_type: null,
  provenance_site_count: 0,
  direct_usage_count: 0,
  source_name: "unicode_cldr",
  source_version: "48.2.1",
  source_code_type: "un_m49",
  source_code: "001",
  retired_at: null,
  created_at: "2026-09-08T00:00:00Z",
  updated_at: "2026-09-08T00:00:00Z",
};

function response(body: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers:
      status === 204 ? undefined : { "Content-Type": "application/json" },
  });
}

function requestPath(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  return input instanceof URL ? input.toString() : input.url;
}

function requestBody(init?: RequestInit): string {
  return typeof init?.body === "string" ? init.body : "";
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("creates, edits, and deletes a path-aware ProvenanceSite", async () => {
  let sites: ProvenanceSiteResponse[] = [];
  const requests: { path: string; init?: RequestInit }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path = requestPath(input);
    requests.push({ path, init });
    if (path === "/api/v1/provenance-sites" && init?.method === "POST") {
      const payload = JSON.parse(requestBody(init)) as Record<string, string>;
      sites = [
        {
          id: "01900000-0000-7000-8000-000000000002",
          name: payload.name,
          geographic_place_id: payload.geographic_place_id,
          geographic_place_path: "World",
          latitude: payload.latitude,
          longitude: payload.longitude,
          coordinate_accuracy_m: payload.coordinate_accuracy_m,
          notes: payload.notes,
          usage: { seed_lots: 0, plants: 0, plant_groups: 0 },
          created_at: "2026-09-08T00:00:00Z",
          updated_at: "2026-09-08T00:00:00Z",
        },
      ];
      return Promise.resolve(response(sites[0], 201));
    }
    if (path.endsWith(sites[0]?.id ?? "missing") && init?.method === "PUT") {
      const payload = JSON.parse(requestBody(init)) as Record<string, string>;
      sites = [{ ...sites[0], name: payload.name }];
      return Promise.resolve(response(sites[0]));
    }
    if (path.endsWith(sites[0]?.id ?? "missing") && init?.method === "DELETE") {
      sites = [];
      return Promise.resolve(response(null, 204));
    }
    if (path === "/api/v1/provenance-sites")
      return Promise.resolve(response(sites));
    throw new Error(`Unexpected request: ${path}`);
  });

  const user = userEvent.setup();
  render(<ProvenanceSiteManager places={[world]} csrfToken="csrf" />);
  await screen.findByText("No ProvenanceSites recorded.");
  await user.type(
    screen.getByLabelText("ProvenanceSite name"),
    "Monte Pellegrino",
  );
  await user.selectOptions(
    screen.getByLabelText("Geographic place (optional)"),
    world.id,
  );
  await user.type(
    screen.getByLabelText("Latitude (WGS84 decimal)"),
    "38.166667",
  );
  await user.type(
    screen.getByLabelText("Longitude (WGS84 decimal)"),
    "13.350000",
  );
  await user.type(
    screen.getByLabelText("Coordinate accuracy in metres (optional)"),
    "25.5",
  );
  await user.type(
    screen.getByLabelText("Notes (optional)"),
    "Historical label",
  );
  await user.click(screen.getByRole("button", { name: "Save ProvenanceSite" }));
  expect(
    await screen.findByText("Monte Pellegrino was saved."),
  ).toBeInTheDocument();
  expect(screen.getAllByText("World").length).toBeGreaterThan(0);

  const post = requests.find(({ init }) => init?.method === "POST");
  expect(JSON.parse(requestBody(post?.init))).toMatchObject({
    geographic_place_id: world.id,
    latitude: "38.166667",
    longitude: "13.35",
    coordinate_accuracy_m: "25.5",
  });
  expect(new Headers(post?.init?.headers).get("X-CSRF-Token")).toBe("csrf");

  await user.clear(screen.getByLabelText("ProvenanceSite name"));
  await user.type(
    screen.getByLabelText("ProvenanceSite name"),
    "Monte Pellegrino ridge",
  );
  await user.click(screen.getByRole("button", { name: "Save ProvenanceSite" }));
  expect(
    await screen.findByText("Monte Pellegrino ridge was saved."),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Delete ProvenanceSite" }),
  );
  expect(
    await screen.findByText("The ProvenanceSite was deleted."),
  ).toBeInTheDocument();
  await waitFor(() => {
    expect(
      screen.getByText("No ProvenanceSites recorded."),
    ).toBeInTheDocument();
  });
});

test("shows an actionable coordinate-pair validation error", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    if (
      requestPath(input) === "/api/v1/provenance-sites" &&
      init?.method === "POST"
    ) {
      return Promise.resolve(response({ detail: [] }, 422));
    }
    return Promise.resolve(response([]));
  });
  const user = userEvent.setup();
  render(<ProvenanceSiteManager places={[world]} csrfToken="csrf" />);
  await screen.findByText("No ProvenanceSites recorded.");
  await user.type(
    screen.getByLabelText("ProvenanceSite name"),
    "Half coordinate",
  );
  await user.type(screen.getByLabelText("Latitude (WGS84 decimal)"), "38");
  await user.click(screen.getByRole("button", { name: "Save ProvenanceSite" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Latitude and longitude must be entered together",
  );
});
