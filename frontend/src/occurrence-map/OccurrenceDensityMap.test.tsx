import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
const mocks = vi.hoisted(() => {
  const map = {
    remove: vi.fn(),
    invalidateSize: vi.fn(),
    createPane: vi.fn(() => ({ style: {} })),
    attributionControl: { addAttribution: vi.fn() },
    setView: vi.fn(),
  };
  map.setView.mockReturnValue(map);
  const layer = { addTo: vi.fn(), remove: vi.fn(), on: vi.fn() };
  layer.addTo.mockReturnValue(layer);
  layer.on.mockReturnValue(layer);
  return {
    map,
    layer,
    createMap: vi.fn(() => map),
    tileLayer: vi.fn(() => layer),
    overlayConstruct: vi.fn(),
    overlayRemove: vi.fn(),
    retry: vi.fn(),
    cancel: vi.fn(),
  };
});
vi.mock("leaflet", () => ({
  map: mocks.createMap,
  tileLayer: mocks.tileLayer,
  polygon: vi.fn(() => mocks.layer),
}));
vi.mock("../native-ranges/geometry", () => ({
  loadGeometry: vi.fn(() => Promise.resolve({ units: {}, regions: {} })),
}));
vi.mock("./EvidenceTiles", () => ({
  EvidenceTiles: class {
    constructor(...args: unknown[]) {
      mocks.overlayConstruct(...args);
    }
    addTo() {
      return this;
    }
    remove = mocks.overlayRemove;
    retryFailed = mocks.retry;
    cancel = mocks.cancel;
  },
}));
import { OccurrenceDensityMap } from "./OccurrenceDensityMap";
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});
test("cache playback has no online basemap, refresh changes only the overlay", async () => {
  const view = render(
    <OccurrenceDensityMap identityId="identity" generation="one" />,
  );
  await waitFor(() => {
    expect(mocks.map.attributionControl.addAttribution).toHaveBeenCalled();
  });
  expect(mocks.tileLayer).not.toHaveBeenCalled();
  expect(mocks.createMap).toHaveBeenCalledTimes(1);
  const url = mocks.overlayConstruct.mock.calls[0][0] as (coords: {
    x: number;
    y: number;
    z: number;
  }) => string;
  expect(url({ x: 1, y: 1, z: 2 })).toContain("generation=one&local_only=true");
  view.rerender(
    <OccurrenceDensityMap
      identityId="identity"
      generation="two"
      localOnly={false}
    />,
  );
  expect(mocks.createMap).toHaveBeenCalledTimes(1);
  expect(mocks.map.remove).not.toHaveBeenCalled();
  expect(mocks.overlayRemove).toHaveBeenCalledTimes(1);
});
test("configured basemap is explicitly enabled with independent recoverable errors", async () => {
  render(<OccurrenceDensityMap identityId="identity" generation="one" />);
  fireEvent.click(screen.getByRole("checkbox", { name: /Online basemap/ }));
  expect(mocks.tileLayer).toHaveBeenCalledTimes(1);
  const callback = mocks.layer.on.mock.calls.find(
    ([name]) => name === "tileerror",
  )?.[1] as (event: { tile: HTMLImageElement }) => void;
  const image = document.createElement("img");
  image.src = "https://tiles.example/tile";
  const { act } = await import("@testing-library/react");
  act(() => {
    callback({ tile: image });
  });
  expect(screen.getByText(/Online basemap tiles are incomplete/)).toBeVisible();
  expect(screen.queryByText(/GBIF tiles unavailable/)).not.toBeInTheDocument();
  const loaded = mocks.layer.on.mock.calls.find(
    ([name]) => name === "tileload tileunload",
  )?.[1] as typeof callback;
  act(() => {
    loaded({ tile: image });
  });
  expect(
    screen.queryByText(/Online basemap tiles are incomplete/),
  ).not.toBeInTheDocument();
});
test("revealed panes resize the existing map and disconnect on unmount", () => {
  let callback: (() => void) | undefined;
  const disconnect = vi.fn();
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(value: () => void) {
        callback = value;
      }
      observe = vi.fn();
      disconnect = disconnect;
    },
  );
  const view = render(<OccurrenceDensityMap identityId="identity" />);
  const canvas = screen.getByRole("region");
  callback?.();
  expect(mocks.map.invalidateSize).not.toHaveBeenCalled();
  Object.defineProperties(canvas, {
    clientWidth: { value: 600 },
    clientHeight: { value: 400 },
  });
  callback?.();
  expect(mocks.map.invalidateSize).toHaveBeenCalledWith({ pan: false });
  view.unmount();
  expect(disconnect).toHaveBeenCalledOnce();
});
