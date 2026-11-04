/**
 * Florabase labels encode an ordinary record URL (labels/labelData.ts `recordUrl`):
 * `<canonical origin>/#/<seeds|plants|plant-groups>/<id>` or
 * `<canonical origin>/#/harvests/<harvest id>?inventory=<id>`. A scanned or typed value is
 * accepted only in exactly those shapes, and only its in-app route is used, so a code can
 * never send the operator to another site or start an action. The canonical origin may differ
 * from the address the app is open on (for example a LAN address), so it is not compared.
 */
const id = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const record = new RegExp(`^#/(seeds|plants|plant-groups)/(${id})$`, "i");
const stored = new RegExp(`^#/harvests/(${id})\\?inventory=(${id})$`, "i");

export function labelRoute(value: string): string | null {
  const text = value.trim();
  if (!text || text.length > 400) return null;
  let hash = text;
  if (!text.startsWith("#")) {
    let url: URL;
    try {
      url = new URL(text);
    } catch {
      return null;
    }
    if (!["http:", "https:"].includes(url.protocol)) return null;
    if (url.username || url.password || !["", "/"].includes(url.pathname))
      return null;
    if (url.search) return null;
    hash = url.hash;
  }
  return record.test(hash) || stored.test(hash) ? hash : null;
}
