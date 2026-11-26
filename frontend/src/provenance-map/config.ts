const DEFAULT_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const DEFAULT_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>';

const DROPPED_HTML_TAGS = new Set([
  "SCRIPT",
  "STYLE",
  "NOSCRIPT",
  "IFRAME",
  "OBJECT",
  "EMBED",
  "TEMPLATE",
  "SVG",
  "MATH",
]);

export interface FlorabaseRuntimeConfig {
  mapOnlineEnabled?: boolean;
  mapTileUrl?: string;
  mapAttribution?: string;
}

declare global {
  interface Window {
    __FLORABASE_RUNTIME_CONFIG__?: FlorabaseRuntimeConfig;
  }
}

function configured(value: string | undefined, fallback: string): string {
  if (value === undefined) return fallback;
  const trimmed = value.trim();
  if (trimmed.length === 0) return fallback;
  return trimmed;
}

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function parseSafeHttpsHref(rawHref: string | null): string | null {
  if (rawHref === null) return null;
  const trimmed = rawHref.trim();
  if (trimmed.length === 0) return null;
  try {
    const parsed = new URL(trimmed);
    if (
      parsed.protocol !== "https:" ||
      parsed.username !== "" ||
      parsed.password !== ""
    ) {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

function parseSafeTileUrl(rawUrl: string | undefined): string | null {
  if (rawUrl === undefined) return null;
  const trimmed = rawUrl.trim();
  if (trimmed.length === 0 || /\s/.test(trimmed)) return null;
  try {
    const parsed = new URL(trimmed);
    if (
      parsed.protocol !== "https:" ||
      parsed.username !== "" ||
      parsed.password !== ""
    ) {
      return null;
    }
    const decodedPath = decodeURIComponent(parsed.pathname);
    if (!decodedPath.includes("{z}/{x}/{y}")) {
      return null;
    }
    return trimmed;
  } catch {
    return null;
  }
}

function serializeAttributionNode(node: Node, insideLink: boolean): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return escapeHtml(node.textContent ?? "");
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return "";
  }
  const element = node as Element;
  const tag = element.tagName.toUpperCase();
  if (DROPPED_HTML_TAGS.has(tag)) {
    return "";
  }
  if (tag === "A" && !insideLink) {
    const safeHref = parseSafeHttpsHref(element.getAttribute("href"));
    const inner = Array.from(element.childNodes, (child) =>
      serializeAttributionNode(child, true),
    ).join("");
    if (safeHref === null) {
      return inner;
    }
    if (inner.trim().length === 0) {
      return "";
    }
    return `<a href="${escapeHtml(safeHref)}" rel="noopener noreferrer" target="_blank">${inner}</a>`;
  }
  return Array.from(element.childNodes, (child) =>
    serializeAttributionNode(child, insideLink),
  ).join("");
}

/**
 * Sanitises network-sourced map attribution HTML before passing it to Leaflet.
 * Allows only plain text and `<a href="https://..." rel="noopener noreferrer" target="_blank">`.
 * Strips scripts, event handlers, images, non-HTTPS links, and all other elements.
 */
export function sanitizeMapAttribution(raw: string | undefined): string {
  if (raw === undefined) return "";
  const trimmed = raw.trim();
  if (trimmed.length === 0) return "";
  const doc = new DOMParser().parseFromString(trimmed, "text/html");
  const serialized = Array.from(doc.body.childNodes, (child) =>
    serializeAttributionNode(child, false),
  )
    .join("")
    .trim();
  return serialized;
}

export const mapRuntimeConfig = {
  onlineConfigured:
    window.__FLORABASE_RUNTIME_CONFIG__?.mapOnlineEnabled === true,

  tileUrl: configured(
    window.__FLORABASE_RUNTIME_CONFIG__?.mapTileUrl,
    DEFAULT_TILE_URL,
  ),
  attribution: configured(
    window.__FLORABASE_RUNTIME_CONFIG__?.mapAttribution,
    DEFAULT_ATTRIBUTION,
  ),
};

/**
 * Applies server-supplied runtime config (e.g. from `GET /api/v1/system/info` in the
 * native mobile app). Never infers online basemap opt-in from a missing value, validates
 * HTTPS `{z}/{x}/{y}` tile URLs, and sanitises attribution HTML before Leaflet renders it.
 */
export function applyMapRuntimeConfig(
  config: FlorabaseRuntimeConfig | undefined,
): void {
  mapRuntimeConfig.onlineConfigured = config?.mapOnlineEnabled === true;
  mapRuntimeConfig.tileUrl =
    parseSafeTileUrl(config?.mapTileUrl) ?? DEFAULT_TILE_URL;
  const sanitized = sanitizeMapAttribution(config?.mapAttribution);
  mapRuntimeConfig.attribution =
    sanitized.length > 0 ? sanitized : DEFAULT_ATTRIBUTION;
}

export function resetMapRuntimeConfig(): void {
  mapRuntimeConfig.onlineConfigured =
    window.__FLORABASE_RUNTIME_CONFIG__?.mapOnlineEnabled === true;
  mapRuntimeConfig.tileUrl = configured(
    window.__FLORABASE_RUNTIME_CONFIG__?.mapTileUrl,
    DEFAULT_TILE_URL,
  );
  mapRuntimeConfig.attribution = configured(
    window.__FLORABASE_RUNTIME_CONFIG__?.mapAttribution,
    DEFAULT_ATTRIBUTION,
  );
}
