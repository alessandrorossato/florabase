import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type LocalPhoto = components["schemas"]["LocalPhotoResponse"];
export type ExternalImage = components["schemas"]["ExternalImageResponse"];
export type CollectionPhoto = LocalPhoto | ExternalImage;
export type ExternalImageWrite = components["schemas"]["ExternalImageCreate"];
export type LocalPhotoUpdate = components["schemas"]["LocalPhotoUpdate"];
export type PhotoTarget =
  "seed_lot" | "sowing" | "plant" | "plant_group" | "event";

function targetPath(target: PhotoTarget, id: string): string {
  return `/api/v1/collection-records/${target}/${encodeURIComponent(id)}/photos`;
}

export function listPhotos(
  target: PhotoTarget,
  id: string,
  signal?: AbortSignal,
): Promise<CollectionPhoto[]> {
  return requestJson(targetPath(target, id), { signal });
}

export function uploadPhoto(
  target: PhotoTarget,
  id: string,
  file: File,
  caption: string,
  attribution: string,
  csrfToken: string,
): Promise<LocalPhoto> {
  const body = new FormData();
  body.set("file", file);
  if (caption.trim()) body.set("caption", caption);
  if (attribution.trim()) body.set("attribution", attribution);
  return requestJson(`${targetPath(target, id)}/local`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body,
  });
}

export function createExternalImage(
  target: PhotoTarget,
  id: string,
  payload: ExternalImageWrite,
  csrfToken: string,
): Promise<ExternalImage> {
  return requestJson(`${targetPath(target, id)}/external`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(payload),
  });
}

export function updateLocalPhoto(
  id: string,
  payload: LocalPhotoUpdate,
  csrfToken: string,
): Promise<LocalPhoto> {
  return requestJson(
    `/api/v1/collection-photos/local/${encodeURIComponent(id)}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(payload),
    },
  );
}

export function updateExternalImage(
  id: string,
  payload: ExternalImageWrite,
  csrfToken: string,
): Promise<ExternalImage> {
  return requestJson(
    `/api/v1/collection-photos/external/${encodeURIComponent(id)}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(payload),
    },
  );
}

export function removePhoto(
  kind: "local" | "external",
  id: string,
  csrfToken: string,
): Promise<void> {
  return requestJson(
    `/api/v1/collection-photos/${kind}/${encodeURIComponent(id)}`,
    { method: "DELETE", headers: { "X-CSRF-Token": csrfToken } },
  );
}
