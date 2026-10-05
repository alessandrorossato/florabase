import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
export type Conversion = components["schemas"]["ConversionResponse"];
export type ConversionCreate = components["schemas"]["ConversionCreate"];
export type Eligibility = components["schemas"]["ConversionEligibility"];
export function listConversions(
  kind: "inventory_id" | "seed_lot_id",
  id: string,
  signal?: AbortSignal,
): Promise<Conversion[]> {
  return requestJson(
    `/api/v1/harvest-seed-conversions?${kind}=${encodeURIComponent(id)}`,
    { signal },
  );
}
export function convertSeeds(
  id: string,
  payload: ConversionCreate,
  token: string,
): Promise<Conversion> {
  return requestJson(
    `/api/v1/harvest-inventory/${encodeURIComponent(id)}/create-seed-lot`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
      body: JSON.stringify(payload),
    },
  );
}
export function reversalEligibility(
  id: string,
  signal?: AbortSignal,
): Promise<Eligibility> {
  return requestJson(
    `/api/v1/harvest-seed-conversions/${encodeURIComponent(id)}/reversal`,
    { signal },
  );
}
export function reverseConversion(
  id: string,
  token: string,
): Promise<Conversion> {
  return requestJson(
    `/api/v1/harvest-seed-conversions/${encodeURIComponent(id)}/reverse`,
    { method: "POST", headers: { "X-CSRF-Token": token } },
  );
}
