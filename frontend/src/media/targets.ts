import type { PhotoTarget } from "../photos/api";

export const mediaTargets: { id: PhotoTarget; label: string }[] = [
  { id: "seed_lot", label: "Seed lot" },
  { id: "sowing", label: "Sowing" },
  { id: "plant", label: "Plant" },
  { id: "plant_group", label: "Plant group" },
  { id: "event", label: "Event" },
  { id: "harvest", label: "Harvest" },
  { id: "supplier", label: "Supplier" },
];
