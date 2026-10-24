import { expect, test } from "vitest";
import type { ProvenanceMapSite } from "../provenance-map/api";
import { identityOriginSites } from "./identityGeography";
test("identity origins exclude unrelated and unlinked sites and recalculate shared-site usage", () => {
  const site: ProvenanceMapSite = {
    id: "shared",
    name: "Shared origin",
    latitude: "45",
    longitude: "9",
    coordinate_accuracy_m: "1000",
    geographic_place_id: null,
    geographic_place_path: null,
    usage: { seed_lots: 2, plants: 1, plant_groups: 0, total: 3 },
    records: [
      {
        id: "ours",
        record_type: "seed_lot",
        label: "Packet",
        is_active: false,
        lifecycle: "exhausted",
        botanical_identity: {
          id: "identity",
          display_label: "Salvia officinalis",
        },
      },
      {
        id: "other",
        record_type: "plant",
        label: "Other plant",
        is_active: true,
        lifecycle: "alive",
        botanical_identity: { id: "other", display_label: "Another identity" },
      },
    ],
  };
  const result = identityOriginSites(
    [site, { ...site, id: "unlinked", records: [] }],
    "identity",
  );
  expect(result).toHaveLength(1);
  expect(result[0].records.map((r) => r.id)).toEqual(["ours"]);
  expect(result[0].usage).toEqual({
    seed_lots: 1,
    plants: 0,
    plant_groups: 0,
    total: 1,
  });
  expect(result[0].coordinate_accuracy_m).toBe("1000");
  expect(site.records).toHaveLength(2);
  expect(identityOriginSites([site], "missing")).toEqual([]);
});
