import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type WcvpVersion = "15" | "16";

function versionQuery(version: WcvpVersion) {
  return version === "15" ? "" : "?version=16";
}

export type SourceStatus = components["schemas"]["SourceStatus"];
export type WcvpTaxon = components["schemas"]["Taxon"];
export type RangeProposal = components["schemas"]["ProposalResponse"];

function path(identity: string) {
  return `/api/v1/botanical-identities/${encodeURIComponent(identity)}/native-range-enrichment`;
}
function write<T>(url: string, method: string, csrf: string, body?: unknown) {
  return requestJson<T>(url, {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
export function getRangeSource(
  identity: string,
  signal?: AbortSignal,
  version: WcvpVersion = "15",
) {
  return requestJson<SourceStatus>(
    `${path(identity)}/source${versionQuery(version)}`,
    { signal },
  );
}
export function searchWcvpTaxa(
  identity: string,
  query: string,
  signal?: AbortSignal,
  version: WcvpVersion = "15",
) {
  return requestJson<WcvpTaxon[]>(
    `${path(identity)}/taxa?q=${encodeURIComponent(query)}${version === "15" ? "" : "&version=16"}`,
    { signal },
  );
}
export function confirmWcvpTaxon(
  identity: string,
  taxon: WcvpTaxon,
  checksum: string,
  csrf: string,
  version: WcvpVersion = "15",
) {
  return write<components["schemas"]["WcvpLinkResponse"]>(
    `${path(identity)}/link${versionQuery(version)}`,
    "PUT",
    csrf,
    { external_id: taxon.external_id, checksum },
  );
}
export function createRangeProposal(
  identity: string,
  csrf: string,
  version: WcvpVersion = "15",
) {
  return write<RangeProposal>(
    `${path(identity)}/proposals${versionQuery(version)}`,
    "POST",
    csrf,
  );
}
export function listRangeProposals(identity: string, signal?: AbortSignal) {
  return requestJson<RangeProposal[]>(`${path(identity)}/proposals`, {
    signal,
  });
}
export function applyRangeProposal(
  identity: string,
  proposal: string,
  selected: string[],
  csrf: string,
) {
  return write<components["schemas"]["ApplicationResponse"]>(
    `${path(identity)}/proposals/${encodeURIComponent(proposal)}/apply`,
    "POST",
    csrf,
    { selected_place_ids: selected },
  );
}
