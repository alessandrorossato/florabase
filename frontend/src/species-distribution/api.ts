import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type RepresentedIdentity = components["schemas"]["RepresentedIdentity"];
export type IdentityPage = components["schemas"]["RepresentedIdentityPage"];
export type Scope = "all" | "living" | "current" | "historical";
const endpoint = "/api/v1/explore/species-distribution/identities";

export function listRepresentedIdentities(
  q: string,
  scope: Scope,
  offset: number,
  signal: AbortSignal,
): Promise<IdentityPage> {
  return requestJson(
    `${endpoint}?${new URLSearchParams({ q: q.trim(), scope, offset: String(offset) })}`,
    { signal },
  );
}
export function getRepresentedIdentity(
  id: string,
  scope: Scope,
  signal: AbortSignal,
): Promise<RepresentedIdentity> {
  return requestJson(`${endpoint}/${encodeURIComponent(id)}?scope=${scope}`, {
    signal,
  });
}
