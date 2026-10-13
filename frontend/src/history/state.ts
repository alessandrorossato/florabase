import type { components } from "../api/schema";

export type Category = components["schemas"]["HistoryCategory"];
export type SubjectKind = components["schemas"]["HistorySubjectKind"];
export interface HistoryState {
  q: string;
  category: Category[];
  subject_kind: SubjectKind[];
  year: string;
}
export const categories: Category[] = [
  "event",
  "propagation",
  "germination",
  "harvest",
  "material",
  "schedule",
];
export const categoryLabels: Record<Category, string> = {
  event: "Journal",
  propagation: "Propagation",
  germination: "Germination",
  harvest: "Harvests",
  material: "Stored material",
  schedule: "Schedule completions",
};
export const subjectLabels: Record<SubjectKind, string> = {
  plant: "Plant",
  plant_group: "Plant group",
  sowing: "Sowing",
  harvest: "Harvest",
  harvest_inventory: "Stored material",
  seed_lot: "Seed lot",
  scheduled_activity: "Scheduled activity",
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
      (key) => !["q", "category", "subject_kind", "year"].includes(key),
    )
  )
    return null;
  const q = input.q ?? "";
  const category = input.category === undefined ? [] : input.category;
  const rawSubject = input.subject_kind;
  const subject =
    rawSubject === undefined || rawSubject === ""
      ? []
      : typeof rawSubject === "string"
        ? [rawSubject]
        : rawSubject;
  const year = input.year ?? undefined;
  if (
    strict &&
    (typeof q !== "string" ||
      Array.from(q.trim()).length > 200 ||
      !Array.isArray(category) ||
      category.length > categories.length ||
      category.some((value) => !categories.includes(value as Category)) ||
      !Array.isArray(subject) ||
      subject.length > Object.keys(subjectLabels).length ||
      subject.some(
        (value) =>
          typeof value !== "string" || !Object.hasOwn(subjectLabels, value),
      ) ||
      (year !== undefined && !validYear(year)))
  )
    return null;
  return {
    q: typeof q === "string" && Array.from(q.trim()).length <= 200 ? q : "",
    category: categories.filter(
      (item) => Array.isArray(category) && category.includes(item),
    ),
    subject_kind: (Object.keys(subjectLabels) as SubjectKind[]).filter(
      (kind) => Array.isArray(subject) && subject.includes(kind),
    ),
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
        q: params.get("q") ?? "",
        category: params.getAll("category"),
        subject_kind: params.getAll("subject_kind"),
        ...(year && /^\d{1,4}$/.test(year) ? { year: Number(year) } : {}),
      },
      false,
    ) ?? { q: "", category: [], subject_kind: [], year: "" }
  );
}
export function saveHistoryState(
  state: HistoryState,
): Record<string, string | number | string[]> {
  return {
    ...(state.q.trim() ? { q: state.q.trim() } : {}),
    ...(state.category.length
      ? { category: categories.filter((c) => state.category.includes(c)) }
      : {}),
    ...(state.subject_kind.length ? { subject_kind: state.subject_kind } : {}),
    ...(state.year ? { year: Number(state.year) } : {}),
  };
}
export function historyParams(state: HistoryState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.q.trim()) params.set("q", state.q.trim());
  for (const category of categories.filter((c) => state.category.includes(c)))
    params.append("category", category);
  for (const kind of (Object.keys(subjectLabels) as SubjectKind[]).filter(
    (kind) => state.subject_kind.includes(kind),
  ))
    params.append("subject_kind", kind);
  if (state.year) params.set("year", state.year);
  return params;
}
export function historyHash(state: HistoryState): string {
  const params = historyParams(state);
  return `#/history${params.size ? `?${params}` : ""}`;
}
