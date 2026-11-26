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

test("sanitizeMapAttribution allows only text and safe https links and strips scripts/onerror", async () => {
  const { sanitizeMapAttribution } = await import("./config");

  expect(
    sanitizeMapAttribution(
      '&copy; <a href="https://www.openstreetmap.org/copyright" onclick="alert(1)">OSM</a>',
    ),
  ).toBe(
    '© <a href="https://www.openstreetmap.org/copyright" rel="noopener noreferrer" target="_blank">OSM</a>',
  );

  expect(
    sanitizeMapAttribution(
      'Tiles <script>alert("xss")</script><img src=x onerror="alert(2)"> by <a href="javascript:alert(3)">Evil</a> <a href="http://insecure.example">HTTP</a>',
    ),
  ).toBe("Tiles  by Evil HTTP");

  expect(
    sanitizeMapAttribution('<svg onload="alert(1)"><script>x</script></svg>'),
  ).toBe("");
});

test("applyMapRuntimeConfig defaults offline, validates HTTPS tile templates, and sanitises attribution", async () => {
  const { applyMapRuntimeConfig, mapRuntimeConfig, resetMapRuntimeConfig } =
    await import("./config");

  applyMapRuntimeConfig(undefined);
  expect(mapRuntimeConfig).toEqual({
    onlineConfigured: false,
    tileUrl: DEFAULT_TILE_URL,
    attribution: DEFAULT_ATTRIBUTION,
  });

  applyMapRuntimeConfig({
    mapOnlineEnabled: true,
    mapTileUrl: "https://tiles.example.org/{z}/{x}/{y}.png",
    mapAttribution:
      '© <a href="https://tiles.example.org">Tiles</a><img src=x onerror=alert(1)>',
  });
  expect(mapRuntimeConfig).toEqual({
    onlineConfigured: true,
    tileUrl: "https://tiles.example.org/{z}/{x}/{y}.png",
    attribution:
      '© <a href="https://tiles.example.org/" rel="noopener noreferrer" target="_blank">Tiles</a>',
  });

  // Invalid tile URL and script-only attribution fall back cleanly.
  applyMapRuntimeConfig({
    mapOnlineEnabled: true,
    mapTileUrl: "http://insecure.example/{z}/{x}/{y}.png",
    mapAttribution: "<script>alert(1)</script>",
  });
  expect(mapRuntimeConfig).toEqual({
    onlineConfigured: true,
    tileUrl: DEFAULT_TILE_URL,
    attribution: DEFAULT_ATTRIBUTION,
  });

  resetMapRuntimeConfig();
  expect(mapRuntimeConfig.onlineConfigured).toBe(false);
});
