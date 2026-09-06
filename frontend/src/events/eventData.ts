import type { EventResponse } from "../collection/api";

export type EventFilter = "all" | "observations" | "cultivation" | "status";

export const eventLabels: Record<EventResponse["kind"], string> = {
  observation: "Observation",
  movement: "Movement",
  repotting: "Repotting",
  flowering: "Flowering",
  fruiting: "Fruiting",
  pruning: "Pruning",
  treatment: "Treatment",
  harvest: "Harvest",
  extraction: "Extraction",
  reintegration: "Reintegration",
  transfer: "Transfer",
  death: "Death",
  loss: "Loss",
  discarded: "Discarded",
  other: "Other",
};

const groups: Record<Exclude<EventFilter, "all">, EventResponse["kind"][]> = {
  observations: ["observation", "flowering", "fruiting"],
  cultivation: [
    "movement",
    "repotting",
    "pruning",
    "treatment",
    "harvest",
    "extraction",
    "reintegration",
  ],
  status: ["transfer", "death", "loss", "discarded"],
};

export function formatPartialDate(value: EventResponse["occurred_on"]): string {
  if (!value) return "Date not recorded";
  if (value.precision === "year") return String(value.year);
  const year = String(value.year);
  const month = String(value.month).padStart(2, "0");
  if (value.precision === "month") return `${year}-${month}`;
  return `${year}-${month}-${String(value.day).padStart(2, "0")}`;
}

export function filteredEvents(events: EventResponse[], filter: EventFilter) {
  return filter === "all"
    ? events
    : events.filter(({ kind }) => groups[filter].includes(kind));
}
