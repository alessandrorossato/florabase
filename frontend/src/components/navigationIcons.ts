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
  media: "image",
  geography: "globe",
  suppliers: "store",
  orders: "parcel",
  labels: "tag",
  "import-export": "exchange",
  account: "gear",
  settings: "gear",
} as const satisfies Record<string, IconName>;
