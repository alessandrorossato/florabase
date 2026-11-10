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
  measurement: "Measurement",
  other: "Other",
};

const groups: Record<Exclude<EventFilter, "all">, EventResponse["kind"][]> = {
  observations: ["observation", "flowering", "fruiting", "measurement"],
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

type Measurement = NonNullable<EventResponse["measurement"]>;
const quantityLabels: Record<Measurement["quantity"], string> = {
  height: "Height",
};

export function measurementText(measurement: Measurement): string {
  return `${quantityLabels[measurement.quantity]}: ${measurement.value} ${measurement.unit}${measurement.is_approximate ? " (approximate)" : ""}`;
}

export type Phenophase = NonNullable<EventResponse["phenology"]>["phase"];

/** Controlled stages, grouped by the existing Event kind that owns them (docs/phenology.md). */
export const phenophaseKinds: Record<
  "observation" | "flowering" | "fruiting",
  Phenophase[]
> = {
  observation: [
    "bud_break",
    "leaf_color_change",
    "leaf_fall",
    "dormancy_entry",
    "dormancy_exit",
  ],
  flowering: ["flowering_onset", "flowering_ongoing", "flowering_end"],
  fruiting: ["fruit_set", "fruit_ripening", "fruit_ripe"],
};

export const phenophaseLabels: Record<Phenophase, string> = {
  bud_break: "Bud break / new growth",
  leaf_color_change: "Leaf colour change",
  leaf_fall: "Leaf loss",
  dormancy_entry: "Entering dormancy",
  dormancy_exit: "Dormancy exit / renewed growth",
  flowering_onset: "Flowering began",
  flowering_ongoing: "In flower",
  flowering_end: "Flowering ended",
  fruit_set: "Fruit set",
  fruit_ripening: "Fruit ripening",
  fruit_ripe: "Fruit ready for harvest",
};

/** The stage of a phenology entry; stage-less flowering/fruiting is still phenology evidence. */
export function phenologyStage(event: EventResponse): string | null {
  if (event.phenology) return phenophaseLabels[event.phenology.phase];
  if (event.kind === "flowering") return "Flowering, stage not recorded";
  if (event.kind === "fruiting") return "Fruiting, stage not recorded";
  return null;
}

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
      event.measurement &&
        `height ${event.measurement.value} ${event.measurement.unit}`,
      event.phenology && phenophaseLabels[event.phenology.phase],
    ].some((value) => value?.toLocaleLowerCase().includes(query)),
  );
}
