export interface BreadcrumbItem {
  label: string;
  href?: string;
}
export const breadcrumbGroups = new Set([
  "Collection",
  "Activity",
  "Explore",
  "Sourcing",
  "Reference",
  "Tools",
  "Application",
]);

/** Root workspaces share the same group/current-page convention; record/task paths own theirs. */
export function workspaceBreadcrumbs(
  title: string,
  group: string,
  hash: string,
): BreadcrumbItem[] | null {
  const [path, query = ""] = hash.split("?", 2);
  if (
    !breadcrumbGroups.has(group) ||
    path.replace(/^#/, "").split("/").filter(Boolean).length !== 1 ||
    new URLSearchParams(query).has("action")
  )
    return null;
  return [{ label: group }, { label: title }];
}
