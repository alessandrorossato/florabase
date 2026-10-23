import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => {
  const map = {
    setView: vi.fn(),
    remove: vi.fn(),
    fitBounds: vi.fn(),
    flyTo: vi.fn(),
    getZoom: vi.fn(() => 10),
  };
  map.setView.mockReturnValue(map);
  const layer = {
    addTo: vi.fn(),
    remove: vi.fn(),
    bindPopup: vi.fn(),
    on: vi.fn(),
    openPopup: vi.fn(),
  };
  layer.addTo.mockReturnValue(layer);
  layer.bindPopup.mockReturnValue(layer);
  layer.on.mockReturnValue(layer);
  return {
    map,
    layer,
    createMap: vi.fn(() => map),
    tileLayer: vi.fn(() => layer),
    circle: vi.fn(() => layer),
    marker: vi.fn(() => layer),
  };
});
vi.mock("leaflet", () => ({
  map: mocks.createMap,
  tileLayer: mocks.tileLayer,
  circle: mocks.circle,
  marker: mocks.marker,
  divIcon: vi.fn(),
  latLngBounds: vi.fn(() => ({ getCenter: vi.fn(() => [1, 2]) })),
}));
import { ProvenanceMap } from "./ProvenanceMap";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
test("appearance changes preserve origin camera, selection, accuracy and configured basemap", () => {
  const sites = [
    {
      id: "one",
      name: "Recorded site",
      latitude: "1",
      longitude: "2",
      geographic_place_path: null,
      coordinate_accuracy_m: "100",
    },
  ];
  render(<ProvenanceMap sites={sites} selectedId="one" onSelect={vi.fn()} />);
  const viewCalls = mocks.map.flyTo.mock.calls.length;
  const fetch = vi.spyOn(globalThis, "fetch");
  window.florabaseAppearance.setPalette("herbarium");
  window.florabaseAppearance.setAppearance("dark");
  expect(mocks.createMap).toHaveBeenCalledTimes(1);
  expect(mocks.tileLayer).toHaveBeenCalledTimes(1);
  expect(mocks.circle).toHaveBeenCalledWith(
    [1, 2],
    expect.objectContaining({
      radius: 100,
      fillOpacity: 0.08,
      color: "var(--primary)",
    }),
  );
  expect(mocks.map.flyTo).toHaveBeenCalledTimes(viewCalls);
  expect(mocks.map.remove).not.toHaveBeenCalled();
  expect(mocks.layer.remove).not.toHaveBeenCalled();
  expect(fetch).not.toHaveBeenCalled();
  fetch.mockRestore();
});
