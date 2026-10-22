import {
  cleanup,
  act,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import type { ProvenanceMapResponse, ProvenanceMapSite } from "./api";
import { identityGroups, uniqueRecords } from "./model";
import { filterMapSites } from "./filter";
import { ProvenanceMapScreen } from "./ProvenanceMapScreen";

vi.mock("./ProvenanceMap", () => ({
  ProvenanceMap: ({
    sites,
    onSelect,
    selectedId,
  }: {
    sites: ProvenanceMapSite[];
    selectedId: string | null;
    onSelect: (id: string) => void;
  }) => (
    <div aria-label="Interactive collection provenance map">
      {sites.map((site) => (
        <button
          key={site.id}
          type="button"
          aria-pressed={selectedId === site.id}
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
      canonical_origin: "http://localhost:5173",
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
  window.history.replaceState(null, "", "#/map");
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

test("synchronizes marker/list/inspector and exposes identity groups, records and lifecycle", async () => {
  const second = {
    ...site,
    id: "second",
    name: "Doi Suthep",
    coordinate_accuracy_m: null,
  };
  renderMap(dataset({ total_provenance_sites: 2, sites: [site, second] }));
  const user = userEvent.setup();
  const inspector = await screen.findByRole("complementary", {
    name: "Provenance site inspector",
  });
  await user.click(
    await within(inspector).findByRole("button", { name: /^Monte Pellegrino/ }),
  );
  expect(screen.getByText("± 25.500 m")).toBeVisible();
  expect(
    screen.getByRole("button", { name: /Map marker Monte/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await user.click(
    screen.getByText("Clitoria ternatea", { selector: "summary" }),
  );
  await user.click(
    screen.getByText("Chamaerops humilis", { selector: "summary" }),
  );
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
  expect(screen.getByText("Discarded")).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Manage provenance site" }),
  ).toHaveAttribute("href", `#/geography/${site.id}`);
  await user.click(
    screen.getByRole("button", { name: "Map marker Doi Suthep" }),
  );
  expect(screen.getByRole("heading", { name: "Doi Suthep" })).toBeVisible();
  expect(screen.getByText("Not recorded")).toBeVisible();
  await user.click(screen.getByRole("button", { name: /All visible sites/ }));
  expect(
    within(inspector).getByRole("button", { name: /^Monte Pellegrino/ }),
  ).toBeVisible();
});

test("functional KPIs deduplicate record keys and identity IDs", async () => {
  renderMap(
    dataset({
      sites: [site, { ...site, id: "second", name: "Second" }],
      total_provenance_sites: 3,
      coordinate_less_sites: 1,
    }),
  );
  const user = userEvent.setup();
  const kpis = await screen.findByLabelText("Collection origin counts");
  expect(
    within(kpis).getByRole("button", { name: /3 Directly linked records/ }),
  ).toBeVisible();
  expect(
    within(kpis).getByRole("link", { name: /1 Without coordinates/ }),
  ).toHaveAttribute("href", "#/geography?mode=sites");
  const trigger = within(kpis).getByRole("button", {
    name: /2 Botanical identities/,
  });
  await user.click(trigger);
  const dialog = screen.getByRole("dialog", {
    name: "Botanical identities represented",
  });
  expect(within(dialog).getByText("2 directly linked records")).toBeVisible();
  await user.type(within(dialog).getByRole("searchbox"), "clitoria");
  expect(
    within(dialog).queryByText("Chamaerops humilis"),
  ).not.toBeInTheDocument();
  await user.keyboard("{Escape}");
  expect(trigger).toHaveFocus();
  expect(uniqueRecords([site, site])).toHaveLength(3);
  expect(identityGroups(site.records)).toHaveLength(2);
});

test("record filters retain eligible inspection and clear excluded selection permanently", async () => {
  renderMap(dataset());
  const user = userEvent.setup();
  await user.click(
    await screen.findByRole("button", { name: /Map marker Monte/ }),
  );
  await user.click(screen.getByRole("button", { name: "Filters" }));
  await user.click(screen.getByRole("checkbox", { name: "Seed lots" }));
  await user.click(screen.getByRole("button", { name: "Done" }));
  expect(screen.getByRole("heading", { name: site.name })).toBeVisible();
  expect(document.querySelector(".origins-site-counts")).toHaveTextContent(
    "2 directly linked records · 1 botanical identity",
  );
  expect(screen.queryByText("Historical seeds")).not.toBeInTheDocument();
  await user.type(
    screen.getByRole("searchbox", { name: "Botanical identity" }),
    "missing",
  );
  expect(
    screen.getByRole("heading", {
      name: "No provenance sites match the current filters",
    }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(
    screen.queryByRole("heading", { name: site.name }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /Map marker Monte/ }),
  ).toHaveAttribute("aria-pressed", "false");
});

test("mapped sites without linked material remain inspectable in the unfiltered view", async () => {
  const unlinked = {
    ...site,
    id: "empty",
    name: "Recorded locality",
    records: [],
    usage: { total: 0, plants: 0, seed_lots: 0, plant_groups: 0 },
  };
  expect(
    filterMapSites([unlinked], {
      seedLots: true,
      plants: true,
      identityQuery: "",
    }),
  ).toHaveLength(1);
  expect(
    filterMapSites([unlinked], {
      seedLots: false,
      plants: true,
      identityQuery: "",
    }),
  ).toHaveLength(0);
  renderMap(dataset({ sites: [unlinked] }));
  await userEvent.click(
    await screen.findByRole("button", { name: "Map marker Recorded locality" }),
  );
  expect(
    screen.getByText(/No directly linked eligible collection records/),
  ).toBeVisible();
});

test("initial URL and browser navigation restore legacy filters and clear inspection", async () => {
  window.history.replaceState(null, "", "#/map?q=chamaerops&seed_lots=false");
  renderMap(dataset());
  const user = userEvent.setup();
  await user.click(
    await screen.findByRole("button", { name: /Map marker Monte/ }),
  );
  expect(
    screen.getByRole("searchbox", { name: "Botanical identity" }),
  ).toHaveValue("chamaerops");
  expect(document.querySelector(".origins-site-counts")).toHaveTextContent(
    "2 directly linked records",
  );
  act(() => {
    window.history.replaceState(null, "", "#/map?q=clitoria&plants=false");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  expect(
    screen.getByRole("searchbox", { name: "Botanical identity" }),
  ).toHaveValue("clitoria");
  expect(
    screen.queryByRole("heading", { name: site.name }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /1 Directly linked records/ }),
  ).toBeVisible();
});

test("Saved View opening including the identical route clears transient inspection", async () => {
  window.history.replaceState(null, "", "#/map?plants=false");
  const saved = {
    id: "saved",
    name: "Seed origins",
    surface: "provenance_map",
    state_version: 1,
    compatibility: "supported",
    state: { plants: false },
    created_at: "2026-10-22T00:00:00Z",
    updated_at: "2026-10-22T00:00:00Z",
  };
  vi.spyOn(globalThis, "fetch").mockImplementation((input) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          (typeof input === "string"
            ? input
            : input instanceof URL
              ? input.href
              : input.url
          ).includes("saved-views")
            ? [saved]
            : dataset(),
        ),
        { headers: { "Content-Type": "application/json" } },
      ),
    ),
  );
  render(
    <AuthContext.Provider value={auth}>
      <ProvenanceMapScreen />
    </AuthContext.Provider>,
  );
  const user = userEvent.setup();
  await user.click(
    await screen.findByRole("button", { name: /Map marker Monte/ }),
  );
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(
    await screen.findByRole("button", { name: "Open Seed origins" }),
  );
  await waitFor(() => {
    expect(
      screen.queryByRole("heading", { name: site.name }),
    ).not.toBeInTheDocument();
  });
  expect(window.location.hash).toBe("#/map?plants=false");
});

test("keyboard and mounted pane switching retain inspection, with Escape returning to the site list", async () => {
  renderMap(dataset());
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Inspector" }));
  screen.getByRole("button", { name: /Monte Pellegrino.*3 linked/ }).focus();
  await user.keyboard("{Enter}");
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: site.name })).toHaveFocus();
  });
  await user.click(screen.getByRole("button", { name: "Map & evidence" }));
  expect(document.querySelector(".maps-workspace")).toHaveAttribute(
    "data-pane",
    "map",
  );
  expect(screen.getByRole("heading", { name: site.name })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Inspector" }));
  screen.getByRole("heading", { name: site.name }).focus();
  await user.keyboard("{Escape}");
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: /Monte Pellegrino.*3 linked/ }),
    ).toHaveFocus();
  });
});

