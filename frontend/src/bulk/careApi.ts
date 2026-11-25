import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

export type BulkCareRecordReference =
  components["schemas"]["BulkCareRecordReference"];
export type BulkCarePreviewRequest =
  components["schemas"]["BulkCarePreviewRequest"];
export type BulkCarePreviewResponse =
  components["schemas"]["BulkCarePreviewResponse"];
export type BulkCareApplyRequest =
  components["schemas"]["BulkCareApplyRequest"];
export type BulkCareApplyResponse =
  components["schemas"]["BulkCareApplyResponse"];
export type BulkCareUndoResponse =
  components["schemas"]["BulkCareUndoResponse"];
export type BulkCareRow = components["schemas"]["BulkCareRow"];
export type BulkCareKeptEvent = components["schemas"]["BulkCareKeptEvent"];
export type BulkCareKeptReason = BulkCareKeptEvent["reason"];
export type BulkCareEventKind = BulkCarePreviewRequest["kind"];

export const bulkCareKeptReasonLabels: Record<BulkCareKeptReason, string> = {
  edited: "Edited after batch creation",
  has_photos: "Has attached photos",
  linked_to_schedule: "Linked to a completed scheduled activity",
  operation_owned: "Owned by an authoritative operation",
  harvest_owned: "Owned by a Harvest record",
};

export const bulkCareKinds: readonly {
  id: BulkCareEventKind;
  label: string;
}[] = [
  { id: "watering", label: "Watering" },
  { id: "feeding", label: "Feeding" },
  { id: "treatment", label: "Treatment" },
  { id: "repotting", label: "Repotting" },
  { id: "pruning", label: "Pruning" },
  { id: "observation", label: "Observation" },
  { id: "other", label: "Other" },
] as const;

export const bulkCareKindLabels: Record<BulkCareEventKind, string> = {
  watering: "Watering",
  feeding: "Feeding",
  treatment: "Treatment",
  repotting: "Repotting",
  pruning: "Pruning",
  observation: "Observation",
  other: "Other",
};

function plural(count: number, singular: string, pluralWord: string): string {
  return `${String(count)} ${count === 1 ? singular : pluralWord}`;
}

export function formatBulkCareSummary(
  preview: BulkCarePreviewResponse,
): string {
  const kindLabel = bulkCareKindLabels[preview.kind];
  const breakdown: string[] = [];
  if (preview.plant_count > 0) {
    breakdown.push(plural(preview.plant_count, "plant", "plants"));
  }
  if (preview.plant_group_count > 0) {
    breakdown.push(plural(preview.plant_group_count, "group", "groups"));
  }
  const detail = breakdown.length ? ` (${breakdown.join(", ")})` : "";
  const locationPart = preview.location_label
    ? ` in ${preview.location_label}${
        preview.sublocation_count > 0
          ? ` and ${plural(preview.sublocation_count, "sub-location", "sub-locations")}`
          : ""
      }`
    : "";
  return `${kindLabel} on ${plural(preview.log_count, "record", "records")}${detail}${locationPart}`;
}

export function previewBulkCare(
  payload: BulkCarePreviewRequest,
  csrfToken: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<BulkCarePreviewResponse> {
  return requestJson<BulkCarePreviewResponse>("/api/v1/bulk/care/preview", {
    capability,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(payload),
    signal,
  });
}

export function applyBulkCare(
  payload: BulkCareApplyRequest,
  csrfToken: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<BulkCareApplyResponse> {
  return requestJson<BulkCareApplyResponse>("/api/v1/bulk/care/apply", {
    capability,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(payload),
    signal,
  });
}

export function undoBulkCare(
  batchId: string,
  csrfToken: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<BulkCareUndoResponse> {
  return requestJson<BulkCareUndoResponse>(
    `/api/v1/bulk/care/batches/${batchId}`,
    {
      capability,
      method: "DELETE",
      headers: {
        "X-CSRF-Token": csrfToken,
      },
      signal,
    },
  );
}
