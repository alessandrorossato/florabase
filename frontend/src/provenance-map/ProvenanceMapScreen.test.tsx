import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import type { ProvenanceMapResponse, ProvenanceMapSite } from "./api";
import { filterMapSites } from "./filter";
import { ProvenanceMapScreen } from "./ProvenanceMapScreen";

vi.mock("./ProvenanceMap", () => ({
  ProvenanceMap: ({
    sites,
    onSelect,
  }: {
    sites: ProvenanceMapSite[];
    onSelect: (id: string) => void;
  }) => (
    <div aria-label="Interactive collection provenance map">
      {sites.map((site) => (
        <button
          key={site.id}
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

const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    session: {
      user_id: "01900000-0000-7000-8000-000000000001",
      login_name: "owner",
      display_name: "Owner",
      owner: true,
    },
    csrfToken: "csrf",
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};

const site: ProvenanceMapSite = {
  id: "01900000-0000-7000-8000-000000000010",
  name: "Monte Pellegrino collection ridge with a deliberately long retained label",
  latitude: "38.166667",
  longitude: "13.350000",
  coordinate_accuracy_m: "25.500",
  geographic_place_id: "01900000-0000-7000-8000-000000000020",
  geographic_place_path:
    "World → Europe → Italy → Sicily → Palermo → Monte Pellegrino upper collection locality",
  usage: { seed_lots: 1, plants: 1, plant_groups: 1, total: 3 },
  records: [
    {
      record_type: "seed_lot",
      id: "01900000-0000-7000-8000-000000000030",
      label: "Historical seeds",
      lifecycle: "discarded",
      is_active: false,
      botanical_identity: {
        id: "01900000-0000-7000-8000-000000000040",
        display_label: "Clitoria ternatea",
      },
    },
    {
      record_type: "plant",
      id: "01900000-0000-7000-8000-000000000031",
      label: "Living plant",
      lifecycle: "active",
      is_active: true,
      botanical_identity: {
        id: "01900000-0000-7000-8000-000000000041",
        display_label: "Chamaerops humilis",
      },
    },
    {
      record_type: "plant_group",
      id: "01900000-0000-7000-8000-000000000032",
      label: null,
      lifecycle: "transferred",
      is_active: false,
      botanical_identity: {
        id: "01900000-0000-7000-8000-000000000041",
        display_label: "Chamaerops humilis",
      },
    },
  ],
};

function dataset(
  overrides: Partial<ProvenanceMapResponse> = {},
): ProvenanceMapResponse {
  return {
    total_provenance_sites: 1,
    coordinate_less_sites: 0,
    sites: [site],
    ...overrides,
  };
}

function renderMap(data: ProvenanceMapResponse) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  return render(
    <AuthContext.Provider value={auth}>
      <ProvenanceMapScreen />
    </AuthContext.Provider>,
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("filters records deterministically and hides a site with no matching records", () => {
  expect(
    filterMapSites([site], {
      seedLots: true,
      plants: false,
      identityQuery: "clitoria",
    })[0]?.usage,
  ).toEqual({ seed_lots: 1, plants: 0, plant_groups: 0, total: 1 });
  expect(
    filterMapSites([site], {
      seedLots: false,
      plants: true,
      identityQuery: "chamaerops",
    })[0]?.usage,
  ).toEqual({ seed_lots: 0, plants: 1, plant_groups: 1, total: 2 });
  expect(
    filterMapSites([site], {
      seedLots: true,
      plants: true,
      identityQuery: "absent identity",
    }),
  ).toEqual([]);
});

test("synchronizes accessible marker and list selection and exposes navigation and history", async () => {
  const second = {
    ...site,
    id: "01900000-0000-7000-8000-000000000099",
    name: "Doi Suthep",
    latitude: "18.804900",
    longitude: "98.921600",
  };
  renderMap(dataset({ total_provenance_sites: 2, sites: [site, second] }));
  expect(
    await screen.findByText("2 mapped provenance sites"),
  ).toBeInTheDocument();
  const user = userEvent.setup();
  const companion = screen.getByRole("complementary", {
    name: "Mapped provenance sites",
  });
  await user.click(
    within(companion).getByRole("button", {
      name: /Monte Pellegrino collection ridge/,
    }),
  );
  expect(
    screen.getAllByText(site.geographic_place_path ?? "").length,
  ).toBeGreaterThan(0);
  expect(screen.getByText("± 25.500 m")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Historical seeds" }),
  ).toHaveAttribute("href", `#/seeds/${site.records[0].id}`);
  expect(screen.getByRole("link", { name: "Living plant" })).toHaveAttribute(
    "href",
    `#/plants/${site.records[1].id}`,
  );
  expect(
    screen.getByRole("link", { name: "Chamaerops humilis" }),
  ).toHaveAttribute("href", `#/plant-groups/${site.records[2].id}`);
  expect(
    screen.getByRole("link", { name: "Botanical identity: Clitoria ternatea" }),
  ).toHaveAttribute(
    "href",
    `#/identities/${site.records[0].botanical_identity.id}`,
  );
  expect(screen.getByText("Discarded")).toBeInTheDocument();

  await user.click(
    screen.getByRole("button", { name: "Map marker Doi Suthep" }),
  );
  expect(
    screen.getByRole("heading", { name: "Doi Suthep" }),
  ).toBeInTheDocument();
  expect(
    within(companion).getByRole("button", {
      name: /Monte Pellegrino collection ridge/,
    }),
  ).toHaveAttribute("aria-pressed", "false");
  await user.click(
    within(companion).getByRole("button", {
      name: /Monte Pellegrino collection ridge/,
    }),
  );
  expect(screen.getByRole("link", { name: "Edit site" })).toHaveAttribute(
    "href",
    `#/geography/${site.id}`,
  );
});

test("filters marker details and reports a filter-empty state", async () => {
  renderMap(dataset());
  const user = userEvent.setup();
  await screen.findByText("1 mapped provenance sites");
  await user.click(
    screen.getByRole("button", {
      name: /Monte Pellegrino collection ridge.*3 linked/,
    }),
  );
  await user.click(screen.getByRole("checkbox", { name: "SeedLots" }));
  expect(
    screen.queryByRole("link", { name: "Historical seeds" }),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/2 linked records/)).toBeInTheDocument();
  await user.type(
    screen.getByRole("searchbox", { name: "Botanical identity" }),
    "missing",
  );
  expect(
    screen.getByRole("heading", {
      name: "No provenance sites match the current filters",
    }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(
    await screen.findByText("1 mapped provenance sites"),
  ).toBeInTheDocument();
});

test("distinguishes no-site and no-coordinate empty states", async () => {
  const view = renderMap(
    dataset({ total_provenance_sites: 0, coordinate_less_sites: 0, sites: [] }),
  );
  expect(
    await screen.findByRole("heading", { name: "No ProvenanceSites recorded" }),
  ).toBeInTheDocument();
  view.unmount();
  vi.restoreAllMocks();
  renderMap(
    dataset({ total_provenance_sites: 2, coordinate_less_sites: 2, sites: [] }),
  );
  expect(
    await screen.findByRole("heading", {
      name: "No provenance sites have coordinates",
    }),
  ).toBeInTheDocument();
  await waitFor(() => {
    expect(globalThis.fetch).toHaveBeenCalled();
  });
});

test("announces loading and recovers from a map request failure", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "unavailable" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify(
          dataset({
            total_provenance_sites: 0,
            coordinate_less_sites: 0,
            sites: [],
          }),
        ),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
  render(
    <AuthContext.Provider value={auth}>
      <ProvenanceMapScreen />
    </AuthContext.Provider>,
  );
  expect(screen.getByText("Loading provenance map…")).toBeInTheDocument();
  expect(
    await screen.findByText(
      "Florabase could not load the collection provenance map.",
    ),
  ).toBeInTheDocument();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("heading", { name: "No ProvenanceSites recorded" }),
  ).toBeInTheDocument();
});
