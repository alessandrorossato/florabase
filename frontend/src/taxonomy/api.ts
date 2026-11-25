import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";
import type { TaxonomyState } from "./state";
export type Tree = components["schemas"]["TaxonomyTree"];
export type Node = components["schemas"]["TaxonomyNode"];
export type Taxon = components["schemas"]["WfoTaxon"];
export type Identity = components["schemas"]["TaxonomyIdentity"];
export type IdentityTaxonomy = components["schemas"]["IdentityTaxonomy"];
export type Candidate = components["schemas"]["WfoCandidate"];
export type LinkWrite = components["schemas"]["TaxonomyLinkWrite"];
export function getTree(
  state: TaxonomyState,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<Tree> {
  const params = new URLSearchParams({ scope: state.scope, q: state.q.trim() });
  params.set("include_covers", "true");
  for (const category of state.record) params.append("record", category);
  return requestJson(`/api/v1/explore/taxonomy/tree?${params}`, {
    capability,
    signal,
  });
}
const endpoint = (id: string) =>
  `/api/v1/botanical-identities/${encodeURIComponent(id)}/taxonomy`;
export function getIdentityTaxonomy(
  id: string,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<IdentityTaxonomy> {
  return requestJson(endpoint(id), { capability, signal });
}
export function searchCandidates(
  id: string,
  q: string,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<Candidate[]> {
  return requestJson(
    `${endpoint(id)}/candidates?${new URLSearchParams({ q })}`,
    { capability, signal },
  );
}
export function confirmLink(
  id: string,
  payload: LinkWrite,
  csrf: string,
  capability: ProtectedRequestCapability,
): Promise<unknown> {
  return requestJson(`${endpoint(id)}/link`, {
    capability,
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
}
export function unlink(
  id: string,
  version: string,
  csrf: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(
    `${endpoint(id)}/link?${new URLSearchParams({ version })}`,
    { capability, method: "DELETE", headers: { "X-CSRF-Token": csrf } },
  );
}
export function searchNames(
  q: string,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<Candidate[]> {
  return requestJson(
    `/api/v1/explore/taxonomy/candidates?${new URLSearchParams({ q })}`,
    { capability, signal },
  );
}
