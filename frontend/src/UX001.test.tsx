import { emptyOverview, journalFixture } from "./collection/dashboardFixtures";
import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";

const identity = {
  id: "01900000-0000-7000-8000-000000000099",
  scientific_name: "Acer palmatum",
  cultivar_name: "Bloodgood",
  common_name: "Japanese maple",
  display_label: "Acer palmatum ‘Bloodgood’",
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-01T10:00:00Z",
};

const event = {
  id: "01900000-0000-7000-8000-000000000401",
  kind: "observation",
  occurred_on: { precision: "month", year: 2026, month: 8, day: null },
  notes: "Strong new growth.",
  target: {
    type: "plant",
    id: "01900000-0000-7000-8000-000000000201",
    label: "Courtyard maple",
    lifecycle: "active",
    botanical_identity: {
      id: identity.id,
      display_label: identity.display_label,
    },
  },
  destination_location_id: null,
  destination_location: null,
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-01T10:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockAuthenticated(
  handler: (path: string, init?: RequestInit) => Response,
) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
    if (path.endsWith("/auth/session"))
      return Promise.resolve(
        json({
          user_id: "01900000-0000-7000-8000-000000000001",
          login_name: "owner",
          display_name: "Florabase Owner",
          owner: true,
        }),
      );
    if (path.endsWith("/auth/csrf"))
      return Promise.resolve(json({ csrf_token: "csrf" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    return Promise.resolve(handler(path, init));
  });
}

beforeEach(() => {
  window.history.replaceState(null, "", "#/dashboard");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("Dashboard is the default workspace with grouped desktop and five-item mobile navigation", async () => {
  mockAuthenticated((path) => {
    if (path.startsWith("/api/v1/dashboard"))
      return json({
        counts: {
          active_plants: 12,
          active_plant_groups: 3,
          active_seed_lots: 8,
          active_sowings: 4,
          botanical_identities: 9,
          events: 27,
        },
        overview: {
          ...emptyOverview,
          recent_activity: [journalFixture(event.id, "Strong new growth.")],
        },
        recent_events: [event],
      });
    if (path === "/api/v1/events") return json([event]);
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<App />);

  expect(
    await screen.findByRole(
      "heading",
      { name: "Dashboard" },
      { timeout: 10_000 },
    ),
  ).toBeInTheDocument();
  const snapshot = await screen.findByRole("region", {
    name: "Collection snapshot",
  });
  for (const label of [
    "Seed lots: 8",
    "Sowings: 4",
    "Plants: 12",
    "Plant groups: 3",
  ]) {
    expect(
      within(snapshot).getByRole("link", { name: label }),
    ).toBeInTheDocument();
  }
  expect(screen.getByText(/Strong new growth\./)).toBeInTheDocument();

  const desktop = screen.getByRole("navigation", {
    name: "Primary navigation",
  });
  for (const group of ["Overview", "Collection", "Explore", "Sourcing"])
    expect(
      within(desktop).getByRole("region", { name: group }),
    ).toBeInTheDocument();
  expect(
    within(within(desktop).getByRole("region", { name: "Explore" })).getByRole(
      "link",
      { name: "Botanical identities" },
    ),
  ).toBeInTheDocument();
  const mobile = screen.getByRole("navigation", {
    name: "Mobile primary navigation",
  });
  expect(mobile.querySelectorAll("a, button")).toHaveLength(5);
  expect(
    within(mobile)
      .getAllByRole("link")
      .map((item) => item.textContent),
  ).toEqual(["Home", "Seeds", "Sowings", "Plants"]);
  expect(
    within(snapshot).getByRole("link", { name: /Plant groups.*3/ }),
  ).toHaveAttribute("href", "#/plants?type=group");
  await user.click(screen.getByRole("button", { name: "Quick add" }));
  expect(
    screen.getByRole("navigation", { name: "Quick actions" }),
  ).toHaveTextContent("New seed lot");
  await user.keyboard("{Escape}");
  await user.click(within(mobile).getByRole("button", { name: "More" }));
  expect(
    screen.getByRole("navigation", { name: "More navigation" }),
  ).toBeInTheDocument();
  expect(
    within(
      screen.getByRole("navigation", { name: "More navigation" }),
    ).getByRole("link", { name: "Journal" }),
  ).toBeInTheDocument();
  await user.click(within(mobile).getByRole("link", { name: "Home" }));
  expect(
    screen.queryByRole("navigation", { name: "More navigation" }),
  ).not.toBeInTheDocument();

  await user.click(within(desktop).getByRole("link", { name: "Journal" }));
  expect(
    await screen.findByRole("heading", { name: "Journal" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("How Event corrections affect current state"),
  ).not.toBeInTheDocument();
  expect(
    await screen.findByRole("link", { name: "Courtyard maple" }),
  ).toHaveAttribute("href", `#/plants/${event.target.id}?tab=events`);
  await user.click(screen.getByRole("button", { name: "Filters" }));
  await user.click(screen.getByRole("checkbox", { name: "Lifecycle" }));
  await user.click(screen.getByRole("button", { name: "Done" }));
  expect(screen.getByRole("status")).toHaveTextContent(
    "No Journal entries match this search or filter.",
  );
});

test("Botanical identity detail is a cross-collection hub without implied lineage", async () => {
  window.history.replaceState(null, "", `#/identities/${identity.id}`);
  const seedLot = {
    id: "seed-1",
    label: "Bloodgood seed lot",
    lifecycle: "active",
    botanical_identity: {
      id: identity.id,
      display_label: identity.display_label,
    },
    quantity: {
      kind: "seed_count",
      value: 18,
      unit: null,
      is_approximate: false,
    },
    location: { id: "location-1", display_path: "Seed cabinet" },
  };
  const sowing = {
    id: "sowing-1",
    label: "Autumn tray",
    lifecycle: "active",
    seed_lot: seedLot,
    location: { id: "location-2", display_path: "Greenhouse → Bench 2" },
  };
  mockAuthenticated((path) => {
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === `/api/v1/botanical-identities/${identity.id}/collection`)
      return json({
        identity,
        seed_lots: [seedLot],
        sowings: [sowing],
        plants: [
          {
            id: "plant-1",
            label: "Courtyard maple",
            lifecycle: "active",
            botanical_identity: {
              id: identity.id,
              display_label: identity.display_label,
            },
            location: { id: "location-1", display_path: "Courtyard" },
          },
        ],
        plant_groups: [
          {
            id: "group-1",
            label: "Maple seedlings",
            lifecycle: "active",
            botanical_identity: {
              id: identity.id,
              display_label: identity.display_label,
            },
            location: null,
          },
        ],
        harvests: [],
        events: [event],
      });
    if (path === `/api/v1/botanical-identities/${identity.id}/profile`)
      return json(
        {
          detail: {
            code: "botanical_profile_not_found",
            message: "Botanical profile not found",
          },
        },
        404,
      );
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<App />);

  await vi.dynamicImportSettled();
  expect(
    await screen.findByRole("heading", { name: identity.display_label }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("navigation", { name: "Breadcrumb" }),
  ).toContainElement(
    within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole(
      "link",
      { name: "Botanical identities" },
    ),
  );
  expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute(
    "aria-controls",
    "panel-overview",
  );
  expect(screen.getByRole("tabpanel")).toHaveAttribute("id", "panel-overview");
  expect(
    screen.getByRole("heading", { name: "Botanical summary" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Collection snapshot" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Edit botanical identity" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Delete botanical identity" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  expect(screen.getByRole("link", { name: "Add seed lot" })).toHaveAttribute(
    "href",
    `#/seeds?action=create&identity=${identity.id}`,
  );

  await user.keyboard("{Escape}");
  for (const [name, route] of [
    ["Seed lots", "seeds"],
    ["Sowings", "sowings"],
    ["Plants", "plants"],
    ["Plant groups", "plants"],
    ["Harvests", "harvests"],
  ]) {
    expect(
      await screen.findByRole("link", {
        name: new RegExp(`View all ${name}:`),
      }),
    ).toHaveAttribute(
      "href",
      expect.stringContaining(`#/${route}?identity_id=${identity.id}`),
    );
  }
  expect(screen.queryByRole("tab", { name: "Collection" })).toBeNull();
  await user.click(screen.getByRole("button", { name: "Start sowing" }));
  const sowingWorkflow = await screen.findByRole("dialog", {
    name: "Start sowing",
  });
  expect(
    await within(sowingWorkflow).findByRole("link", {
      name: "Bloodgood seed lot",
    }),
  ).toHaveAttribute("href", "#/sowings?action=start&seedLot=seed-1");
  await user.click(
    within(sowingWorkflow).getByRole("button", { name: "Cancel" }),
  );
  await user.click(screen.getByRole("tab", { name: "Media" }));
  for (const [name, href] of [
    ["Bloodgood seed lot", "#/seeds/seed-1?tab=photos"],
    ["Autumn tray", "#/sowings/sowing-1?tab=photos"],
    ["Courtyard maple", "#/plants/plant-1?tab=photos"],
    ["Maple seedlings", "#/plant-groups/group-1?tab=photos"],
  ]) {
    expect(await screen.findByRole("link", { name })).toHaveAttribute(
      "href",
      href,
    );
  }
  await user.click(screen.getByRole("tab", { name: "History" }));
  expect(screen.getByText(/Strong new growth\./)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Courtyard maple" })).toHaveAttribute(
    "href",
    `#/plants/${event.target.id}?tab=events`,
  );
});

test("Botanical identity directory uses bounded local thumbnails and configured external covers", async () => {
  window.history.replaceState(null, "", "#/identities");
  const localCoverIdentity = {
    ...identity,
    compact_cover_kind: "local" as const,
  };
  const externalCoverIdentity = {
    ...identity,
    id: "01900000-0000-7000-8000-000000000098",
    scientific_name: "Acer rubrum",
    display_label: "Acer rubrum",
    common_name: "Red maple",
    compact_cover_kind: "external" as const,
    compact_external_cover_url: "https://images.example.test/acer-rubrum.jpg",
  };
  const noCoverIdentity = {
    ...identity,
    id: "01900000-0000-7000-8000-000000000097",
    scientific_name: "Acer saccharum",
    display_label: "Acer saccharum",
    common_name: "Sugar maple",
    compact_cover_kind: null,
  };
  const fetch = vi.fn((path: string) => {
    if (path === "/api/v1/botanical-identities")
      return json([localCoverIdentity, externalCoverIdentity, noCoverIdentity]);
    throw new Error(`Unexpected request: ${path}`);
  });
  mockAuthenticated(fetch);
  render(<App />);

  const directory = await screen.findByRole("region", {
    name: "Identity directory",
  });
  await within(directory).findByRole("button", { name: /Acer rubrum/ });
  const images = Array.from(directory.querySelectorAll("img"));
  expect(images).toHaveLength(2);
  expect(images[0]).toHaveAttribute(
    "src",
    `/api/v1/botanical-identities/${identity.id}/cover-image/thumbnail`,
  );
  expect(images[1]).toHaveAttribute(
    "src",
    externalCoverIdentity.compact_external_cover_url,
  );
  expect(images[1]).toHaveAttribute("loading", "lazy");
  expect(images[1]).toHaveAttribute("referrerpolicy", "no-referrer");
  expect(fetch.mock.calls.some(([path]) => path.startsWith("https://"))).toBe(
    false,
  );
});

test("A Botanical identity tab deep link restores the selected collection view", async () => {
  window.history.replaceState(
    null,
    "",
    `#/identities/${identity.id}?tab=events`,
  );
  mockAuthenticated((path) => {
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === `/api/v1/botanical-identities/${identity.id}/collection`)
      return json({
        identity,
        seed_lots: [],
        sowings: [],
        plants: [],
        plant_groups: [],
        harvests: [],
        events: [],
      });
    if (path === `/api/v1/botanical-identities/${identity.id}/profile`)
      return json({ detail: "not needed" }, 404);
    throw new Error(`Unexpected request: ${path}`);
  });
  render(<App />);

  expect(await screen.findByRole("tab", { name: "History" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(
    await screen.findByText(
      "No events belong to plants or plant groups with this identity.",
    ),
  ).toBeInTheDocument();
});

test("Botanical reference deep links use compact context and defer collection work", async () => {
  window.history.replaceState(
    null,
    "",
    `#/identities/${identity.id}?tab=reference`,
  );
  const requested: string[] = [];
  mockAuthenticated((path) => {
    requested.push(path);
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === `/api/v1/botanical-identities/${identity.id}/profile`)
      return json({ detail: { code: "botanical_profile_not_found" } }, 404);
    if (
      path === `/api/v1/botanical-identities/${identity.id}/external-taxon-link`
    )
      return json({ detail: { code: "external_taxon_link_not_found" } }, 404);
    throw new Error(`Unexpected request: ${path}`);
  });
  render(<App />);

  expect(await screen.findByRole("tab", { name: "Reference" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(
    screen.getByRole("heading", {
      name: "Botanical profile",
      level: 3,
    }),
  ).toBeInTheDocument();
  expect(requested).not.toContain(
    `/api/v1/botanical-identities/${identity.id}/cover-image`,
  );
  expect(document.querySelector(".identity-work-header")).toBeInTheDocument();
  expect(document.querySelector(".identity-summary")).not.toBeInTheDocument();
  expect(requested).not.toContain(
    `/api/v1/botanical-identities/${identity.id}/collection`,
  );
});

test("Botanical identity empty states require a SeedLot before Sowing and preserve direct Plant entry", async () => {
  window.history.replaceState(
    null,
    "",
    `#/identities/${identity.id}?tab=sowings`,
  );
  mockAuthenticated((path) => {
    if (path === "/api/v1/botanical-identities") return json([identity]);
    if (path === `/api/v1/botanical-identities/${identity.id}/collection`)
      return json({
        identity,
        seed_lots: [],
        sowings: [],
        plants: [],
        plant_groups: [],
        harvests: [],
        events: [],
      });
    if (path === `/api/v1/botanical-identities/${identity.id}/profile`)
      return json({ detail: "not needed" }, 404);
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<App />);

  await user.click(
    await screen.findByRole("button", { name: "Add to collection" }),
  );
  await user.click(screen.getByRole("button", { name: "Start sowing" }));
  expect(
    await screen.findByText(/No active seed lots are recorded/),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Create seed lot" })).toHaveAttribute(
    "href",
    `#/seeds?action=create&identity=${identity.id}`,
  );
  await user.click(screen.getByRole("button", { name: "Cancel" }));

  expect(
    await screen.findByRole("link", { name: /Sowings: 0 recorded, 0 active/ }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Add to collection" }));
  expect(screen.getByRole("link", { name: "Add plant" })).toHaveAttribute(
    "href",
    `#/plants?action=create&identity=${identity.id}&kind=plant`,
  );
});

test("Botanical identity edit and guarded deletion stay explicit", async () => {
  window.history.replaceState(null, "", `#/identities/${identity.id}`);
  let current: typeof identity | null = identity;
  let referenced = true;
  mockAuthenticated((path, init) => {
    if (path === "/api/v1/botanical-identities")
      return json(current ? [current] : []);
    if (path === `/api/v1/botanical-identities/${identity.id}/collection`)
      return json({
        identity: current ?? identity,
        seed_lots: [],
        sowings: [],
        plants: [],
        plant_groups: [],
        harvests: [],
        events: [],
      });
    if (path === `/api/v1/botanical-identities/${identity.id}/profile`)
      return json(
        {
          detail: {
            code: "botanical_profile_not_found",
            message: "Botanical profile not found",
          },
        },
        404,
      );
    if (
      path === `/api/v1/botanical-identities/${identity.id}` &&
      init?.method === "PUT"
    ) {
      current = { ...identity, common_name: "Japanese laceleaf maple" };
      return json(current);
    }
    if (
      path === `/api/v1/botanical-identities/${identity.id}` &&
      init?.method === "DELETE"
    ) {
      if (referenced)
        return json({ detail: { code: "botanical_identity_referenced" } }, 409);
      current = null;
      return new Response(null, { status: 204 });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: identity.display_label });

  await user.click(
    screen.getByRole("button", { name: "Edit botanical identity" }),
  );
  await user.clear(screen.getByLabelText("Common name"));
  await user.type(
    screen.getByLabelText("Common name"),
    "Japanese laceleaf maple",
  );
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findAllByText("Japanese laceleaf maple")).toHaveLength(1);

  await user.click(screen.getByRole("button", { name: "Close editor" }));
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Edit botanical identity" }),
    ).not.toBeInTheDocument();
  });
  await user.click(
    screen.getByRole("button", { name: "Delete botanical identity" }),
  );
  expect(screen.getByRole("dialog")).toHaveTextContent(
    "Collection records are never cascaded",
  );
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Delete botanical identity",
    }),
  );
  expect(
    await screen.findByText(
      "This botanical identity has collection records, a cover image, or retained native-range source evidence and cannot be deleted.",
    ),
  ).toHaveAttribute("role", "alert");

  referenced = false;
  await user.click(
    screen.getByRole("button", { name: "Delete botanical identity" }),
  );
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Delete botanical identity",
    }),
  );
  expect(
    await screen.findByRole("heading", { name: "Select a botanical identity" }),
  ).toBeInTheDocument();
});
