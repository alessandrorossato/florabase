import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

export type LocalPhoto = components["schemas"]["LocalPhotoResponse"];
export type ExternalImage = components["schemas"]["ExternalImageResponse"];
export type CollectionPhoto = LocalPhoto | ExternalImage;
export type PrimaryPhoto = components["schemas"]["PrimaryPhotoResponse"];
export type ExternalImageWrite = components["schemas"]["ExternalImageCreate"];
export type LocalPhotoUpdate = components["schemas"]["LocalPhotoUpdate"];
export type PhotoTarget =
  | "seed_lot"
  | "sowing"
  | "plant"
  | "plant_group"
  | "event"
  | "harvest"
  | "supplier"
  | "vegetative_lot"
  | "propagation_attempt";

function targetPath(target: PhotoTarget, id: string): string {
  return `/api/v1/collection-records/${target}/${encodeURIComponent(id)}/photos`;
}

export function getPrimaryPhoto(
  target: Exclude<PhotoTarget, "sowing" | "event">,
  id: string,
  capability: ProtectedRequestCapability,
): Promise<PrimaryPhoto | null> {
  return requestJson(
    `/api/v1/collection-records/${target}/${encodeURIComponent(id)}/primary-photo`,
    { capability },
  );
}

export function setPrimaryPhoto(
  target: Exclude<PhotoTarget, "sowing" | "event">,
  id: string,
  photo: Pick<PrimaryPhoto, "kind" | "photo_id">,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<PrimaryPhoto> {
  return requestJson(
    `/api/v1/collection-records/${target}/${encodeURIComponent(id)}/primary-photo`,
    {
      capability,
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(photo),
    },
  );
}

export function clearPrimaryPhoto(
  target: Exclude<PhotoTarget, "sowing" | "event">,
  id: string,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(
    `/api/v1/collection-records/${target}/${encodeURIComponent(id)}/primary-photo`,
    { capability, method: "DELETE", headers: { "X-CSRF-Token": csrfToken } },
  );
}

export function listPhotos(
  target: PhotoTarget,
  id: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<CollectionPhoto[]> {
  return requestJson(targetPath(target, id), { capability, signal });
}

export function uploadPhoto(
  target: PhotoTarget,
  id: string,
  file: File,
  metadata: {
    caption: string;
    attribution: string;
    licence_label: string;
    licence_url: string;
  },
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<LocalPhoto> {
  const body = new FormData();
  body.set("file", file);
  for (const [key, value] of Object.entries(metadata))
    if (value.trim()) body.set(key, value);
  return requestJson(`${targetPath(target, id)}/local`, {
    capability,
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
  capability: ProtectedRequestCapability,
): Promise<ExternalImage> {
  return requestJson(`${targetPath(target, id)}/external`, {
    capability,
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
  capability: ProtectedRequestCapability,
): Promise<LocalPhoto> {
  return requestJson(
    `/api/v1/collection-photos/local/${encodeURIComponent(id)}`,
    {
      capability,
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
  capability: ProtectedRequestCapability,
): Promise<ExternalImage> {
  return requestJson(
    `/api/v1/collection-photos/external/${encodeURIComponent(id)}`,
    {
      capability,
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
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(
    `/api/v1/collection-photos/${kind}/${encodeURIComponent(id)}`,
    { capability, method: "DELETE", headers: { "X-CSRF-Token": csrfToken } },
  );
}
