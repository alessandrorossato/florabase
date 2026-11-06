import type { IconName } from "../components/Icon";
import { navigationIcons } from "../components/navigationIcons";

/** Every routable section. Hash routes are unchanged from UI Foundation. */
export type Section =
  | "dashboard"
  | "seeds"
  | "sowings"
  | "plants"
  | "harvests"
  | "events"
  | "history"
  | "schedule"
  | "taxonomy"
  | "identities"
  | "suppliers"
  | "orders"
  | "locations"
  | "geography"
  | "import-export"
  | "labels"
  | "settings"
  | "media";

export type WorkspaceId =
  "today" | "collection" | "activity" | "explore" | "sourcing" | "settings";

/** A deep link to an existing view inside a section (no new route is created). */
export interface SubDestination {
  label: string;
  href: string;
  /** True when the current hash is this view. */
  matches: (hash: string) => boolean;
}

export interface Destination {
  section: Section;
  label: string;
  icon: IconName;
  children?: SubDestination[];
}

export interface Workspace {
  id: WorkspaceId;
  label: string;
  icon: IconName;
  summary: string;
  destinations: Destination[];
}

function pathOf(hash: string) {
  return hash.replace(/^#/, "").split("?", 2)[0] ?? "";
}
function param(hash: string, name: string) {
  return new URLSearchParams(hash.split("?", 2)[1] ?? "").get(name);
}

const destination = (
  section: Section,
  label: string,
  children?: SubDestination[],
): Destination => ({
  section,
  label,
  icon: navigationIcons[section],
  children,
});

/**
 * Workbench information architecture: five workspaces from the frozen v0.1 IA
 * (Overview is presented as Today) plus Settings with its Tools. Every former
 * sidebar destination and every Settings tool appears exactly once.
 */
export const workspaces: Workspace[] = [
  {
    id: "today",
    label: "Today",
    icon: "sun",
    summary: "Current holdings, due work and recent activity.",
    destinations: [destination("dashboard", "Today")],
  },
  {
    id: "collection",
    label: "Collection",
    icon: "plant",
    summary: "Physical material you hold, and where it is kept.",
    destinations: [
      destination("seeds", "Seeds"),
      destination("sowings", "Sowings"),
      destination("plants", "Plants", [
        {
          label: "Plant groups",
          href: "#/plants?type=group",
          matches: (hash) =>
            pathOf(hash) === "/plants" && param(hash, "type") === "group",
        },
      ]),
      destination("harvests", "Harvests", [
        {
          label: "Stored material",
          href: "#/harvests?tab=stored-material",
          matches: (hash) =>
            pathOf(hash) === "/harvests" &&
            param(hash, "tab") === "stored-material",
        },
      ]),
      destination("locations", "Locations"),
    ],
  },
  {
    id: "activity",
    label: "Activity",
    icon: "journal",
    summary: "What was recorded, what happened and what is planned.",
    destinations: [
      destination("events", "Journal"),
      destination("history", "History"),
      destination("schedule", "Schedule", [
        {
          label: "Calendar",
          href: "#/schedule?view=calendar",
          matches: (hash) =>
            pathOf(hash) === "/schedule" && param(hash, "view") === "calendar",
        },
      ]),
    ],
  },
  {
    id: "explore",
    label: "Explore",
    icon: "globe",
    summary: "Species, classification, media and geography.",
    destinations: [
      destination("identities", "Botanical identities"),
      destination("taxonomy", "Taxonomy"),
      destination("media", "Media"),
      destination("geography", "Geography", [
        {
          label: "Collection origins",
          href: "#/map",
          matches: (hash) =>
            ["/map", "/geography/origins"].includes(pathOf(hash)),
        },
        {
          label: "Species distribution",
          href: "#/species-distribution",
          matches: (hash) =>
            [
              "/species-distribution",
              "/geography/species-distribution",
            ].includes(pathOf(hash)),
        },
        {
          label: "Native ranges",
          href: "#/native-ranges",
          matches: (hash) =>
            ["/native-ranges", "/geography/native-ranges"].includes(
              pathOf(hash),
            ),
        },
      ]),
    ],
  },
  {
    id: "sourcing",
    label: "Sourcing",
    icon: "store",
    summary: "Suppliers and the orders material arrived through.",
    destinations: [
      destination("suppliers", "Suppliers"),
      destination("orders", "Orders"),
    ],
  },
  {
    id: "settings",
    label: "Settings",
    icon: "gear",
    summary: "Theme, printed labels and data transfer.",
    destinations: [
      destination("settings", "Theme"),
      destination("labels", "Labels"),
      destination("import-export", "Import / Export"),
    ],
  },
];

export const primaryWorkspaces = workspaces.filter(
  (workspace) => workspace.id !== "settings",
);

export function workspaceOf(section: Section): Workspace {
  return (
    workspaces.find((workspace) =>
      workspace.destinations.some((item) => item.section === section),
    ) ?? workspaces[0]
  );
}

/** The single list of creation entry points; each is an existing create route. */
export const createActions = [
  ["New seed lot", "#/seeds?action=create", "seed"],
  ["New sowing", "#/sowings?action=create", "sprout"],
  ["New plant", "#/plants?action=create&kind=plant", "plant"],
  ["New plant group", "#/plants?action=create&kind=group", "layers"],
  ["Record harvest", "#/harvests?action=create", "harvest"],
  ["New botanical identity", "#/identities?action=create", "flower"],
  ["New supplier", "#/suppliers?action=create", "store"],
  ["New location", "#/locations?action=create", "pin"],
  ["New local place", "#/geography?action=create", "globe"],
] as const satisfies readonly (readonly [string, string, IconName])[];

/** Flattened destinations, used by the command palette. */
export function allDestinations() {
  return workspaces.flatMap((workspace) =>
    workspace.destinations.flatMap((item) => [
      {
        label: item.label,
        href: `#/${item.section}`,
        icon: item.icon,
        workspace: workspace.label,
      },
      ...(item.children ?? []).map((child) => ({
        label: child.label,
        href: child.href,
        icon: item.icon,
        workspace: workspace.label,
      })),
    ]),
  );
}

/** Which link in a destination is the current page, honouring sub-destinations. */
export function currentLink(
  item: Destination,
  activeSection: Section,
  hash: string,
): { section: boolean; child?: SubDestination } {
  const child = item.children?.find((candidate) => candidate.matches(hash));
  if (child) return { section: false, child };
  return { section: item.section === activeSection };
}

/** The workspace whose sections own a hash route (ignoring record ids and query). */
export function workspaceOfHash(hash: string): Workspace | undefined {
  const first = hash.replace(/^#\/?/, "").split(/[/?]/, 1)[0];
  const alias: Partial<Record<string, Section>> = {
    "plant-groups": "plants",
    map: "geography",
    "species-distribution": "geography",
    "native-ranges": "geography",
  };
  const section: string = alias[first] ?? first;
  return workspaces.find((workspace) =>
    workspace.destinations.some((item) => item.section === section),
  );
}

/** A section-level destination (not a record) for a hash, used for Recent. */
export function destinationOfHash(
  hash: string,
): { label: string; href: string; icon: IconName } | undefined {
  for (const workspace of workspaces)
    for (const item of workspace.destinations) {
      const child = item.children?.find((candidate) => candidate.matches(hash));
      if (child)
        return { label: child.label, href: child.href, icon: item.icon };
      const path = hash.split("?", 1)[0];
      if (path === `#/${item.section}`)
        return {
          label: item.label,
          href: `#/${item.section}`,
          icon: item.icon,
        };
    }
  return undefined;
}
