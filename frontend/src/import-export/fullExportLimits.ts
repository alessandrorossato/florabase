/**
 * The Android app reads a protected download completely into memory and hands it to the share
 * sheet as base64, so a large photo library would exhaust the WebView. Above this size the app
 * offers the export without photos and points to a web browser instead (DATA-EXPORT-001).
 */
export const NATIVE_PHOTO_EXPORT_LIMIT_BYTES = 100 * 1024 * 1024;

export function photosTooLargeForApp(
  native: boolean,
  attachmentBytes: number | undefined,
): boolean {
  return (
    native &&
    attachmentBytes !== undefined &&
    attachmentBytes > NATIVE_PHOTO_EXPORT_LIMIT_BYTES
  );
}
