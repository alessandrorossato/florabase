export const geographyViews = [
  ["overview", "Overview"],
  ["native-ranges", "Native ranges"],
  ["species-distribution", "Species distribution"],
  ["origins", "Collection origins"],
  ["places", "Places"],
  ["sites", "Provenance sites"],
] as const;
export type GeographyView = (typeof geographyViews)[number][0];
export const geographyHref = (view: GeographyView) => `#/geography/${view}`;

const legacyMaps = {
  "native-ranges": "native-ranges",
  "species-distribution": "species-distribution",
  map: "origins",
} as const;

export function geographyRoute(
  hash: string,
): { view: GeographyView; siteId?: string } | null {
  const [path, query = ""] = hash.replace(/^#/, "").split("?", 2);
  const [section, view] = path.split("/").filter(Boolean);
  if (section && Object.hasOwn(legacyMaps, section))
    return { view: legacyMaps[section as keyof typeof legacyMaps] };
  if (section !== "geography") return null;
  if (view && geographyViews.some(([id]) => id === view))
    return { view: view as GeographyView };
  if (view) return { view: "sites", siteId: view };
  const params = new URLSearchParams(query);
  if (params.get("mode") === "sites" || params.get("mode") === "map")
    return { view: "sites" };
  // Existing q-only Saved Views and record/task links still enter management.
  return {
    view: ["q", "mode", "place", "action"].some((key) => params.has(key))
      ? "places"
      : "overview",
  };
}

/** Match canonical Geography subroutes to the unchanged directory state contracts. */
export function directoryPath(hash: string): string {
  const path = hash.split("?", 1)[0];
  switch (path) {
    case "#/geography/native-ranges":
      return "#/native-ranges";
    case "#/geography/species-distribution":
      return "#/species-distribution";
    case "#/geography/origins":
      return "#/map";
    case "#/geography/places":
    case "#/geography/sites":
      return "#/geography";
    default:
      return path;
  }
}
