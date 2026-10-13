import type { EventResponse } from "../collection/api";

export const entryLabels = {
  observations: "Observations",
  cultivation: "Cultivation",
  status: "Lifecycle",
} as const;
export type EntryCategory = keyof typeof entryLabels;
export type EventFilter = "all" | "observations" | "cultivation" | "status";

export function eventSourceLabel(event: EventResponse): string {
  return event.harvest_id
    ? "Harvest"
    : event.operation_kind ||
        ["extraction", "reintegration"].includes(event.kind)
      ? "Collection operation"
      : "Journal";
}

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

export function filteredEvents(
  events: EventResponse[],
  filter: EventFilter | EntryCategory[],
) {
  const selection = Array.isArray(filter)
    ? filter
    : filter === "all"
      ? []
      : [filter];
  return selection.length
    ? events.filter(({ kind }) =>
        selection.some((category) => groups[category].includes(kind)),
      )
    : events;
}

export function notebookEvents(events: EventResponse[]): EventResponse[] {
  const stateActions = new Set<EventResponse["kind"]>([
    "movement",
    "transfer",
    "death",
    "loss",
    "discarded",
    "harvest",
  ]);
  return events.filter(
    (event) =>
      !event.harvest_id &&
      !event.operation_kind &&
      !["extraction", "reintegration"].includes(event.kind) &&
      (!stateActions.has(event.kind) || Boolean(event.notes?.trim())),
  );
}

export function searchJournal(
  events: EventResponse[],
  q: string,
): EventResponse[] {
  const query = q.trim().toLocaleLowerCase();
  if (!query) return events;
  return events.filter((event) =>
    [
      eventLabels[event.kind],
      event.notes,
      event.target.label,
      event.target.botanical_identity.display_label,
      event.destination_location?.display_path,
      event.recipient,
    ].some((value) => value?.toLocaleLowerCase().includes(query)),
  );
}
