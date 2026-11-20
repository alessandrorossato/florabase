import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

export type RepresentedIdentity = components["schemas"]["RepresentedIdentity"];
export type IdentityPage = components["schemas"]["RepresentedIdentityPage"];
export type Scope = "all" | "living" | "current" | "historical";
const endpoint = "/api/v1/explore/species-distribution/identities";

export function listRepresentedIdentities(
  q: string,
  scope: Scope,
  offset: number,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<IdentityPage> {
  return requestJson(
    `${endpoint}?${new URLSearchParams({ q: q.trim(), scope, offset: String(offset) })}`,
    { capability, signal },
  );
}
export function getRepresentedIdentity(
  id: string,
  scope: Scope,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<RepresentedIdentity> {
  return requestJson(`${endpoint}/${encodeURIComponent(id)}?scope=${scope}`, {
    capability,
    signal,
  });
}
