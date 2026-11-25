import type { components } from "../api/schema";
import {
  requestJson,
  type ProtectedRequestCapability,
  type ProtectedRequestInit,
} from "../auth/api";
import type { PhotoTarget } from "../photos/api";

export type MediaAsset = components["schemas"]["AssetResponse"];
export type MediaDetail = components["schemas"]["AssetDetailResponse"];
export type MediaPage = components["schemas"]["AssetPageResponse"];
export type MediaLink = components["schemas"]["LinkResponse"];
export type LinkWrite = components["schemas"]["LinkWrite"];
export type AssetWrite = components["schemas"]["AssetMetadataWrite"];
export type ExternalWrite = components["schemas"]["ExternalAssetCreate"];
export type TargetPage = components["schemas"]["TargetPageResponse"];
export type MediaTargetFilter = PhotoTarget | "collection";
export interface MediaFilters {
  query?: string;
  kind?: string;
  association?: string;
  target?: MediaTargetFilter | "";
  offset?: number;
}

export function listMedia(
  filters: MediaFilters = {},
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<MediaPage> {
  const params = new URLSearchParams({ limit: "24" });
  for (const key of [
    "query",
    "kind",
    "association",
    "target",
    "offset",
  ] as const) {
    const value = filters[key];
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  return requestJson(`/api/v1/media-assets?${params}`, { capability, signal });
}
export function getMedia(
  id: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<MediaDetail> {
  return requestJson(`/api/v1/media-assets/${encodeURIComponent(id)}`, {
    capability,
    signal,
  });
}
function mutation(
  method: string,
  token: string,
  capability: ProtectedRequestCapability,
  value?: unknown,
): ProtectedRequestInit {
  return {
    capability,
    method,
    headers: {
      "X-CSRF-Token": token,
      ...(value !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    ...(value !== undefined ? { body: JSON.stringify(value) } : {}),
  };
}
export function uploadMedia(
  file: File,
  metadata: {
    title: string;
    attribution: string;
    licence_label: string;
    licence_url: string;
  },
  token: string,
  capability: ProtectedRequestCapability,
): Promise<MediaAsset> {
  const body = new FormData();
  body.set("file", file);
  for (const [key, value] of Object.entries(metadata))
    if (value.trim()) body.set(key, value);
  return requestJson("/api/v1/media-assets/local", {
    capability,
    method: "POST",
    headers: { "X-CSRF-Token": token },
    body,
  });
}
export function createExternalMedia(
  value: ExternalWrite,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<MediaAsset> {
  return requestJson(
    "/api/v1/media-assets/external",
    mutation("POST", token, capability, value),
  );
}
export function updateMedia(
  id: string,
  value: AssetWrite,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<MediaAsset> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}`,
    mutation("PATCH", token, capability, value),
  );
}
export function deleteMedia(
  id: string,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}`,
    mutation("DELETE", token, capability),
  );
}
export function linkMedia(
  target: PhotoTarget,
  id: string,
  mediaId: string,
  value: LinkWrite,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<MediaLink> {
  return requestJson(
    `/api/v1/collection-records/${target}/${encodeURIComponent(id)}/media-links`,
    mutation("POST", token, capability, { ...value, media_asset_id: mediaId }),
  );
}
export function unlinkMedia(
  id: string,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(
    `/api/v1/media-links/${encodeURIComponent(id)}`,
    mutation("DELETE", token, capability),
  );
}
export function editMediaLink(
  id: string,
  value: LinkWrite,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<MediaLink> {
  return requestJson(
    `/api/v1/media-links/${encodeURIComponent(id)}`,
    mutation("PATCH", token, capability, value),
  );
}
export function listTargets(
  target: PhotoTarget,
  query: string,
  offset = 0,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<TargetPage> {
  return requestJson(
    `/api/v1/media-targets/${target}?${new URLSearchParams({ query, offset: String(offset), limit: "20" })}`,
    { capability, signal },
  );
}

export function saveLocalCopy(
  id: string,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<MediaAsset> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}/save-local-copy`,
    mutation("POST", token, capability),
  );
}
export function refreshLocalCopy(
  id: string,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<MediaAsset> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}/refresh-local-copy`,
    mutation("POST", token, capability),
  );
}
export function removeLocalCopy(
  id: string,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<MediaAsset> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}/local-copy`,
    mutation("DELETE", token, capability),
  );
}
