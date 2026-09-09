import type { ProvenanceMapRecord, ProvenanceMapSite } from "./api";

export interface MapFilters {
  seedLots: boolean;
  plants: boolean;
  identityQuery: string;
}

function recordMatches(
  record: ProvenanceMapRecord,
  filters: MapFilters,
): boolean {
  const typeMatches =
    (record.record_type === "seed_lot" && filters.seedLots) ||
    (record.record_type !== "seed_lot" && filters.plants);
  const query = filters.identityQuery.trim().toLocaleLowerCase();
  return (
    typeMatches &&
    (!query ||
      record.botanical_identity.display_label
        .toLocaleLowerCase()
        .includes(query))
  );
}

export function filterMapSites(
  sites: ProvenanceMapSite[],
  filters: MapFilters,
): ProvenanceMapSite[] {
  return sites.flatMap((site) => {
    const records = site.records.filter((record) =>
      recordMatches(record, filters),
    );
    if (records.length === 0) return [];
    const seedLots = records.filter(
      ({ record_type }) => record_type === "seed_lot",
    ).length;
    const plants = records.filter(
      ({ record_type }) => record_type === "plant",
    ).length;
    const plantGroups = records.filter(
      ({ record_type }) => record_type === "plant_group",
    ).length;
    return [
      {
        ...site,
        records,
        usage: {
          seed_lots: seedLots,
          plants,
          plant_groups: plantGroups,
          total: records.length,
        },
      },
    ];
  });
}
