/**
 * Native Android file-sharing, full-screen image viewer dispatch, and printing
 * helpers accessed strictly via Capacitor's injected `window.Capacitor` bridge
 * (zero `@capacitor/*` imports in `frontend/package.json`).
 *
 * All temporary exported/shared files live exclusively under the app cache's
 * dedicated `shared/` subfolder (`file_paths.xml` exposes only `cache/shared/`).
 */

import {
  NativeFileActionUnavailableError,
  type ProtectedRequestCapability,
} from "../auth/api";
import { getCapacitorGlobal } from "./runtime";

export const NATIVE_SHARED_CACHE_DIR = "shared";

export interface NativeImageViewerRequest {
  blob: Blob;
  filename: string;
  contentType: string;
  capability: ProtectedRequestCapability;
}

type NativeImageViewerHandler = (request: NativeImageViewerRequest) => void;

let imageViewerHandler: NativeImageViewerHandler | null = null;

export function registerNativeImageViewerHandler(
  handler: NativeImageViewerHandler | null,
): void {
  imageViewerHandler = handler;
}

const MIME_EXTENSIONS: Readonly<Partial<Record<string, string>>> = {
  "text/csv": ".csv",
  "image/jpeg": ".jpg",
  "image/png": ".png",
  "image/webp": ".webp",
  "image/gif": ".gif",
  "application/pdf": ".pdf",
  "text/html": ".html",
  "text/plain": ".txt",
};

function normalizedMimeType(contentType: string | null | undefined): string {
  if (!contentType) return "";
  return contentType.split(";", 1)[0].trim().toLowerCase();
}

function stripControlChars(input: string): string {
  return Array.from(input)
    .filter((ch) => {
      const code = ch.charCodeAt(0);
      return code >= 0x20 && code !== 0x7f;
    })
    .join("");
}

export function sanitizeShareFilename(
  rawName: string,
  contentType?: string | null,
): string {
  const leaf = rawName.split(/[\\/]/).pop() ?? "";
  let cleaned = stripControlChars(leaf)
    .replaceAll(/[<>:"|?*]/g, "_")
    .replaceAll(/\.{2,}/g, ".")
    .replace(/^\.+/, "")
    .trim();

  if (cleaned === "" || cleaned === ".") {
    cleaned = "florabase-file";
  }

  const mime = normalizedMimeType(contentType);
  const inferredExt = MIME_EXTENSIONS[mime];
  if (inferredExt !== undefined && !/\.[A-Za-z0-9]{1,8}$/.test(cleaned)) {
    cleaned = `${cleaned}${inferredExt}`;
  }

  if (cleaned.length > 120) {
    const dot = cleaned.lastIndexOf(".");
    if (dot > 0 && cleaned.length - dot <= 10) {
      const ext = cleaned.slice(dot);
      cleaned = `${cleaned.slice(0, 120 - ext.length)}${ext}`;
    } else {
      cleaned = cleaned.slice(0, 120);
    }
  }
  return cleaned;
}

export async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    const slice = bytes.subarray(offset, offset + chunkSize);
    binary += String.fromCharCode(...slice);
  }
  return btoa(binary);
}

function isShareCancelledError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return /cancel/i.test(error.message);
}

export async function cleanupNativeSharedCache(): Promise<void> {
  const filesystem = getCapacitorGlobal()?.Plugins?.Filesystem;
  if (!filesystem) return;
  try {
    await filesystem.rmdir({
      path: NATIVE_SHARED_CACHE_DIR,
      directory: "CACHE",
      recursive: true,
    });
  } catch {
    // Directory may not exist yet; best-effort startup cleanup.
  }
}

export async function shareNativeBlob({
  blob,
  filename,
  contentType,
}: {
  blob: Blob;
  filename: string;
  contentType?: string | null;
}): Promise<string> {
  const plugins = getCapacitorGlobal()?.Plugins;
  const filesystem = plugins?.Filesystem;
  const share = plugins?.Share;
  if (!filesystem || !share) {
    throw new NativeFileActionUnavailableError(
      "File sharing is not available in this app build.",
    );
  }

  const safeName = sanitizeShareFilename(filename, contentType ?? blob.type);
  const cachePath = `${NATIVE_SHARED_CACHE_DIR}/${safeName}`;
  const base64Data = await blobToBase64(blob);

  let fileUri: string;
  try {
    const written = await filesystem.writeFile({
      path: cachePath,
      data: base64Data,
      directory: "CACHE",
      recursive: true,
    });
    fileUri =
      written.uri ||
      (await filesystem.getUri({ path: cachePath, directory: "CACHE" })).uri;
  } catch {
    throw new NativeFileActionUnavailableError(
      "Could not prepare the file in app cache for sharing.",
    );
  }

  try {
    await share.share({
      title: safeName,
      files: [fileUri],
      dialogTitle: safeName,
    });
  } catch (error: unknown) {
    if (isShareCancelledError(error)) {
      return safeName;
    }
    throw new NativeFileActionUnavailableError(
      "Could not open the Android share sheet for this file.",
    );
  }
  return safeName;
}

export async function openNativeProtectedBlob({
  blob,
  filename,
  contentType,
  capability,
}: {
  blob: Blob;
  filename: string;
  contentType?: string | null;
  capability: ProtectedRequestCapability;
}): Promise<void> {
  const mime = normalizedMimeType(contentType ?? blob.type);
  if (mime.startsWith("image/") && imageViewerHandler !== null) {
    imageViewerHandler({
      blob,
      filename: sanitizeShareFilename(filename, mime),
      contentType: mime,
      capability,
    });
    return;
  }
  await shareNativeBlob({ blob, filename, contentType: mime });
}

export async function printNativePage(
  jobName = "Florabase Labels",
): Promise<void> {
  const capacitor = getCapacitorGlobal();
  const plugin = capacitor?.Plugins?.WebPrint;
  if (plugin) {
    await plugin.print({ jobName });
    return;
  }
  if (typeof capacitor?.nativePromise === "function") {
    await capacitor.nativePromise("WebPrint", "print", { jobName });
    return;
  }
  throw new NativeFileActionUnavailableError(
    "Printing is not available in this app build. Open Florabase in a browser to print labels.",
  );
}
