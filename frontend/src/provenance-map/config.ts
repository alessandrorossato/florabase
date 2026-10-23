const DEFAULT_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const DEFAULT_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>';

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
