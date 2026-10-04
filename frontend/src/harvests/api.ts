import type { ReferenceChoice } from "../seed-lots/ReferencePicker";
import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
export type Harvest = components["schemas"]["HarvestResponse"];
export type HarvestWrite = components["schemas"]["HarvestWrite"];
export type HarvestItem = components["schemas"]["HarvestItemWrite"];
export type MaterialKind = components["schemas"]["MaterialKind"];
export function listHarvests(
  signal?: AbortSignal,
  botanicalIdentityId?: string,
): Promise<Harvest[]> {
  const query = new URLSearchParams();
  if (botanicalIdentityId)
    query.set("botanical_identity_id", botanicalIdentityId);
  return requestJson(`/api/v1/harvests${query.size ? `?${query}` : ""}`, {
    signal,
  });
}
export function getHarvest(id: string, signal?: AbortSignal): Promise<Harvest> {
  return requestJson(`/api/v1/harvests/${encodeURIComponent(id)}`, { signal });
}
export function saveHarvest(
  id: string | null,
  payload: HarvestWrite,
  token: string,
): Promise<Harvest> {
  return requestJson(
    `/api/v1/harvests${id ? `/${encodeURIComponent(id)}` : ""}`,
    {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
      body: JSON.stringify(payload),
    },
  );
}
export function deleteHarvest(id: string, token: string): Promise<void> {
  return requestJson(`/api/v1/harvests/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": token },
  });
}
export const materials: { id: MaterialKind; label: string }[] = [
  { id: "fruit", label: "Fruit" },
  { id: "flower", label: "Flowers" },
  { id: "leaf", label: "Leaves" },
  { id: "root", label: "Roots" },
  { id: "seed", label: "Seeds" },
  { id: "stem_or_shoot", label: "Stem / shoot" },
  { id: "whole_plant", label: "Whole plant" },
  { id: "other", label: "Other" },
];
export function quantityLabel(item: HarvestItem): string {
  const q = item.quantity;
  return q
    ? `${q.is_approximate ? "About " : ""}${String(q.value)} ${q.kind === "item_count" ? "items" : (q.unit ?? "g")}`
    : "Quantity not recorded";
}
export function materialSummary(harvest: Harvest): string {
  const kinds = [...new Set(harvest.items.map((item) => item.material_kind))];
  return kinds
    .map(
      (kind) =>
        materials.find((material) => material.id === kind)?.label ?? kind,
    )
    .join(" · ");
}

export function identityChoices(
  sources: { botanical_identity: { id: string; display_label: string } }[],
): ReferenceChoice[] {
  return [
    ...new Map(
      sources.map(({ botanical_identity: identity }) => [
        identity.id,
        { id: identity.id, label: identity.display_label },
      ]),
    ).values(),
  ].sort((a, b) => a.label.localeCompare(b.label));
}
