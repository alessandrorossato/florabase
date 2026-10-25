import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import type { GeographicPlaceResponse } from "../geographic-places/api";
import { ProvenanceSiteManager } from "./ProvenanceSiteManager";
import type { ProvenanceSiteResponse } from "./api";
import type { MapPoint } from "../provenance-map/ProvenanceMap";

vi.mock("../provenance-map/ProvenanceMap", () => ({
  ProvenanceMap: ({
    sites,
    onSelect,
    selectedId,
  }: {
    selectedId: string | null;
    sites: MapPoint[];
    onSelect: (id: string) => void;
  }) => (
    <div aria-label="Geography map of stored provenance sites">
      {sites.map((site) => (
        <button
          key={site.id}
          aria-pressed={site.id === selectedId}
          type="button"
          onClick={() => {
            onSelect(site.id);
          }}
        >
          Map marker {site.name}
        </button>
      ))}
    </div>
  ),
}));

const world: GeographicPlaceResponse = {
  id: "01900000-0000-7000-8000-000000000001",
  name: "World",
  parent_id: null,
  display_path: "World",
  place_kind: "canonical",
  place_type: null,
  provenance_site_count: 0,
  native_range_count: 0,
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
  await screen.findByText("No provenance sites recorded.");
  await user.click(screen.getByRole("button", { name: "New provenance site" }));
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  await user.type(
    screen.getByLabelText("Provenance site name"),
    "Monte Pellegrino",
  );
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  await user.selectOptions(screen.getByLabelText("Geographic place"), world.id);
  await user.click(screen.getByRole("tab", { name: "Coordinates" }));
  await user.type(
    screen.getByLabelText("Latitude (WGS84 decimal)"),
    "38.166667",
  );
  await user.click(screen.getByRole("tab", { name: "Coordinates" }));
  await user.type(
    screen.getByLabelText("Longitude (WGS84 decimal)"),
    "13.350000",
  );
  await user.click(screen.getByRole("tab", { name: "Coordinates" }));
  await user.type(
    screen.getByLabelText("Coordinate accuracy in metres"),
    "25.5",
  );
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.type(
    screen.getByLabelText("Notes", { selector: "textarea" }),
    "Historical label",
  );
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(
    screen.getByRole("button", { name: "Save provenance site" }),
  );
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

  await user.click(screen.getByRole("button", { name: "Edit" }));
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  await user.clear(screen.getByLabelText("Provenance site name"));
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  await user.type(
    screen.getByLabelText("Provenance site name"),
    "Monte Pellegrino ridge",
  );
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(
    screen.getByRole("button", { name: "Save provenance site" }),
  );
  expect(
    await screen.findByText("Monte Pellegrino ridge was saved."),
  ).toBeInTheDocument();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  await user.click(screen.getByLabelText("More provenance site actions"));
  await user.click(
    screen.getByRole("button", { name: "Delete provenance site" }),
  );
  expect(
    await screen.findByText("The provenance site was deleted."),
  ).toBeInTheDocument();
  await waitFor(() => {
    expect(
      screen.getByText("No provenance sites recorded."),
    ).toBeInTheDocument();
  });
});

