import { expect, test } from "vitest";

import { locationsForScope, type LocationResponse } from "./api";

function location(
  name: string,
  usageScopes: LocationResponse["usage_scopes"],
): LocationResponse {
  return {
    id: `01900000-0000-7000-8000-00000000030${String(name.length)}`,
    name,
    parent_id: null,
    display_path: `Home → ${name}`,
    usage_scopes: usageScopes,
    usage: {
      plants: { active: 0, total: 0 },
      sowings: { active: 0, total: 0 },
      seed_lots: { active: 0, total: 0 },
    },
    retired_at: null,
    created_at: "2026-09-07T10:00:00Z",
    updated_at: "2026-09-07T10:00:00Z",
  };
}

test("assignment selectors retain path labels and expose only their authoritative scope", () => {
  const plants = location("Greenhouse", ["plants"]);
  const sowings = location("Propagation bench", ["sowings"]);
  const seeds = location("Seed cabinet", ["seed_lots"]);
  const shared = location("Indoor shelf", ["plants", "sowings", "seed_lots"]);
  const locations = [plants, sowings, seeds, shared];

  expect(locationsForScope(locations, "plants")).toEqual([plants, shared]);
  expect(locationsForScope(locations, "sowings")).toEqual([sowings, shared]);
  expect(locationsForScope(locations, "seed_lots")).toEqual([seeds, shared]);
  expect(locationsForScope(locations, "seed_lots")[0]?.display_path).toBe(
    "Home → Seed cabinet",
  );
});
