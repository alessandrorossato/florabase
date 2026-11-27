import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";
export type BulkReference = components["schemas"]["BulkReference"];
export type BulkPreview = components["schemas"]["BulkLocationPreview"];
export type BulkResult = components["schemas"]["BulkLocationResult"];
export function previewLocation(
  records: BulkReference[],
  target: string,
  token: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<BulkPreview> {
  return requestJson("/api/v1/bulk/location/preview", {
    capability,
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify({ records, target_location_id: target }),
    signal,
  });
}
export type BulkMoveDate = components["schemas"]["PartialDate"] | null;
export function applyLocation(
  preview: BulkPreview,
  token: string,
  capability: ProtectedRequestCapability,
  occurredOn: BulkMoveDate = null,
): Promise<BulkResult> {
  return requestJson("/api/v1/bulk/location/apply", {
    capability,
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify({
      target_location_id: preview.target_location_id,
      expected_target_updated_at: preview.target_updated_at,
      occurred_on: occurredOn,
      records: preview.rows.map((row) => ({
        kind: row.kind,
        id: row.id,
        expected_updated_at: row.updated_at,
      })),
    }),
  });
}
