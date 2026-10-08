import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";

export type SeedLotCreate = components["schemas"]["SeedLotCreate"];
export type SeedLotUpdate = components["schemas"]["SeedLotUpdate"];
export type SeedLotResponse = components["schemas"]["SeedLotResponse"];
export type PartialDate = components["schemas"]["PartialDate"];
export type SeedQuantityInput = components["schemas"]["SeedQuantity-Input"];
export type SeedLotLifecycle = components["schemas"]["SeedLotLifecycle"];
export type SeedLotSourceKind = components["schemas"]["SeedLotSourceKind"];
export type SeedLotSowingTransitionCreate =
  components["schemas"]["SeedLotSowingTransitionCreate"];
export type SeedLotSowingTransitionResponse =
  components["schemas"]["SeedLotSowingTransitionResponse"];

export function listSeedLots(signal?: AbortSignal): Promise<SeedLotResponse[]> {
  return requestJson("/api/v1/seed-lots", { signal });
}

export function createSeedLot(
  payload: SeedLotCreate,
  csrfToken: string,
): Promise<SeedLotResponse> {
  return requestJson("/api/v1/seed-lots", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function createSowingFromSeedLot(
  id: string,
  payload: SeedLotSowingTransitionCreate,
  csrfToken: string,
): Promise<SeedLotSowingTransitionResponse> {
  return requestJson(
    `/api/v1/seed-lots/${encodeURIComponent(id)}/create-sowing`,
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

export function updateSeedLot(
  id: string,
  payload: SeedLotUpdate,
  csrfToken: string,
): Promise<SeedLotResponse> {
  return requestJson(`/api/v1/seed-lots/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

const fieldLabels: Record<string, string> = {
  botanical_identity_id: "Botanical identity",
  label: "Lot label",
  acquisition_date: "Acquisition date",
  harvest_date: "Harvest date",
  expected_viability_until: "Expected viability",
  source_detail: "Source detail",
  supplier_id: "Supplier",
  order_id: "Purchase Order",
  material_provenance_place_id: "Material provenance",
  provenance_site_id: "ProvenanceSite",
  location_id: "Storage location",
  notes: "Notes",
  quantity: "Quantity",
  lifecycle: "Lifecycle",
};

export function seedLotOrderError(error: ApiError): string | undefined {
  if (
    ![404, 409].includes(error.status) ||
    !isRecord(error.body) ||
    !isRecord(error.body.detail)
  )
    return undefined;
  switch (error.body.detail.code) {
    case "stale_purchase_context":
    case "purchase_context_changed":
      return "The Order or reviewed acquisition context changed. Review purchase context again before creating this SeedLot.";
    case "order_not_found":
      return "The selected Order no longer exists. Choose another Order or clear the link.";
    case "order_source_conflict":
      return "Only purchased or purchased-fruit seed lots can link to an Order. Check the source or clear the Order link.";
    case "order_supplier_conflict":
      return "The seed lot Supplier must match the Order Supplier when both are known. Check the Supplier or choose another Order.";
    default:
      return undefined;
  }
}

export function seedLotValidationMessages(error: ApiError): string[] {
  if (!isRecord(error.body) || !Array.isArray(error.body.detail))
    return ["Check the seed lot details and try again."];
  const detail: unknown[] = error.body.detail;
  return Array.from(
    new Set(
      detail.map((item: unknown) => {
        if (!isRecord(item)) return "Check the seed lot details and try again.";
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
        if (lower.includes("zero") || lower.includes("greater than zero"))
          return "A known zero quantity is only valid for an exhausted lot, and it must be exact.";
        if (lower.includes("source detail"))
          return "Source detail is only available when the source is Other.";
        if (lower.includes("not found"))
          return `${label ?? "A selected reference"} no longer exists. Refresh the choices and select it again.`;
        if (lower.includes("blank"))
          return `${label ?? "This field"} cannot be blank.`;
        return label
          ? `Check ${label.toLocaleLowerCase()} and try again.`
          : "Check the seed lot details and try again.";
      }),
    ),
  );
}
