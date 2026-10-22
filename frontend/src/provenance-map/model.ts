import type { ProvenanceMapRecord, ProvenanceMapSite } from "./api";

export function recordKey(record: ProvenanceMapRecord): string {
  return `${record.record_type}:${record.id}`;
}
export function recordTypeLabel(record: ProvenanceMapRecord): string {
  return record.record_type === "seed_lot"
    ? "SeedLot"
    : record.record_type === "plant_group"
      ? "PlantGroup"
      : "Plant";
}
export function recordHref(record: ProvenanceMapRecord): string {
  const route =
    record.record_type === "seed_lot"
      ? "seeds"
      : record.record_type === "plant_group"
        ? "plant-groups"
        : "plants";
  return `#/${route}/${record.id}`;
}
export function uniqueRecords(
  sites: ProvenanceMapSite[],
): ProvenanceMapRecord[] {
  return [
    ...new Map(
      sites
        .flatMap((site) => site.records)
        .map((record) => [recordKey(record), record]),
    ).values(),
  ];
}
export function identityGroups(records: ProvenanceMapRecord[]) {
  const groups = new Map<
    string,
    {
      identity: ProvenanceMapRecord["botanical_identity"];
      records: ProvenanceMapRecord[];
    }
  >();
  for (const record of records) {
    const id = record.botanical_identity.id;
    const group = groups.get(id) ?? {
      identity: record.botanical_identity,
      records: [],
    };
    group.records.push(record);
    groups.set(id, group);
  }
  return [...groups.values()].sort((a, b) =>
    a.identity.display_label.localeCompare(b.identity.display_label),
  );
}
