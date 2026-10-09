import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
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
  signal: AbortSignal,
): Promise<Tree> {
  const params = new URLSearchParams({ scope: state.scope, q: state.q.trim() });
  for (const category of state.record) params.append("record", category);
  return requestJson(`/api/v1/explore/taxonomy/tree?${params}`, { signal });
}
const endpoint = (id: string) =>
  `/api/v1/botanical-identities/${encodeURIComponent(id)}/taxonomy`;
export function getIdentityTaxonomy(
  id: string,
  signal: AbortSignal,
): Promise<IdentityTaxonomy> {
  return requestJson(endpoint(id), { signal });
}
export function searchCandidates(
  id: string,
  q: string,
  signal: AbortSignal,
): Promise<Candidate[]> {
  return requestJson(
    `${endpoint(id)}/candidates?${new URLSearchParams({ q })}`,
    { signal },
  );
}
export function confirmLink(
  id: string,
  payload: LinkWrite,
  csrf: string,
): Promise<unknown> {
  return requestJson(`${endpoint(id)}/link`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
}
export function unlink(
  id: string,
  version: string,
  csrf: string,
): Promise<void> {
  return requestJson(
    `${endpoint(id)}/link?${new URLSearchParams({ version })}`,
    { method: "DELETE", headers: { "X-CSRF-Token": csrf } },
  );
}
