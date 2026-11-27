import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

export type QuickAddRequest = components["schemas"]["QuickAddRequest"];
export type QuickAddResponse = components["schemas"]["QuickAddResponse"];

/** QUICK-ADD-001: one atomic request for identity, optional WFO link and the record. */
export function quickAddPlant(
  payload: QuickAddRequest,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<QuickAddResponse> {
  return requestJson("/api/v1/quick-add/plant", {
    capability,
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify(payload),
  });
}

export function recordHref(result: QuickAddResponse): string {
  return `#/${result.record_kind === "plant" ? "plants" : "plant-groups"}/${result.record_id}`;
}
