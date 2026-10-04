import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";
export type Inventory = components["schemas"]["InventoryResponse"];
export type InventoryWrite = components["schemas"]["InventoryWrite"];
export type Disposition = components["schemas"]["DispositionResponse"];
export type DispositionCreate = components["schemas"]["DispositionCreate"];
export type Quantity = components["schemas"]["HarvestQuantity-Input"];
export const dispositionKinds: {
  id: DispositionCreate["kind"];
  label: string;
}[] = [
  { id: "consumed", label: "Consumed" },
  { id: "processed", label: "Processed" },
  { id: "discarded", label: "Discarded" },
  { id: "gifted", label: "Gifted" },
  { id: "used_for_propagation", label: "Used for propagation" },
];
export function inventoryList(
  signal?: AbortSignal,
  harvestId?: string,
): Promise<Inventory[]> {
  return requestJson(
    `/api/v1/harvest-inventory${harvestId ? `?harvest_id=${encodeURIComponent(harvestId)}` : ""}`,
    { signal },
  );
}
export function saveInventory(
  itemId: string,
  inventoryId: string | undefined,
  payload: InventoryWrite,
  token: string,
): Promise<Inventory> {
  return requestJson(
    inventoryId
      ? `/api/v1/harvest-inventory/${encodeURIComponent(inventoryId)}`
      : `/api/v1/harvest-items/${encodeURIComponent(itemId)}/inventory`,
    {
      method: inventoryId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
      body: JSON.stringify(payload),
    },
  );
}
export function removeInventory(id: string, token: string): Promise<void> {
  return requestJson(`/api/v1/harvest-inventory/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": token },
  });
}
export function dispositionHistory(
  id: string,
  signal?: AbortSignal,
): Promise<Disposition[]> {
  return requestJson(
    `/api/v1/harvest-inventory/${encodeURIComponent(id)}/dispositions`,
    { signal },
  );
}
export function recordDisposition(
  id: string,
  payload: DispositionCreate,
  token: string,
): Promise<Disposition[]> {
  return requestJson(
    `/api/v1/harvest-inventory/${encodeURIComponent(id)}/dispositions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
      body: JSON.stringify(payload),
    },
  );
}
export function inventoryError(failure: unknown): string {
  if (failure instanceof ApiError) {
    const body = failure.body as
      { detail?: { message?: string } | { msg: string }[] } | undefined;
    if (Array.isArray(body?.detail))
      return body.detail
        .map((item) => item.msg.replace(/^Value error, /, ""))
        .join(". ");
    if (body?.detail?.message) return body.detail.message;
  }
  return "Could not save stored material. Check the details and retry.";
}
export function remainingLabel(inventory: {
  state: string;
  quantity?: Quantity | null;
}): string {
  if (inventory.state === "depleted") return "Depleted · no material held";
  const q = inventory.quantity;
  return q
    ? `${q.is_approximate ? "About " : ""}${String(q.value)} ${q.kind === "item_count" ? "items" : (q.unit ?? "")}`
    : "Unknown quantity";
}
