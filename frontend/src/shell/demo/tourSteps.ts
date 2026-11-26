export interface DemoTourStep {
  readonly id: string;
  readonly href: string;
  readonly workspaceLabel: string;
  readonly title: string;
  readonly body: string;
  readonly hint: string;
}

export const DEMO_INSTALL_URL = "https://florabase.eu/docs/installation/";
export const DEMO_TOUR_DISMISSED_KEY = "florabase.demo.tour-dismissed.v1";

export const DEMO_TOUR_STEPS: readonly DemoTourStep[] = [
  {
    id: "today",
    href: "#/dashboard",
    workspaceLabel: "Today",
    title: "Welcome to Florabase",
    body: "You are exploring a live read-only sample collection. Florabase keeps botanical reference knowledge separate from the physical seeds, plants and propagation lots you hold.",
    hint: "Use the cards below or press Ctrl+K / ⌘K to search across the entire collection.",
  },
  {
    id: "identities",
    href: "#/identities",
    workspaceLabel: "Explore · Botanical identities",
    title: "Botanical identities & taxonomy history",
    body: "Author incomplete-friendly species profiles with accepted-name history, synonyms, structured native ranges and explicit links to external GBIF references.",
    hint: "Open any species from the list to inspect its profile, cover photo, synonyms and collection holdings.",
  },
  {
    id: "seeds",
    href: "#/seeds",
    workspaceLabel: "Collection · Seeds & Sowings",
    title: "Seed lots, sowings & germination",
    body: "Track seed sources, partial collection dates, storage quantities and producer lineage, then follow each sowing through dated germination observations.",
    hint: "Switch to Sowings in the left panel to see active propagation trays and germination logs.",
  },
  {
    id: "plants",
    href: "#/plants",
    workspaceLabel: "Collection · Plants & Cuttings",
    title: "Living plants, groups & cuttings",
    body: "Manage individual specimens and quantity-aware plant groups alongside vegetative cuttings, height measurements, phenology notes and hierarchical locations.",
    hint: "Click any plant to review its journal events, measurements and explicit lineage.",
  },
  {
    id: "lineage",
    href: "#/lineage",
    workspaceLabel: "Explore · Lineage & Taxonomy",
    title: "Explicit provenance & lineage chains",
    body: "Trace every specimen back through concrete SeedLot → Sowing → Plant / Cutting edges, and browse your collection inside a local World Flora Online taxonomy tree.",
    hint: "Visit Taxonomy in the Explore workspace to inspect the family and genus hierarchy.",
  },
  {
    id: "geography",
    href: "#/geography",
    workspaceLabel: "Explore · Geography",
    title: "Origins, native ranges & distribution",
    body: "Keep local provenance sites and collection origins cleanly separated from reviewed WCVP native ranges and on-demand GBIF occurrence density maps.",
    hint: "Switch tabs inside Geography to compare Collection origins with Native ranges.",
  },
  {
    id: "schedule",
    href: "#/schedule",
    workspaceLabel: "Activity · Schedule & Self-hosting",
    title: "Planned care, QR labels & self-hosting",
    body: "Plan upcoming care in list or calendar views, print QR labels for physical pots, and customize light/dark themes locally. Ready to track your own collection?",
    hint: "Try switching color themes from the sidebar footer, or install Florabase with one Docker Compose file.",
  },
];

export function hasExplicitTourParam(search: string, hash: string): boolean {
  const searchParams = new URLSearchParams(search);
  if (searchParams.get("tour") === "1") return true;
  const queryIndex = hash.indexOf("?");
  if (queryIndex === -1) return false;
  return new URLSearchParams(hash.slice(queryIndex + 1)).get("tour") === "1";
}

export function readTourDismissed(): boolean {
  try {
    return window.sessionStorage.getItem(DEMO_TOUR_DISMISSED_KEY) === "true";
  } catch {
    return false;
  }
}

export function writeTourDismissed(dismissed: boolean): void {
  try {
    if (dismissed) {
      window.sessionStorage.setItem(DEMO_TOUR_DISMISSED_KEY, "true");
    } else {
      window.sessionStorage.removeItem(DEMO_TOUR_DISMISSED_KEY);
    }
  } catch {
    // Ignore storage unavailability in restricted browser contexts.
  }
}
