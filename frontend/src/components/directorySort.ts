import type { components } from "../api/schema";

type PartialDate = components["schemas"]["PartialDate"];
export type DirectorySort = "" | "name" | "name_desc" | "newest" | "oldest";
export type DirectoryNameSort = "" | "name" | "name_desc";
export const directorySorts = [
  "name",
  "name_desc",
  "newest",
  "oldest",
] as const;
export const directoryNameSorts = ["name", "name_desc"] as const;

function dateKey(date: PartialDate | null | undefined): number | null {
  return date
    ? date.year * 10000 + (date.month ?? 0) * 100 + (date.day ?? 0)
    : null;
}

/** Order an already filtered directory before pagination; records without a date stay last. */
export function sortDirectory<T>(
  records: T[],
  sort: DirectorySort,
  name: (record: T) => string,
  date?: (record: T) => PartialDate | null | undefined,
): T[] {
  if (!sort) return records;
  if (sort === "name" || sort === "name_desc") {
    const sorted = [...records];
    const direction = sort === "name" ? 1 : -1;
    return sorted.sort(
      (a, b) =>
        direction *
        name(a).localeCompare(name(b), undefined, {
          numeric: true,
          sensitivity: "base",
        }),
    );
  }
  if (!date) return records;
  const sorted = [...records];
  const direction = sort === "oldest" ? 1 : -1;
  return sorted.sort((a, b) => {
    const left = dateKey(date(a));
    const right = dateKey(date(b));
    if (left === right) return 0;
    if (left === null) return 1;
    if (right === null) return -1;
    return direction * (left - right);
  });
}
