import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

const { remove, createMap, makeTileLayer, on } = vi.hoisted(() => {
  const remove = vi.fn();
  const addTo = vi.fn();
  const setView = vi.fn(() => ({ remove }));
  const createMap = vi.fn(() => ({ setView, remove }));
  const on = vi.fn(() => ({ addTo }));
  const makeTileLayer = vi.fn(() => ({ addTo, on }));
  return { remove, addTo, setView, createMap, makeTileLayer, on };
});

vi.mock("leaflet", () => ({
  map: createMap,
  tileLayer: makeTileLayer,
}));

vi.mock("../provenance-map/config", () => ({
  mapRuntimeConfig: {
    tileUrl: "https://tiles.example/{z}/{x}/{y}.png",
    attribution: "Example basemap",
  },
}));

import { OccurrenceDensityMap } from "./OccurrenceDensityMap";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("creates fixed same-origin occurrence tiles and cleans up on identity changes", () => {
  const { rerender, unmount } = render(
    <OccurrenceDensityMap identityId="identity-one" onTileError={vi.fn()} />,
  );
  expect(createMap).toHaveBeenCalledTimes(1);
  expect(makeTileLayer).toHaveBeenNthCalledWith(
    2,
    "/api/v1/botanical-identities/identity-one/occurrence-map/tiles/{z}/{x}/{y}.png",
    expect.objectContaining({ opacity: 0.82, maxNativeZoom: 16 }),
  );
  expect(on).toHaveBeenCalledWith("tileerror", expect.any(Function));

  rerender(
    <OccurrenceDensityMap identityId="identity-two" onTileError={vi.fn()} />,
  );
  expect(remove).toHaveBeenCalledTimes(1);
  expect(createMap).toHaveBeenCalledTimes(2);
  expect(makeTileLayer).toHaveBeenNthCalledWith(
    4,
    "/api/v1/botanical-identities/identity-two/occurrence-map/tiles/{z}/{x}/{y}.png",
    expect.any(Object),
  );

  unmount();
  expect(remove).toHaveBeenCalledTimes(2);
});
