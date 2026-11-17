import { afterEach, expect, test, vi } from "vitest";

const DEFAULT_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const DEFAULT_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>';

afterEach(() => {
  delete window.__FLORABASE_RUNTIME_CONFIG__;
  vi.resetModules();
});

test("runtime config tile URL and attribution are used when set, trimmed, and fall back when blank", async () => {
  window.__FLORABASE_RUNTIME_CONFIG__ = {
    mapOnlineEnabled: true,
    mapTileUrl: "  https://tiles.example.test/{z}/{x}/{y}.png  ",
    mapAttribution: "  &copy; Example Tiles  ",
  };
  vi.resetModules();
  const configured = await import("./config");
  expect(configured.mapRuntimeConfig).toEqual({
    onlineConfigured: true,
    tileUrl: "https://tiles.example.test/{z}/{x}/{y}.png",
    attribution: "&copy; Example Tiles",
  });

  window.__FLORABASE_RUNTIME_CONFIG__ = {
    mapOnlineEnabled: "true" as unknown as boolean,
    mapTileUrl: "   ",
    mapAttribution: "   ",
  };
  vi.resetModules();
  const blank = await import("./config");
  expect(blank.mapRuntimeConfig).toEqual({
    onlineConfigured: false,
    tileUrl: DEFAULT_TILE_URL,
    attribution: DEFAULT_ATTRIBUTION,
  });

  delete window.__FLORABASE_RUNTIME_CONFIG__;
  vi.resetModules();
  const unset = await import("./config");
  expect(unset.mapRuntimeConfig).toEqual({
    onlineConfigured: false,
    tileUrl: DEFAULT_TILE_URL,
    attribution: DEFAULT_ATTRIBUTION,
  });
});
