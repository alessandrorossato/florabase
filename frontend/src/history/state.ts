import type { components } from "../api/schema";

export type Category = components["schemas"]["HistoryCategory"];
export type SubjectKind = components["schemas"]["HistorySubjectKind"];
export interface HistoryState {
  category: Category[];
  subject_kind: SubjectKind | "";
  year: string;
}
export const categories: Category[] = [
  "event",
  "propagation",
  "germination",
  "harvest",
  "material",
];
export const categoryLabels: Record<Category, string> = {
  event: "Events",
  propagation: "Propagation",
  germination: "Germination",
  harvest: "Harvests",
  material: "Stored material",
};
export const subjectLabels: Record<SubjectKind, string> = {
  plant: "Plant",
  plant_group: "Plant group",
  sowing: "Sowing",
  harvest: "Harvest",
  harvest_inventory: "Stored material",
  seed_lot: "Seed lot",
};
const validYear = (value: unknown): value is number =>
  typeof value === "number" &&
  Number.isInteger(value) &&
  value >= 1 &&
  value <= 9999;
export function parseHistoryState(
  input: Record<string, unknown>,
  strict = true,
): HistoryState | null {
  if (
    strict &&
    Object.keys(input).some(
      (key) => !["category", "subject_kind", "year"].includes(key),
    )
  )
    return null;
  const category = input.category === undefined ? [] : input.category;
  const subject = input.subject_kind ?? "";
  const year = input.year ?? undefined;
  if (
    strict &&
    (!Array.isArray(category) ||
      category.length > 5 ||
      category.some((value) => !categories.includes(value as Category)) ||
      (subject !== "" &&
        !(
          typeof subject === "string" && Object.hasOwn(subjectLabels, subject)
        )) ||
      (year !== undefined && !validYear(year)))
  )
    return null;
  return {
    category: categories.filter(
      (item) => Array.isArray(category) && category.includes(item),
    ),
    subject_kind:
      typeof subject === "string" && Object.hasOwn(subjectLabels, subject)
        ? (subject as SubjectKind)
        : "",
    year: validYear(year) ? String(year) : "",
  };
}
export function readHistoryState(hash = window.location.hash): HistoryState {
  const [path, query = ""] = hash.split("?", 2);
  const params = new URLSearchParams(path === "#/history" ? query : "");
  const year = params.get("year");
  return (
    parseHistoryState(
      {
        category: params.getAll("category"),
        subject_kind: params.get("subject_kind") ?? "",
        ...(year && /^\d{1,4}$/.test(year) ? { year: Number(year) } : {}),
      },
      false,
    ) ?? { category: [], subject_kind: "", year: "" }
  );
}
export function saveHistoryState(
  state: HistoryState,
): Record<string, string | number | Category[]> {
  return {
    ...(state.category.length
      ? { category: categories.filter((c) => state.category.includes(c)) }
      : {}),
    ...(state.subject_kind ? { subject_kind: state.subject_kind } : {}),
    ...(state.year ? { year: Number(state.year) } : {}),
  };
}
export function historyParams(state: HistoryState): URLSearchParams {
  const params = new URLSearchParams();
  for (const category of categories.filter((c) => state.category.includes(c)))
    params.append("category", category);
  if (state.subject_kind) params.set("subject_kind", state.subject_kind);
  if (state.year) params.set("year", state.year);
  return params;
}
export function historyHash(state: HistoryState): string {
  const params = historyParams(state);
  return `#/history${params.size ? `?${params}` : ""}`;
}
