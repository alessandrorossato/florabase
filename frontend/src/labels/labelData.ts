import { listPlantGroups, listPlants } from "../plants/api";
import { listSeedLots } from "../seed-lots/api";

export const labelKinds = ["seed-lot", "plant", "plant-group"] as const;
export type LabelKind = (typeof labelKinds)[number];
export const labelTypeNames: Record<LabelKind, string> = {
  "seed-lot": "Seed lot",
  plant: "Plant",
  "plant-group": "Plant group",
};
const routes: Record<LabelKind, string> = {
  "seed-lot": "seeds",
  plant: "plants",
  "plant-group": "plant-groups",
};
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface LabelRecord {
  kind: LabelKind;
  id: string;
  botanicalName: string;
  context: string | null;
}
export interface LabelEntry {
  record: LabelRecord;
  copies: number;
}

export function isLabelKind(value: unknown): value is LabelKind {
  return labelKinds.some((kind) => kind === value);
}

export function recordUrl(
  kind: LabelKind,
  id: string,
  canonicalOrigin: string | null,
): string {
  if (!isLabelKind(kind) || !uuid.test(id))
    throw new Error("Choose a supported collection record with a valid UUID.");
  if (!canonicalOrigin)
    throw new Error("Florabase has no canonical public address configured.");
  let parsed: URL;
  try {
    parsed = new URL(canonicalOrigin);
  } catch {
    throw new Error("Florabase canonical address is invalid.");
  }
  if (
    !["http:", "https:"].includes(parsed.protocol) ||
    parsed.username !== "" ||
    parsed.password !== "" ||
    !["", "/"].includes(parsed.pathname) ||
    parsed.search !== "" ||
    parsed.hash !== ""
  )
    throw new Error("Florabase canonical address is invalid.");
  // Use the backend-configured public origin, never a proxy or browser Host alias.
  return `${canonicalOrigin.replace(/\/$/, "")}/#/${routes[kind]}/${id}`;
}

export function labelComposerHref(kind: LabelKind, id: string): string {
  return `#/labels?kind=${kind}&record=${encodeURIComponent(id)}`;
}

export function labelKey(record: LabelRecord): string {
  return `${record.kind}:${record.id}`;
}

export async function listLabelRecords(
  kind: LabelKind,
  signal: AbortSignal,
): Promise<LabelRecord[]> {
  if (!isLabelKind(kind)) throw new Error("Unsupported label target.");
  const records =
    kind === "seed-lot"
      ? await listSeedLots(signal)
      : kind === "plant"
        ? await listPlants(signal)
        : await listPlantGroups(signal);
  return records.map((record) => {
    const name = record.botanical_identity.display_label.trim();
    const context = record.label?.trim();
    return {
      kind,
      id: record.id,
      botanicalName: name === "" ? "Botanical identity unavailable" : name,
      context: context === "" ? null : (context ?? null),
    };
  });
}

export const labelsPerPage = 36;

export function composePages(entries: LabelEntry[]): LabelRecord[][] {
  const labels = entries.flatMap(({ record, copies }) => {
    if (!Number.isInteger(copies) || copies < 1 || copies > labelsPerPage)
      throw new Error("Copies must be a whole number from 1 to 36.");
    return Array.from({ length: copies }, () => record);
  });
  if (labels.length > labelsPerPage)
    throw new Error("An A4 sheet holds at most 36 labels.");
  return labels.length ? [labels] : [];
}
