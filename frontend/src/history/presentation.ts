import type { HistoryEntry } from "./api";
import { formatPartialDate } from "../events/eventData";

export function historyOrigin(entry: HistoryEntry) {
  if (entry.source_kind === "event") {
    const operation =
      entry.status !== null ||
      ["extraction", "reintegration"].includes(entry.subtype);
    return {
      surface: operation ? "History" : "Journal",
      label: operation ? "Collection operation" : "Journal",
    };
  }
  const labels = {
    operation_receipt: "Propagation",
    germination: "Germination",
    harvest: "Harvest",
    disposition: "Stored material",
    conversion: "Stored material",
    scheduled_activity: "Scheduled activity",
  } as const;
  return { surface: "History", label: labels[entry.source_kind] };
}

export function historyDateLabel(entry: HistoryEntry): string {
  const utcDay = (value: string) =>
    new Intl.DateTimeFormat("en-GB", {
      dateStyle: "medium",
      timeZone: "UTC",
    }).format(new Date(value));
  if (entry.source_kind === "scheduled_activity" && entry.occurred_at)
    return `Completion recorded ${utcDay(entry.occurred_at)} (UTC)`;
  return entry.date_basis === "recorded"
    ? `Recorded ${utcDay(entry.recorded_at)} (UTC)`
    : formatPartialDate(entry.occurred_on);
}
