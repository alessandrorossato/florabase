import { cleanup, render, screen, within } from "@testing-library/react";
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
    if (path === "/api/v1/dashboard")
      return json({
        counts: {
          active_plants: 12,
          active_plant_groups: 3,
          active_seed_lots: 8,
          active_sowings: 4,
          botanical_identities: 9,
          events: 27,
        },
        recent_events: [event],
      });
    if (path === "/api/v1/events") return json([event]);
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Dashboard" }),
  ).toBeInTheDocument();
  expect(await screen.findByLabelText("Collection totals")).toHaveTextContent(
    "Active12PlantsActive3Plant groupsActive8Seed lotsActive4SowingsBotany9Botanical identitiesHistory27Events",
  );
  expect(screen.getByText("Strong new growth.")).toBeInTheDocument();

  const desktop = screen.getByRole("navigation", {
    name: "Primary navigation",
  });
  for (const group of ["Overview", "Collection", "Botany", "Reference"])
    expect(
      within(desktop).getByRole("region", { name: group }),
    ).toBeInTheDocument();
  const mobile = screen.getByRole("navigation", {
    name: "Mobile primary navigation",
  });
  expect(mobile.querySelectorAll("a, button")).toHaveLength(5);
  const plantGroupCard = screen.getByText("Plant groups").closest("article");
  if (!plantGroupCard) throw new Error("Plant groups summary card is missing");
  expect(within(plantGroupCard).getByRole("link")).toHaveAttribute(
    "href",
    "#/plants?type=group",
  );
  await user.click(within(mobile).getByRole("button", { name: "More" }));
  expect(
    screen.getByRole("navigation", { name: "More navigation" }),
  ).toBeInTheDocument();
  await user.click(within(mobile).getByRole("link", { name: "Home" }));
  expect(
    screen.queryByRole("navigation", { name: "More navigation" }),
  ).not.toBeInTheDocument();

  await user.click(within(desktop).getByRole("button", { name: "Events" }));
  expect(
    await screen.findByRole("heading", { name: "Events" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Courtyard maple" })).toHaveAttribute(
    "href",
    `#/plants/${event.target.id}?tab=events`,
  );
  await user.click(screen.getByRole("button", { name: "Status" }));
  expect(screen.getByRole("status")).toHaveTextContent(
    "No Events match this filter.",
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

  expect(
    await screen.findByRole("heading", { name: identity.display_label }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("navigation", { name: "Breadcrumb" }),
  ).toContainElement(
    screen.getByRole("link", { name: "Botanical identities" }),
  );
  expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(
    screen.getByText(/does not create or imply lineage/i),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Edit botanical identity" }),
  ).toBeInTheDocument();
  expect(
    screen.getByLabelText("More botanical identity actions"),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("tab", { name: "Seeds" }));
  expect(window.location.hash).toBe(`#/identities/${identity.id}?tab=seeds`);
  expect(
    screen.getByRole("link", { name: /Bloodgood seed lot/ }),
  ).toHaveAttribute("href", "#/seeds/seed-1");
  expect(screen.getByRole("link", { name: "Add SeedLot" })).toHaveAttribute(
    "href",
    `#/seeds?action=create&identity=${identity.id}`,
  );

  await user.keyboard("{ArrowRight}");
  expect(screen.getByRole("tab", { name: "Sowings" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(screen.getByRole("link", { name: /Autumn tray/ })).toHaveAttribute(
    "href",
    "#/sowings/sowing-1",
  );
  expect(
    screen.getByRole("link", { name: "Start from this SeedLot" }),
  ).toHaveAttribute("href", "#/sowings?action=start&seedLot=seed-1");

  await user.click(screen.getByRole("tab", { name: "Plants" }));
  expect(screen.getByRole("link", { name: /Courtyard maple/ })).toHaveAttribute(
    "href",
    "#/plants/plant-1",
  );
  expect(screen.getByRole("link", { name: /Maple seedlings/ })).toHaveAttribute(
    "href",
    "#/plant-groups/group-1",
  );
  expect(screen.getByText("Plant group")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Direct / acquired Plant" }),
  ).toHaveAttribute(
    "href",
    `#/plants?action=create&identity=${identity.id}&kind=plant`,
  );
  expect(screen.getByRole("link", { name: "Create Plant" })).toHaveAttribute(
    "href",
    "#/plants?action=from-sowing&sowing=sowing-1&kind=plant",
  );

  await user.click(screen.getByRole("tab", { name: "Events" }));
  expect(screen.getByText("Strong new growth.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Courtyard maple" })).toHaveAttribute(
    "href",
    `#/plants/${event.target.id}?tab=events`,
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
        events: [],
      });
    if (path === `/api/v1/botanical-identities/${identity.id}/profile`)
      return json({ detail: "not needed" }, 404);
    throw new Error(`Unexpected request: ${path}`);
  });
  render(<App />);

  expect(await screen.findByRole("tab", { name: "Events" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(
    await screen.findByText(
      "No Events belong to Plants or Plant groups with this identity.",
    ),
  ).toBeInTheDocument();
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
        events: [],
      });
    if (path === `/api/v1/botanical-identities/${identity.id}/profile`)
      return json({ detail: "not needed" }, 404);
    throw new Error(`Unexpected request: ${path}`);
  });
  const user = userEvent.setup();
  render(<App />);

  expect(
    await screen.findByText(/cannot exist without its source SeedLot/),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Create SeedLot" })).toHaveAttribute(
    "href",
    `#/seeds?action=create&identity=${identity.id}`,
  );
  await user.click(screen.getByRole("tab", { name: "Plants" }));
  expect(
    screen.getByRole("heading", { name: "From a Sowing" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/No source Sowings are recorded yet/),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Direct / acquired Plant" }),
  ).toHaveAttribute(
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
  expect(await screen.findAllByText("Japanese laceleaf maple")).toHaveLength(3);

  await user.click(screen.getByLabelText("More botanical identity actions"));
  await user.click(screen.getByRole("button", { name: "Delete" }));
  expect(screen.getByRole("dialog")).toHaveTextContent(
    "Collection records are never cascaded",
  );
  await user.click(
    screen.getByRole("button", { name: "Delete botanical identity" }),
  );
  expect(
    await screen.findByText(
      "This botanical identity is used by collection records and cannot be deleted.",
    ),
  ).toHaveAttribute("role", "alert");

  referenced = false;
  await user.click(screen.getByRole("button", { name: "Delete" }));
  await user.click(
    screen.getByRole("button", { name: "Delete botanical identity" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Select a botanical identity" }),
  ).toBeInTheDocument();
});
