import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "../App";
import type { EventResponse } from "../collection/api";
import "./BotanicalIdentityScreen";

const activeIdentity = {
  id: "01900000-0000-7000-8000-000000000701",
  scientific_name: "Coffea arabica",
  cultivar_name: null,
  common_name: "Arabica coffee",
  display_label: "Coffea arabica",
  synonyms: [],
  collection_counts: {
    seed_lots: 1,
    sowings: 1,
    plants: 1,
    plant_groups: 1,
  },
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

const historyEvents: EventResponse[] = [
  {
    id: "01900000-0000-7000-8000-000000000801",
    kind: "harvest",
    occurred_on: { precision: "day", year: 2026, month: 11, day: 2 },
    notes: "Ripe red cherries collected from lower branches.",
    target: {
      type: "plant",
      id: "01900000-0000-7000-8000-000000000301",
      label: "Courtyard coffee",
      lifecycle: "active",
      botanical_identity: {
        id: activeIdentity.id,
        display_label: activeIdentity.display_label,
      },
    },
    destination_location_id: null,
    destination_location: null,
    recipient: null,
    resulting_plant_id: null,
    resulting_plant: null,
    harvest_id: "01900000-0000-7000-8000-000000000901",
    harvest_title: "Coffea arabica — Fruit harvest",
    measurement_corrections: [],
    created_at: "2026-11-02T12:00:00Z",
    updated_at: "2026-11-02T12:00:00Z",
  },
  {
    id: "01900000-0000-7000-8000-000000000802",
    kind: "observation",
    occurred_on: { precision: "month", year: 2026, month: 10 },
    notes: "Green fruit swelling after autumn rain.",
    target: {
      type: "plant",
      id: "01900000-0000-7000-8000-000000000301",
      label: "Courtyard coffee",
      lifecycle: "active",
      botanical_identity: {
        id: activeIdentity.id,
        display_label: activeIdentity.display_label,
      },
    },
    destination_location_id: null,
    destination_location: null,
    recipient: null,
    resulting_plant_id: null,
    resulting_plant: null,
    measurement_corrections: [],
    created_at: "2026-10-15T09:00:00Z",
    updated_at: "2026-10-15T09:00:00Z",
  },
  {
    id: "01900000-0000-7000-8000-000000000803",
    kind: "repotting",
    occurred_on: { precision: "year", year: 2025 },
    notes: "Potted up the seedling bench cohort.",
    target: {
      type: "plant_group",
      id: "01900000-0000-7000-8000-000000000401",
      label: "Bench cohort",
      lifecycle: "active",
      botanical_identity: {
        id: activeIdentity.id,
        display_label: activeIdentity.display_label,
      },
    },
    destination_location_id: null,
    destination_location: null,
    recipient: null,
    resulting_plant_id: null,
    resulting_plant: null,
    measurement_corrections: [],
    created_at: "2025-05-01T09:00:00Z",
    updated_at: "2025-05-01T09:00:00Z",
  },
];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockHistoryFetch(events: EventResponse[]) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
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
      return Promise.resolve(json({ csrf_token: "csrf-token" }));
    if (path.endsWith("/health"))
      return Promise.resolve(json({ status: "ok" }));
    if (path === "/api/v1/saved-views?surface=botanical_identities")
      return Promise.resolve(json([]));
    if (path === "/api/v1/botanical-identities")
      return Promise.resolve(json([activeIdentity]));
    if (path === `/api/v1/botanical-identities/${activeIdentity.id}/collection`)
      return Promise.resolve(
        json({
          identity: activeIdentity,
          seed_lots: [],
          sowings: [],
          plants: [],
          plant_groups: [],
          harvests: [],
          events,
        }),
      );
    if (path === `/api/v1/botanical-identities/${activeIdentity.id}/profile`)
      return Promise.resolve(
        json({ detail: { code: "botanical_profile_not_found" } }, 404),
      );
    if (
      path ===
      `/api/v1/botanical-identities/${activeIdentity.id}/profile/native-ranges`
    )
      return Promise.resolve(json([]));
    if (
      path ===
      `/api/v1/botanical-identities/${activeIdentity.id}/external-taxon-link`
    )
      return Promise.resolve(json(null));
    if (path === `/api/v1/botanical-identities/${activeIdentity.id}/taxonomy`)
      return Promise.resolve(json(null));
    if (path === "/api/v1/provenance-sites") return Promise.resolve(json([]));
    return Promise.resolve(json({}));
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.history.replaceState(null, "", "#/");
});

test("identity History lists linked recorded events once, newest first, with Harvest links, precision and documented gaps", async () => {
  mockHistoryFetch(historyEvents);
  window.history.replaceState(
    null,
    "",
    `#/identities/${activeIdentity.id}?tab=history`,
  );
  const view = render(<App />);
  await vi.dynamicImportSettled();

  const panel = await screen.findByRole("tabpanel", { name: "History" });
  expect(
    within(panel).getByRole("heading", { name: "Recorded history", level: 3 }),
  ).toBeVisible();
  expect(
    within(panel).getByText(
      /Sowing and germination records remain in their source directories\. This view does not infer earlier lifecycle facts from current state or include planned work\./,
    ),
  ).toBeVisible();
  expect(
    within(panel).getByRole("link", { name: "View all Sowings" }),
  ).toHaveAttribute(
    "href",
    `#/sowings?identity_id=${activeIdentity.id}&lifecycle=all`,
  );
  expect(
    within(panel).getByRole("link", { name: "View all Harvests" }),
  ).toHaveAttribute("href", `#/harvests?identity_id=${activeIdentity.id}`);

  const rows = within(panel).getAllByRole("listitem");
  expect(rows).toHaveLength(3);
  expect(rows.map((row) => row.querySelector("time")?.textContent)).toEqual([
    "2026-11-02",
    "2026-10",
    "2025",
  ]);

  const harvestLinks = within(panel).getAllByRole("link", {
    name: /Harvest: Coffea arabica — Fruit harvest/,
  });
  expect(harvestLinks).toHaveLength(1);
  expect(harvestLinks[0]).toHaveAttribute(
    "href",
    "#/harvests/01900000-0000-7000-8000-000000000901",
  );
  expect(
    within(rows[0]).getByRole("link", { name: "Courtyard coffee" }),
  ).toHaveAttribute(
    "href",
    "#/plants/01900000-0000-7000-8000-000000000301?tab=events",
  );
  expect(
    within(rows[2]).getByRole("link", { name: "Bench cohort" }),
  ).toHaveAttribute(
    "href",
    "#/plant-groups/01900000-0000-7000-8000-000000000401?tab=events",
  );
  expect(
    within(panel).queryByRole("link", { name: activeIdentity.display_label }),
  ).toBeNull();

  view.unmount();
  vi.restoreAllMocks();
  mockHistoryFetch([]);
  window.history.replaceState(
    null,
    "",
    `#/identities/${activeIdentity.id}?tab=history`,
  );
  render(<App />);
  await vi.dynamicImportSettled();

  const emptyPanel = await screen.findByRole("tabpanel", { name: "History" });
  expect(
    within(emptyPanel).getByText(
      "No events belong to plants or plant groups with this identity.",
    ),
  ).toBeVisible();
  expect(within(emptyPanel).queryByRole("listitem")).toBeNull();
});
