import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";

export type DirectOriginKind = components["schemas"]["DirectOriginKind"];
export type PartialDate = components["schemas"]["PartialDate"];
export type PlantCreate = components["schemas"]["PlantCreate"];
export type PlantUpdate = components["schemas"]["PlantUpdate"];
export type PlantResponse = components["schemas"]["PlantResponse"];
export type PlantExtractionCreate =
  components["schemas"]["PlantExtractionCreate"];
export type PlantExtractionResponse =
  components["schemas"]["PlantExtractionResponse"];
export type PlantLifecycle = components["schemas"]["PlantLifecycle"];
export type PlantGroupCreate = components["schemas"]["PlantGroupCreate"];
export type PlantGroupUpdate = components["schemas"]["PlantGroupUpdate"];
export type PlantGroupResponse = components["schemas"]["PlantGroupResponse"];
export type PlantGroupLifecycle = components["schemas"]["PlantGroupLifecycle"];

export function listPlants(signal?: AbortSignal): Promise<PlantResponse[]> {
  return requestJson("/api/v1/plants", { signal });
}

export function listPlantGroups(
  signal?: AbortSignal,
): Promise<PlantGroupResponse[]> {
  return requestJson("/api/v1/plant-groups", { signal });
}

export function getPlant(
  id: string,
  signal?: AbortSignal,
): Promise<PlantResponse> {
  return requestJson(`/api/v1/plants/${encodeURIComponent(id)}`, { signal });
}

export function getPlantGroup(
  id: string,
  signal?: AbortSignal,
): Promise<PlantGroupResponse> {
  return requestJson(`/api/v1/plant-groups/${encodeURIComponent(id)}`, {
    signal,
  });
}

export function createPlant(
  payload: PlantCreate,
  csrfToken: string,
): Promise<PlantResponse> {
  return requestJson("/api/v1/plants", mutation("POST", payload, csrfToken));
}

export function createPlantGroup(
  payload: PlantGroupCreate,
  csrfToken: string,
): Promise<PlantGroupResponse> {
  return requestJson(
    "/api/v1/plant-groups",
    mutation("POST", payload, csrfToken),
  );
}

export function updatePlant(
  id: string,
  payload: PlantUpdate,
  csrfToken: string,
): Promise<PlantResponse> {
  return requestJson(
    `/api/v1/plants/${encodeURIComponent(id)}`,
    mutation("PUT", payload, csrfToken),
  );
}

export function updatePlantGroup(
  id: string,
  payload: PlantGroupUpdate,
  csrfToken: string,
): Promise<PlantGroupResponse> {
  return requestJson(
    `/api/v1/plant-groups/${encodeURIComponent(id)}`,
    mutation("PUT", payload, csrfToken),
  );
}

export function extractPlantFromGroup(
  id: string,
  payload: PlantExtractionCreate,
  csrfToken: string,
): Promise<PlantExtractionResponse> {
  return requestJson(
    `/api/v1/plant-groups/${encodeURIComponent(id)}/extract-plant`,
    mutation("POST", payload, csrfToken),
  );
}

function mutation(method: "POST" | "PUT", payload: unknown, csrfToken: string) {
  return {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

const fieldLabels: Record<string, string> = {
  botanical_identity_id: "Botanical identity",
  originating_sowing_id: "Originating Sowing",
  direct_origin_kind: "Direct origin",
  direct_origin_detail: "Other origin detail",
  supplier_id: "Supplier",
  material_provenance_place_id: "Material provenance",
  location_id: "Current location",
  collection_entry_date: "Collection-entry date",
  lifecycle: "Lifecycle",
  quantity: "Quantity",
  label: "Label",
  notes: "Notes",
};

export function plantValidationMessages(error: ApiError): string[] {
  if (!isRecord(error.body) || !Array.isArray(error.body.detail))
    return ["Check the Plant details and try again."];
  return Array.from(
    new Set(
      error.body.detail.map((item: unknown) => {
        if (!isRecord(item)) return "Check the Plant details and try again.";
        const location: unknown[] = Array.isArray(item.loc) ? item.loc : [];
        const field = [...location]
          .reverse()
          .find(
            (part): part is string =>
              typeof part === "string" && part in fieldLabels,
          );
        const label = field ? fieldLabels[field] : undefined;
        const message = typeof item.msg === "string" ? item.msg : "";
        const lower = message.toLocaleLowerCase();
        if (lower.includes("zero") || lower.includes("greater than"))
          return "Check quantity and lifecycle: exact zero is only valid for completed, dead, or discarded groups, and approximate counts must be positive.";
        if (lower.includes("origin"))
          return "Choose either a known Sowing or direct origin information, not both.";
        if (lower.includes("not found"))
          return `${label ?? "A selected reference"} no longer exists. Refresh the choices and select it again.`;
        return label
          ? `Check ${label.toLocaleLowerCase()} and try again.`
          : "Check the Plant details and try again.";
      }),
    ),
  );
}
