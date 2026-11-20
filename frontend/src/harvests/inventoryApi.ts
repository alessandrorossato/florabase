import type { components } from "../api/schema";
import {
  ApiError,
  requestJson,
  type ProtectedRequestCapability,
} from "../auth/api";
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
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
  harvestId?: string,
): Promise<Inventory[]> {
  return requestJson(
    `/api/v1/harvest-inventory${harvestId ? `?harvest_id=${encodeURIComponent(harvestId)}` : ""}`,
    { capability, signal },
  );
}
export function saveInventory(
  itemId: string,
  inventoryId: string | undefined,
  payload: InventoryWrite,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<Inventory> {
  return requestJson(
    inventoryId
      ? `/api/v1/harvest-inventory/${encodeURIComponent(inventoryId)}`
      : `/api/v1/harvest-items/${encodeURIComponent(itemId)}/inventory`,
    {
      capability,
      method: inventoryId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
      body: JSON.stringify(payload),
    },
  );
}
export function removeInventory(
  id: string,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(`/api/v1/harvest-inventory/${encodeURIComponent(id)}`, {
    capability,
    method: "DELETE",
    headers: { "X-CSRF-Token": token },
  });
}
export function dispositionHistory(
  id: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<Disposition[]> {
  return requestJson(
    `/api/v1/harvest-inventory/${encodeURIComponent(id)}/dispositions`,
    { capability, signal },
  );
}
export function recordDisposition(
  id: string,
  payload: DispositionCreate,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<Disposition[]> {
  return requestJson(
    `/api/v1/harvest-inventory/${encodeURIComponent(id)}/dispositions`,
    {
      capability,
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
