import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
import type { PhotoTarget } from "../photos/api";

export type MediaAsset = components["schemas"]["AssetResponse"];
export type MediaDetail = components["schemas"]["AssetDetailResponse"];
export type MediaPage = components["schemas"]["AssetPageResponse"];
export type MediaLink = components["schemas"]["LinkResponse"];
export type LinkWrite = components["schemas"]["LinkWrite"];
export type AssetWrite = components["schemas"]["AssetMetadataWrite"];
export type ExternalWrite = components["schemas"]["ExternalAssetCreate"];
export type TargetPage = components["schemas"]["TargetPageResponse"];
export interface MediaFilters {
  query?: string;
  kind?: string;
  association?: string;
  target?: string;
  offset?: number;
}

export function listMedia(
  filters: MediaFilters = {},
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
  return requestJson(`/api/v1/media-assets?${params}`, { signal });
}
export function getMedia(
  id: string,
  signal?: AbortSignal,
): Promise<MediaDetail> {
  return requestJson(`/api/v1/media-assets/${encodeURIComponent(id)}`, {
    signal,
  });
}
function mutation(method: string, token: string, value?: unknown): RequestInit {
  return {
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
  title: string,
  attribution: string,
  token: string,
): Promise<MediaAsset> {
  const body = new FormData();
  body.set("file", file);
  if (title.trim()) body.set("title", title);
  if (attribution.trim()) body.set("attribution", attribution);
  return requestJson("/api/v1/media-assets/local", {
    method: "POST",
    headers: { "X-CSRF-Token": token },
    body,
  });
}
export function createExternalMedia(
  value: ExternalWrite,
  token: string,
): Promise<MediaAsset> {
  return requestJson(
    "/api/v1/media-assets/external",
    mutation("POST", token, value),
  );
}
export function updateMedia(
  id: string,
  value: AssetWrite,
  token: string,
): Promise<MediaAsset> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}`,
    mutation("PATCH", token, value),
  );
}
export function deleteMedia(id: string, token: string): Promise<void> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}`,
    mutation("DELETE", token),
  );
}
export function linkMedia(
  target: PhotoTarget,
  id: string,
  mediaId: string,
  value: LinkWrite,
  token: string,
): Promise<MediaLink> {
  return requestJson(
    `/api/v1/collection-records/${target}/${encodeURIComponent(id)}/media-links`,
    mutation("POST", token, { ...value, media_asset_id: mediaId }),
  );
}
export function unlinkMedia(id: string, token: string): Promise<void> {
  return requestJson(
    `/api/v1/media-links/${encodeURIComponent(id)}`,
    mutation("DELETE", token),
  );
}
export function editMediaLink(
  id: string,
  value: LinkWrite,
  token: string,
): Promise<MediaLink> {
  return requestJson(
    `/api/v1/media-links/${encodeURIComponent(id)}`,
    mutation("PATCH", token, value),
  );
}
export function listTargets(
  target: PhotoTarget,
  query: string,
  offset = 0,
  signal?: AbortSignal,
): Promise<TargetPage> {
  return requestJson(
    `/api/v1/media-targets/${target}?${new URLSearchParams({ query, offset: String(offset), limit: "20" })}`,
    { signal },
  );
}

export function saveLocalCopy(id: string, token: string): Promise<MediaAsset> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}/save-local-copy`,
    mutation("POST", token),
  );
}
export function refreshLocalCopy(
  id: string,
  token: string,
): Promise<MediaAsset> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}/refresh-local-copy`,
    mutation("POST", token),
  );
}
export function removeLocalCopy(
  id: string,
  token: string,
): Promise<MediaAsset> {
  return requestJson(
    `/api/v1/media-assets/${encodeURIComponent(id)}/local-copy`,
    mutation("DELETE", token),
  );
}
