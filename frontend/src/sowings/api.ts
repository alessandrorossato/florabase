import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";

export type SowingCreate = components["schemas"]["SowingCreate"];
export type SowingUpdate = components["schemas"]["SowingUpdate"];
export type SowingResponse = components["schemas"]["SowingResponse"];
export type SowingLifecycle = components["schemas"]["SowingLifecycle"];
export type SowingQuantityInput = components["schemas"]["SowingQuantity-Input"];
export type PartialDate = components["schemas"]["PartialDate"];
export type SowingPropagationSummary =
  components["schemas"]["SowingPropagationSummary"];
export type SowingPlantTransitionCreate =
  components["schemas"]["SowingPlantTransitionCreate"];
export type SowingPlantTransitionResponse =
  components["schemas"]["SowingPlantTransitionResponse"];
export type SowingPlantGroupTransitionCreate =
  components["schemas"]["SowingPlantGroupTransitionCreate"];
export type SowingPlantGroupTransitionResponse =
  components["schemas"]["SowingPlantGroupTransitionResponse"];

export function listSowings(signal?: AbortSignal): Promise<SowingResponse[]> {
  return requestJson("/api/v1/sowings", { signal });
}

export function getSowing(
  id: string,
  signal?: AbortSignal,
): Promise<SowingResponse> {
  return requestJson(`/api/v1/sowings/${encodeURIComponent(id)}`, { signal });
}

export function createSowing(
  payload: SowingCreate,
  csrfToken: string,
): Promise<SowingResponse> {
  return requestJson("/api/v1/sowings", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function updateSowing(
  id: string,
  payload: SowingUpdate,
  csrfToken: string,
): Promise<SowingResponse> {
  return requestJson(`/api/v1/sowings/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function getSowingPropagationSummary(
  id: string,
  signal?: AbortSignal,
): Promise<SowingPropagationSummary> {
  return requestJson(
    `/api/v1/sowings/${encodeURIComponent(id)}/propagation-summary`,
    { signal },
  );
}

export function createPlantFromSowing(
  id: string,
  payload: SowingPlantTransitionCreate,
  csrfToken: string,
): Promise<SowingPlantTransitionResponse> {
  return requestJson(`/api/v1/sowings/${encodeURIComponent(id)}/create-plant`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function createPlantGroupFromSowing(
  id: string,
  payload: SowingPlantGroupTransitionCreate,
  csrfToken: string,
): Promise<SowingPlantGroupTransitionResponse> {
  return requestJson(
    `/api/v1/sowings/${encodeURIComponent(id)}/create-plant-group`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(payload),
    },
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

const fieldLabels: Record<string, string> = {
  seed_lot_id: "Seed lot",
  label: "Sowing label",
  sowing_date: "Sowing date",
  quantity: "Quantity sown",
  germinated_count: "Germinated count",
  location_id: "Current location",
  substrate: "Substrate",
  method_container: "Method or container",
  pretreatment: "Pretreatment",
  temperature_min_c: "Minimum temperature",
  temperature_max_c: "Maximum temperature",
  environment: "Environment",
  lifecycle: "Lifecycle",
  notes: "Notes",
};

export function sowingValidationMessages(error: ApiError): string[] {
  if (!isRecord(error.body) || !Array.isArray(error.body.detail))
    return ["Check the Sowing details and try again."];
  return Array.from(
    new Set(
      error.body.detail.map((item: unknown) => {
        if (!isRecord(item)) return "Check the Sowing details and try again.";
        const location: unknown[] = Array.isArray(item.loc)
          ? (item.loc as unknown[])
          : [];
        const field = [...location]
          .reverse()
          .find(
            (part): part is string =>
              typeof part === "string" && part in fieldLabels,
          );
        const label = field ? fieldLabels[field] : undefined;
        const message = typeof item.msg === "string" ? item.msg : "";
        const lower = message.toLocaleLowerCase();
        if (lower.includes("germinated") && lower.includes("quantity"))
          return "Germinated count cannot exceed an exact seed count.";
        if (lower.includes("temperature"))
          return "Minimum temperature cannot be greater than maximum temperature.";
        if (lower.includes("not found"))
          return `${label ?? "A selected reference"} no longer exists. Refresh the choices and select it again.`;
        if (
          lower.includes("greater than 0") ||
          lower.includes("greater than zero")
        )
          return `${label ?? "Quantity"} must be greater than zero.`;
        return label
          ? `Check ${label.toLocaleLowerCase()} and try again.`
          : "Check the Sowing details and try again.";
      }),
    ),
  );
}
