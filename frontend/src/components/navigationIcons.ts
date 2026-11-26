import type { IconName } from "./Icon";

/** Existing destinations only; PlantGroups/Stored material keep their contextual access. */
export const navigationIcons = {
  dashboard: "overview",
  seeds: "seed",
  sowings: "sprout",
  cuttings: "cutting",
  plants: "plant",
  harvests: "harvest",
  locations: "pin",
  events: "journal",
  history: "history",
  schedule: "calendar",
  identities: "flower",
  taxonomy: "taxonomy",
  lineage: "lineage",
  media: "image",
  geography: "globe",
  suppliers: "store",
  orders: "parcel",
  labels: "tag",
  "import-export": "exchange",
  account: "person",
  settings: "gear",
  "data-sources": "layers",
  help: "document",
  about: "monitor",
} as const satisfies Record<string, IconName>;
