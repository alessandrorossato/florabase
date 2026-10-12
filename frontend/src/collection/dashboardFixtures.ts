// Synthetic API fixtures shared by Dashboard and shell regression tests.
import type { components } from "../api/schema";
export const emptyOverview: components["schemas"]["DashboardOverview"] = {
  today: "2026-10-11",
  current_identities: 0,
  identities_with_wfo: 0,
  identities_with_profile: 0,
  sowings_unknown_germination: 0,
  sowings_with_germination: 0,
  sowings_zero_germination: 0,
  purchase_packets_without_order: 0,
  overdue: 0,
  due_today: 0,
  next_seven_days: 0,
  upcoming: [],
  recent_activity: [],
};
export function journalFixture(
  id: string,
  context: string,
): components["schemas"]["HistoryEntry"] {
  return {
    key: `event:${id}`,
    category: "event",
    source_kind: "event",
    source_id: id,
    subtype: "observation",
    title: "Observation",
    context,
    occurred_on: { precision: "year", year: 2024, month: null, day: null },
    occurred_at: null,
    recorded_at: "2026-10-10T12:00:00Z",
    date_basis: "occurred",
    primary: { kind: "plant", id, label: "Acmella plant", harvest_id: null },
    related: [],
    status: null,
  };
}
