import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
import type { SeedLotCreate, SeedLotResponse } from "../seed-lots/api";
export type AcquisitionContext = components["schemas"]["AcquisitionContext"];
export type PurchasePreview = components["schemas"]["PurchasePreview"];
export type PurchaseApply = components["schemas"]["PurchaseApplyRequest"];
export type PurchaseResolution = components["schemas"]["PurchaseResolution"];
export type PurchasePreviewInput =
  components["schemas"]["PurchasePreviewRequest"];
export type PurchaseSeedPage = components["schemas"]["PurchaseSeedPage"];
function post<T>(
  path: string,
  payload: unknown,
  csrf?: string,
  signal?: AbortSignal,
): Promise<T> {
  return requestJson(path, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify(payload),
  });
}
export function previewPurchase(
  orderId: string,
  payload: PurchasePreviewInput,
  signal?: AbortSignal,
): Promise<PurchasePreview> {
  return post(
    `/api/v1/orders/${encodeURIComponent(orderId)}/purchase-context/preview`,
    payload,
    undefined,
    signal,
  );
}
export function applyPurchase(
  orderId: string,
  payload: PurchaseApply,
  csrf: string,
  signal?: AbortSignal,
): Promise<PurchaseResolution> {
  return post(
    `/api/v1/orders/${encodeURIComponent(orderId)}/purchase-context/apply`,
    payload,
    csrf,
    signal,
  );
}
export function createPurchaseLot(
  orderId: string,
  seedLot: SeedLotCreate,
  confirmation: PurchaseApply,
  csrf: string,
): Promise<SeedLotResponse> {
  return post(
    `/api/v1/orders/${encodeURIComponent(orderId)}/seed-lots`,
    { seed_lot: seedLot, confirmation },
    csrf,
  );
}
export function purchaseChoices(
  orderId: string,
  q: string,
  offset: number,
  signal?: AbortSignal,
): Promise<PurchaseSeedPage> {
  return requestJson(
    `/api/v1/orders/${encodeURIComponent(orderId)}/seed-lot-choices?${new URLSearchParams({ q, offset: String(offset) })}`,
    { signal },
  );
}
