import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";

export type SupplierCreate = components["schemas"]["SupplierCreate"];
export type SupplierDetailResponse =
  components["schemas"]["SupplierDetailResponse"];
export type SupplierListResponse =
  components["schemas"]["SupplierListResponse"];
export type SupplierUpdate = components["schemas"]["SupplierUpdate"];
export type SupplierResponse = components["schemas"]["SupplierResponse"];
type HTTPValidationError = components["schemas"]["HTTPValidationError"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

const labels: Record<string, string> = {
  name: "Name",
  kind: "Kind",
  website: "Website",
  email: "Email",
  phone: "Phone",
  notes: "Notes",
};

export function supplierValidationMessages(error: ApiError): string[] {
  if (!isRecord(error.body) || !Array.isArray(error.body.detail))
    return ["Check the supplier details and try again."];
  const detail = error.body as HTTPValidationError;
  return Array.from(
    new Set(
      (detail.detail ?? []).map((item) => {
        const field = item.loc.at(-1);
        const label = typeof field === "string" ? labels[field] : undefined;
        if (item.msg.toLowerCase().includes("not be blank"))
          return `${label ?? "This field"} cannot be blank.`;
        if (item.msg.toLowerCase().includes("control character"))
          return `${label ?? "This field"} contains an unsupported character.`;
        if (item.type === "string_too_long")
          return `${label ?? "This field"} is too long.`;
        return label
          ? `Check ${label.toLowerCase()} and try again.`
          : "Check the supplier details and try again.";
      }),
    ),
  );
}

export function listSuppliers(
  signal?: AbortSignal,
): Promise<SupplierListResponse[]> {
  return requestJson("/api/v1/suppliers", { signal });
}

export function getSupplier(
  id: string,
  signal?: AbortSignal,
): Promise<SupplierDetailResponse> {
  return requestJson(`/api/v1/suppliers/${encodeURIComponent(id)}`, { signal });
}

export function createSupplier(
  payload: SupplierCreate,
  csrfToken: string,
): Promise<SupplierResponse> {
  return requestJson("/api/v1/suppliers", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function updateSupplier(
  id: string,
  payload: SupplierUpdate,
  csrfToken: string,
): Promise<SupplierResponse> {
  return requestJson(`/api/v1/suppliers/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function setSupplierRetired(
  id: string,
  retired: boolean,
  csrfToken: string,
): Promise<SupplierResponse> {
  const action = retired ? "retire" : "reactivate";
  return requestJson(`/api/v1/suppliers/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
