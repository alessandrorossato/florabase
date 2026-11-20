import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

export type WcvpVersion = "15" | "16";
export const DEFAULT_WCVP_VERSION: WcvpVersion = "16";

function versionQuery(version: WcvpVersion) {
  return version === DEFAULT_WCVP_VERSION ? "" : `?version=${version}`;
}

export type SourceStatus = components["schemas"]["SourceStatus"];
export type WcvpTaxon = components["schemas"]["Taxon"];
export type RangeProposal = components["schemas"]["ProposalResponse"];

function path(identity: string) {
  return `/api/v1/botanical-identities/${encodeURIComponent(identity)}/native-range-enrichment`;
}
function write<T>(
  url: string,
  method: string,
  csrf: string,
  capability: ProtectedRequestCapability,
  body?: unknown,
) {
  return requestJson<T>(url, {
    capability,
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
export function getRangeSource(
  identity: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
  version: WcvpVersion = DEFAULT_WCVP_VERSION,
) {
  return requestJson<SourceStatus>(
    `${path(identity)}/source${versionQuery(version)}`,
    { capability, signal },
  );
}
export function searchWcvpTaxa(
  identity: string,
  query: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
  version: WcvpVersion = DEFAULT_WCVP_VERSION,
) {
  return requestJson<WcvpTaxon[]>(
    `${path(identity)}/taxa?q=${encodeURIComponent(query)}${version === DEFAULT_WCVP_VERSION ? "" : `&version=${version}`}`,
    { capability, signal },
  );
}
export function confirmWcvpTaxon(
  identity: string,
  taxon: WcvpTaxon,
  checksum: string,
  csrf: string,
  capability: ProtectedRequestCapability,
  version: WcvpVersion = DEFAULT_WCVP_VERSION,
) {
  return write<components["schemas"]["WcvpLinkResponse"]>(
    `${path(identity)}/link${versionQuery(version)}`,
    "PUT",
    csrf,
    capability,
    { external_id: taxon.external_id, checksum },
  );
}
export function createRangeProposal(
  identity: string,
  csrf: string,
  capability: ProtectedRequestCapability,
  version: WcvpVersion = DEFAULT_WCVP_VERSION,
) {
  return write<RangeProposal>(
    `${path(identity)}/proposals${versionQuery(version)}`,
    "POST",
    csrf,
    capability,
  );
}
export function listRangeProposals(
  identity: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
) {
  return requestJson<RangeProposal[]>(`${path(identity)}/proposals`, {
    capability,
    signal,
  });
}
export function applyRangeProposal(
  identity: string,
  proposal: string,
  selected: string[],
  csrf: string,
  capability: ProtectedRequestCapability,
) {
  return write<components["schemas"]["ApplicationResponse"]>(
    `${path(identity)}/proposals/${encodeURIComponent(proposal)}/apply`,
    "POST",
    csrf,
    capability,
    { selected_place_ids: selected },
  );
}