test("shows an actionable coordinate-pair validation error", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    if (
      requestPath(input) === "/api/v1/provenance-sites" &&
      init?.method === "POST"
    ) {
      return Promise.resolve(
        response(
          {
            detail: [
              {
                loc: ["body", "longitude"],
                msg: "Longitude is required with latitude",
              },
            ],
          },
          422,
        ),
      );
    }
    return Promise.resolve(response([]));
  });
  const user = userEvent.setup();
  render(<ProvenanceSiteManager places={[world]} csrfToken="csrf" />);
  await screen.findByText("No provenance sites recorded.");
  await user.click(screen.getByRole("button", { name: "New provenance site" }));
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  await user.type(
    screen.getByLabelText("Provenance site name"),
    "Half coordinate",
  );
  await user.click(screen.getByRole("tab", { name: "Coordinates" }));
  await user.type(screen.getByLabelText("Latitude (WGS84 decimal)"), "38");
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  await user.click(
    screen.getByRole("button", { name: "Save provenance site" }),
  );
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Latitude and longitude must be entered together",
  );
  await waitFor(() => {
    expect(screen.getByRole("tab", { name: "Coordinates" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByLabelText("Longitude (WGS84 decimal)")).toHaveFocus();
  });
  expect(screen.getByLabelText("Latitude (WGS84 decimal)")).toHaveValue(38);
  await user.click(screen.getByRole("tab", { name: "Essentials" }));
  await user.type(screen.getByLabelText("Provenance site name"), " corrected");
  expect(screen.getByRole("tab", { name: "Essentials" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(screen.getByLabelText("Provenance site name")).toHaveFocus();
});

test("List and Map share all sites and selection; only stored coordinate pairs create markers", async () => {
  const coordinateSite: ProvenanceSiteResponse = {
    id: "mapped-site",
    name: "Ridge collection",
    geographic_place_id: world.id,
    geographic_place_path: "World",
    latitude: "38.1",
    longitude: "13.3",
    coordinate_accuracy_m: null,
    notes: null,
    usage: { seed_lots: 1, plants: 0, plant_groups: 0 },
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
  };
  const withoutCoordinates = {
    ...coordinateSite,
    id: "unmapped-site",
    name: "Historical valley",
    latitude: null,
    longitude: null,
  };
  const requests: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    requests.push(requestPath(input));
    return Promise.resolve(response([coordinateSite, withoutCoordinates]));
  });
  const { rerender } = render(
    <ProvenanceSiteManager places={[world]} csrfToken="csrf" mode="browse" />,
  );
  expect(
    await screen.findByRole("button", { name: /Historical valley/ }),
  ).toBeInTheDocument();
  expect(
    within(screen.getByRole("list", { name: "Provenance sites" })).getByRole(
      "button",
      { name: /Ridge collection/ },
    ),
  ).toBeInTheDocument();
  rerender(
    <ProvenanceSiteManager places={[world]} csrfToken="csrf" mode="map" />,
  );
  const directory = screen.getByRole("list", { name: "Provenance sites" });
  const user = userEvent.setup();
  await user.click(
    within(directory).getByRole("button", { name: /Historical valley/ }),
  );
  expect(
    within(directory).getByRole("button", { name: /Historical valley/ }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getByRole("button", { name: "Map marker Ridge collection" }),
  ).toHaveAttribute("aria-pressed", "false");
  expect(
    screen.queryByRole("button", { name: "Map marker Historical valley" }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Edit" })).toBeEnabled();
  expect(screen.getAllByText("No coordinates recorded")).toHaveLength(2);
  rerender(
    <ProvenanceSiteManager places={[world]} csrfToken="csrf" mode="browse" />,
  );
  expect(
    within(directory).getByRole("button", { name: /Historical valley/ }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    within(screen.getByRole("list", { name: "Provenance sites" })).getByRole(
      "button",
      { name: /Ridge collection/ },
    ),
  ).toBeInTheDocument();
  await user.click(
    await screen.findByRole("button", { name: "Map marker Ridge collection" }),
  );
  expect(
    within(directory).getByRole("button", { name: /Ridge collection/ }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getByRole("button", { name: "Map marker Ridge collection" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("38.1, 13.3")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Edit" }));
  expect(
    screen.getByRole("dialog", { name: "Edit provenance site" }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Provenance site name")).toHaveValue(
    "Ridge collection",
  );
  expect(requests).toEqual(["/api/v1/provenance-sites"]);
});

test("shows zero accuracy and distinguishes delete conflicts from other failures", async () => {
  const site: ProvenanceSiteResponse = {
    id: "site-with-zero-accuracy",
    name: "Survey point",
    geographic_place_id: world.id,
    geographic_place_path: "World",
    latitude: "0",
    longitude: "0",
    coordinate_accuracy_m: "0",
    notes: null,
    usage: { seed_lots: 0, plants: 0, plant_groups: 0 },
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
  };
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path = requestPath(input);
    if (
      path === `/api/v1/provenance-sites/${site.id}` &&
      init?.method === "DELETE"
    )
      return Promise.resolve(response({ detail: "Unavailable" }, 500));
    return Promise.resolve(response([site]));
  });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();
  render(<ProvenanceSiteManager places={[world]} csrfToken="csrf" />);
  await user.click(
    within(
      await screen.findByRole("list", { name: "Provenance sites" }),
    ).getByRole("button", { name: /Survey point/ }),
  );
  expect(screen.getByText("± 0 m")).toBeInTheDocument();
  await user.click(screen.getByLabelText("More provenance site actions"));
  await user.click(
    screen.getByRole("button", { name: "Delete provenance site" }),
  );
  expect(
    await screen.findByText("Florabase could not delete this provenance site."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(/used by collection records/),
  ).not.toBeInTheDocument();
});

test("associated sites use exact place identity independently of matching names and search", async () => {
  const sites: ProvenanceSiteResponse[] = [
    world.id,
    "01900000-0000-7000-8000-000000000099",
  ].map((placeId, i) => ({
    id: `01900000-0000-7000-8000-00000000001${String(i)}`,
    name: `Same locality site ${String(i)}`,
    geographic_place_id: placeId,
    geographic_place_path: "World → Same locality",
    latitude: null,
    longitude: null,
    coordinate_accuracy_m: null,
    notes: null,
    usage: { seed_lots: 0, plants: 0, plant_groups: 0 },
    created_at: "2026-10-24T00:00:00Z",
    updated_at: "2026-10-24T00:00:00Z",
  }));
  vi.spyOn(globalThis, "fetch").mockResolvedValue(response(sites));
  render(
    <ProvenanceSiteManager
      places={[world]}
      placeId={world.id}
      csrfToken="csrf"
      query="Same locality"
    />,
  );
  await screen.findByRole("button", { name: /Same locality site 0/ });
  expect(
    screen.queryByRole("button", { name: /Same locality site 1/ }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Show all provenance sites" }),
  ).toHaveAttribute("href", "#/geography?mode=sites");
});
