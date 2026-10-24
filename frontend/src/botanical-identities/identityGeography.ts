import type { ProvenanceMapSite } from "../provenance-map/api";

/** Exact current identity membership; no inherited provenance or storage-location inference. */
export function identityOriginSites(
  sites: ProvenanceMapSite[],
  id: string,
): ProvenanceMapSite[] {
  return sites.flatMap((site) => {
    const records = site.records.filter(
      (record) => record.botanical_identity.id === id,
    );
    return records.length
      ? [
          {
            ...site,
            records,
            usage: {
              seed_lots: records.filter((r) => r.record_type === "seed_lot")
                .length,
              plants: records.filter((r) => r.record_type === "plant").length,
              plant_groups: records.filter(
                (r) => r.record_type === "plant_group",
              ).length,
              total: records.length,
            },
          },
        ]
      : [];
  });
}