test("distinguishes no-site and no-coordinate states and links the non-map path", async () => {
  const result = renderMap(
    dataset({ total_provenance_sites: 0, coordinate_less_sites: 0, sites: [] }),
  );
  expect(
    await screen.findByRole("heading", {
      name: "No provenance sites recorded",
    }),
  ).toBeVisible();
  result.unmount();
  vi.restoreAllMocks();
  renderMap(
    dataset({ total_provenance_sites: 2, coordinate_less_sites: 2, sites: [] }),
  );
  expect(
    await screen.findByRole("heading", {
      name: "No provenance sites have coordinates",
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Open provenance sites in Geography" }),
  ).toHaveAttribute("href", "#/geography?mode=sites");
});

test("announces loading and recovers from an API failure", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response("{}", { status: 503 }))
    .mockResolvedValueOnce(
      new Response(JSON.stringify(dataset()), {
        headers: { "Content-Type": "application/json" },
      }),
    );
  render(
    <AuthContext.Provider value={auth}>
      <ProvenanceMapScreen />
    </AuthContext.Provider>,
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "Loading collection origins",
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Florabase could not load collection origins",
  );
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("button", { name: /Map marker Monte/ }),
  ).toBeVisible();
});

test("filter labels toggle their complete row and shared dismissals retain applied values", async () => {
  renderMap(dataset());
  const user = userEvent.setup();
  const trigger = await screen.findByRole("button", { name: "Filters" });
  await user.click(trigger);
  const dialog = screen.getByRole("dialog", {
    name: "Collection origins filters",
  });
  const categories = within(dialog).getByRole("group", {
    name: "Directly linked record categories",
  });
  await user.click(within(categories).getByText("Plants and plant groups"));
  expect(
    within(categories).getByRole("checkbox", {
      name: "Plants and plant groups",
    }),
  ).not.toBeChecked();
  await user.keyboard("{Escape}");
  expect(trigger).toHaveFocus();
  await user.click(trigger);
  expect(
    screen.getByRole("checkbox", { name: "Plants and plant groups" }),
  ).not.toBeChecked();
  await user.click(screen.getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
