import { listBotanicalIdentities } from "../botanical-identities/api";
import { formatPartialDate } from "../events/eventData";
import { materials } from "../harvests/api";
import { inventoryList, remainingLabel } from "../harvests/inventoryApi";
import { listPlantGroups, listPlants } from "../plants/api";
import { listSeedLots } from "../seed-lots/api";

export const labelKinds = [
  "seed-lot",
  "plant",
  "plant-group",
  "stored-material",
] as const;
export type LabelKind = (typeof labelKinds)[number];
export const labelTypeNames: Record<LabelKind, string> = {
  "seed-lot": "Seed lot",
  plant: "Plant",
  "plant-group": "Plant group",
  "stored-material": "Stored material",
};
const routes = {
  "seed-lot": "seeds",
  plant: "plants",
  "plant-group": "plant-groups",
};
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export interface LabelRecord {
  kind: LabelKind;
  id: string;
  botanicalName: string;
  cultivar: string | null;
  commonName: string | null;
  context: string | null;
  metadata: string[];
  // Stored material is a specific inventory record within its source Harvest.
  harvestId?: string;
}
export interface LabelEntry {
  record: LabelRecord;
  copies: number;
}
export function isLabelKind(value: unknown): value is LabelKind {
  return labelKinds.some((kind) => kind === value);
}
export function sourceHref(
  record: Pick<LabelRecord, "kind" | "id" | "harvestId">,
): string {
  if (!isLabelKind(record.kind) || !uuid.test(record.id))
    throw new Error("Invalid label source.");
  if (record.kind === "stored-material") {
    if (!record.harvestId || !uuid.test(record.harvestId))
      throw new Error("Invalid source Harvest.");
    return `#/harvests/${record.harvestId}?inventory=${record.id}`;
  }
  return `#/${routes[record.kind]}/${record.id}`;
}
// QR and source links share the existing authenticated frontend routes.
export function recordUrl(
  kind: LabelKind,
  id: string,
  canonicalOrigin: string | null,
  harvestId?: string,
): string {
  const href = sourceHref({ kind, id, harvestId });
  if (!canonicalOrigin)
    throw new Error("Florabase has no canonical public address configured.");
  const normalized = canonicalOrigin.trim();
  if (
    !/^https?:\/\/[^/?#\\\s@]+\/?$/i.test(normalized) ||
    normalized.length > 200
  )
    throw new Error("Florabase canonical address is invalid.");
  const parsed = new URL(normalized);
  if (
    parsed.username ||
    parsed.password ||
    !["", "/"].includes(parsed.pathname)
  )
    throw new Error("Florabase canonical address is invalid.");
  return `${parsed.origin}/${href}`;
}
export function labelComposerHref(kind: LabelKind, id: string): string {
  return `#/labels?kind=${kind}&record=${encodeURIComponent(id)}`;
}
export function labelKey(record: LabelRecord): string {
  return `${record.kind}:${record.id}`;
}

function nonBlank(value: string | null | undefined): string | null {
  const text = value?.trim();
  if (text === undefined || text === "") return null;
  return text;
}

export async function listLabelRecords(
  kind: LabelKind,
  signal: AbortSignal,
): Promise<LabelRecord[]> {
  if (!isLabelKind(kind)) throw new Error("Unsupported label target.");
  // One identity request per chooser load; structured scientific/cultivar fields avoid parsing display text.
  const identitiesPromise = listBotanicalIdentities(signal);
  const recordsPromise =
    kind === "stored-material"
      ? inventoryList(signal)
      : kind === "seed-lot"
        ? listSeedLots(signal)
        : kind === "plant"
          ? listPlants(signal)
          : listPlantGroups(signal);
  const [identities, records] = await Promise.all([
    identitiesPromise,
    recordsPromise,
  ]);
  const identitiesById = new Map(
    identities.map((identity) => [identity.id, identity]),
  );
  return records.map((record) => {
    const summary =
      "source" in record
        ? record.source.botanical_identity
        : record.botanical_identity;
    const identity = identitiesById.get(summary.id);
    const base: LabelRecord = {
      kind,
      id: record.id,
      botanicalName:
        nonBlank(identity?.scientific_name) ??
        nonBlank(summary.display_label) ??
        "Botanical identity unavailable",
      cultivar: nonBlank(identity?.cultivar_name),
      commonName: nonBlank(identity?.common_name),
      context:
        "harvest_title" in record
          ? record.harvest_title
          : nonBlank(record.label),
      metadata: [],
    };
    if ("harvest_item_id" in record) {
      base.harvestId = record.harvest_id;
      base.metadata = [
        `${materials.find((item) => item.id === record.material_kind)?.label ?? record.material_kind} · ${remainingLabel(record)}`,
        `Source: ${nonBlank(record.source.label) ?? (record.source.type === "plant_group" ? "Plant group" : "Plant")}`,
      ];
    } else if ("acquisition_date" in record) {
      const q = record.quantity;
      const acquisition = record.acquisition_date
        ? `Acquired: ${formatPartialDate(record.acquisition_date)}`
        : null;
      const quantity = q
        ? `${q.is_approximate ? "About " : ""}${q.value} ${q.kind === "seed_count" ? "seeds" : (q.unit ?? "unit not recorded")}`
        : null;
      const stock = [acquisition, quantity]
        .filter((value): value is string => value !== null)
        .join(" · ");
      base.metadata = [
        stock,
        record.supplier ? `Supplier: ${record.supplier.name}` : null,
      ].filter((value): value is string => value !== null && value !== "");
    } else if ("quantity" in record) {
      const q = record.quantity;
      base.metadata = q
        ? [`${q.is_approximate ? "About " : ""}${String(q.value)} plants`]
        : [];
    } else {
      const source =
        record.originating_plant_group ?? record.originating_sowing;
      base.metadata = source
        ? [
            `From: ${nonBlank(source.label) ?? (record.originating_plant_group ? "Plant group" : "Sowing")}`,
          ]
        : [];
    }
    if (record.location?.display_path)
      base.metadata.push(`Location: ${record.location.display_path}`);
    return base;
  });
}
export const labelPresets = {
  small: {
    id: "small",
    title: "40 × 20 mm — Small",
    columns: 5,
    rows: 13,
    widthMm: 40,
    heightMm: 20,
    marginX: 5,
    marginY: 18.5,
    qrMm: 16,
  },
  medium: {
    id: "medium",
    title: "50 × 30 mm — Medium",
    columns: 4,
    rows: 9,
    widthMm: 50,
    heightMm: 30,
    marginX: 5,
    marginY: 13.5,
    qrMm: 24,
  },
  large: {
    id: "large",
    title: "70 × 40 mm — Large",
    columns: 2,
    rows: 7,
    widthMm: 70,
    heightMm: 40,
    marginX: 35,
    marginY: 8.5,
    qrMm: 32,
  },
} as const;
export type LabelPresetId = keyof typeof labelPresets;
export type LabelPreset = (typeof labelPresets)[LabelPresetId];
export function isLabelPreset(value: unknown): value is LabelPresetId {
  return value === "small" || value === "medium" || value === "large";
}
export const labelPreset = labelPresets.medium;
export const labelsPerPage = labelPreset.columns * labelPreset.rows;
export const maxLabels = 360;
export function pickerLabel(record: LabelRecord): string {
  return [
    record.botanicalName + (record.cultivar ? ` ‘${record.cultivar}’` : ""),
    record.context ?? labelTypeNames[record.kind],
  ].join(" · ");
}
export function pickerDescription(record: LabelRecord): string {
  return [labelTypeNames[record.kind], record.commonName, ...record.metadata]
    .filter(Boolean)
    .join(" · ");
}
export function composePages(
  entries: LabelEntry[],
  preset: LabelPreset = labelPreset,
): LabelRecord[][] {
  const total = entries.reduce((sum, { copies }) => {
    if (!Number.isInteger(copies) || copies < 1 || copies > maxLabels)
      throw new Error("Copies must be a whole number from 1 to 360.");
    return sum + copies;
  }, 0);
  if (total > maxLabels) throw new Error("A batch holds at most 360 labels.");
  const perPage = preset.columns * preset.rows;
  const labels = entries.flatMap(({ record, copies }) =>
    Array.from({ length: copies }, () => record),
  );
  return Array.from({ length: Math.ceil(total / perPage) }, (_, page) =>
    labels.slice(page * perPage, (page + 1) * perPage),
  );
}
