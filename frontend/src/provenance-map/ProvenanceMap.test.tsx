import {
  act,
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
    fitBounds: vi.fn(),
    createPane: vi.fn(() => ({ style: {} })),
    attributionControl: { addAttribution: vi.fn() },
    setView: vi.fn(),
  };
  map.setView.mockReturnValue(map);
  const layer = {
    addTo: vi.fn(),
    remove: vi.fn(),
    on: vi.fn(),
    redraw: vi.fn(),
  };
  layer.addTo.mockReturnValue(layer);
  layer.on.mockReturnValue(layer);
  return {
    map,
    layer,
    createMap: vi.fn(() => map),
    tileLayer: vi.fn(() => layer),
    circle: vi.fn(() => layer),
    markers: [] as {
      element: HTMLElement;
      point: unknown;
      tooltip: HTMLElement;
      events: Record<string, () => void>;
      setIcon: ReturnType<typeof vi.fn>;
      setZIndexOffset: ReturnType<typeof vi.fn>;
      openTooltip: ReturnType<typeof vi.fn>;
    }[],
  };
});
vi.mock("leaflet", () => ({
  map: mocks.createMap,
  tileLayer: mocks.tileLayer,
  circle: mocks.circle,
  polygon: vi.fn(() => mocks.layer),
  divIcon: vi.fn((options: unknown) => options),
  latLngBounds: vi.fn((points: unknown) => points),
  marker: vi.fn((point: unknown) => {
    const marker = {
      element: document.createElement("button"),
      point,
      tooltip: document.createElement("div") as HTMLElement,
      events: {} as Record<string, () => void>,
      setIcon: vi.fn(),
      setZIndexOffset: vi.fn(),
      openTooltip: vi.fn(),
      closeTooltip: vi.fn(),
      remove: vi.fn(),
      getElement() {
        return this.element;
      },
      bindTooltip(content: HTMLElement) {
        this.tooltip = content;
        return this;
      },
      on(name: string, callback: () => void) {
        this.events[name] = callback;
        return this;
      },
      addTo() {
        return this;
      },
    };
    marker.setIcon.mockImplementation(() => {
      marker.element = document.createElement("button");
    });
    mocks.markers.push(marker);
    return marker;
  }),
}));
vi.mock("../native-ranges/geometry", () => ({
  loadGeometry: vi.fn(() => Promise.resolve({ units: {}, regions: {} })),
}));
import { mapRuntimeConfig } from "./config";
import { ProvenanceMap, type MapPoint } from "./ProvenanceMap";
const site: MapPoint = {
  id: "site",
  name: '<img src=x onerror="alert(1)">',
  geographic_place_path: "World → Italy",
  latitude: "38.166667",
  longitude: "13.350000",
  coordinate_accuracy_m: "25.500",
  usage: { total: 3 },
};
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  mocks.markers.length = 0;
  mapRuntimeConfig.onlineConfigured = false;
});

test("retains exact coordinates, accuracy circles, safe tooltip and Space/click selection", async () => {
  const select = vi.fn();
  const view = render(
    <ProvenanceMap sites={[site]} selectedId={null} onSelect={select} />,
  );
  await waitFor(() => {
    expect(mocks.map.attributionControl.addAttribution).toHaveBeenCalled();
  });
  expect(mocks.circle).toHaveBeenCalledWith(
    [38.166667, 13.35],
    expect.objectContaining({ radius: 25.5, interactive: false }),
  );
  const marker = mocks.markers[0];
  expect(marker.point).toEqual([38.166667, 13.35]);
  expect(marker.tooltip.querySelector("img")).toBeNull();
  expect(marker.tooltip).toHaveTextContent(site.name);
  expect(marker.tooltip).toHaveTextContent("3 linked records");
  fireEvent.focus(marker.element);
  expect(marker.openTooltip).toHaveBeenCalled();
  fireEvent.keyDown(marker.element, { key: " " });
  expect(select).toHaveBeenCalledWith("site");
  view.rerender(
    <ProvenanceMap sites={[site]} selectedId="site" onSelect={select} />,
  );
  expect(marker.setIcon).toHaveBeenCalled();
  fireEvent.focus(marker.element);
  fireEvent.keyDown(marker.element, { key: "Enter" });
  act(() => {
    marker.events.click();
  });
  expect(select).toHaveBeenCalledTimes(3);
  expect(mocks.tileLayer).not.toHaveBeenCalled();
  expect(
    screen.getByRole("checkbox", { name: "Online basemap" }),
  ).toBeDisabled();
  expect(screen.getByText(/Local overview/)).toHaveTextContent(
    "not street-level detail",
  );
});

test("selection and record-only filtering preserve viewport while Fit and geometry changes refit", () => {
  const sites = [site];
  const view = render(
    <ProvenanceMap sites={sites} selectedId={null} onSelect={vi.fn()} />,
  );
  view.rerender(
    <ProvenanceMap sites={sites} selectedId="site" onSelect={vi.fn()} />,
  );
  expect(mocks.map.fitBounds).toHaveBeenCalledTimes(1);
  expect(mocks.markers[0].setZIndexOffset).toHaveBeenLastCalledWith(1000);
  expect(mocks.markers[0].element).toHaveAttribute("aria-pressed", "true");
  view.rerender(
    <ProvenanceMap
      sites={[{ ...site, usage: { total: 1 } }]}
      selectedId="site"
      onSelect={vi.fn()}
    />,
  );
  expect(mocks.map.fitBounds).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Fit visible sites" }));
  expect(mocks.map.fitBounds).toHaveBeenCalledTimes(2);
  expect(mocks.map.fitBounds).toHaveBeenLastCalledWith(
    expect.anything(),
    expect.objectContaining({ animate: false }),
  );
  view.rerender(
    <ProvenanceMap
      sites={[{ ...site, longitude: "14" }]}
      selectedId="site"
      onSelect={vi.fn()}
    />,
  );
  expect(mocks.map.fitBounds).toHaveBeenCalledTimes(3);
  expect(mocks.createMap).toHaveBeenCalledTimes(1);
});

test("revealing a hidden map invalidates size without recreation or panning", () => {
  let callback: (() => void) | undefined;
  const disconnect = vi.fn();
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(cb: () => void) {
        callback = cb;
      }
      observe = vi.fn();
      disconnect = disconnect;
    },
  );
  const view = render(
    <ProvenanceMap sites={[site]} selectedId={null} onSelect={vi.fn()} />,
  );
  const container = screen.getByRole("region");
  Object.defineProperty(container, "clientWidth", {
    configurable: true,
    value: 0,
  });
  Object.defineProperty(container, "clientHeight", {
    configurable: true,
    value: 400,
  });
  act(() => {
    callback?.();
  });
  expect(mocks.map.invalidateSize).not.toHaveBeenCalled();
  Object.defineProperty(container, "clientWidth", {
    configurable: true,
    value: 600,
  });
  act(() => {
    callback?.();
  });
  expect(mocks.map.invalidateSize).toHaveBeenCalledWith({
    pan: false,
    animate: false,
  });
  expect(mocks.createMap).toHaveBeenCalledTimes(1);
  view.unmount();
  expect(disconnect).toHaveBeenCalled();
});

test("configured online enhancement preserves Referer and latches failures without retry", async () => {
  mapRuntimeConfig.onlineConfigured = true;
  render(<ProvenanceMap sites={[site]} selectedId={null} onSelect={vi.fn()} />);
  expect(mocks.tileLayer).not.toHaveBeenCalled();
  const toggle = screen.getByRole("checkbox", { name: "Online basemap" });
  fireEvent.click(toggle);
  expect(mocks.tileLayer).toHaveBeenCalledWith(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    expect.objectContaining({
      referrerPolicy: "strict-origin-when-cross-origin",
    }),
  );
  const failed = mocks.layer.on.mock.calls.find(
    ([name]) => name === "tileerror",
  )?.[1] as () => void;
  act(() => {
    failed();
  });
  expect(mocks.layer.remove).toHaveBeenCalled();
  expect(screen.getByRole("status")).toHaveTextContent("it has been hidden");
  expect(toggle).toBeDisabled();
  expect(toggle).not.toBeChecked();
  expect(screen.queryByRole("button", { name: "Retry basemap" })).toBeNull();
  expect(mocks.layer.redraw).not.toHaveBeenCalled();
  expect(mocks.tileLayer).toHaveBeenCalledTimes(1);
  expect(mocks.markers).toHaveLength(1);
  expect(mocks.map.fitBounds).toHaveBeenCalledTimes(1);
  await waitFor(() => {
    expect(mocks.map.attributionControl.addAttribution).toHaveBeenCalled();
  });
});

test("unknown and zero accuracy never invent a circle; coincident sites retain distinct markers", () => {
  render(
    <ProvenanceMap
      sites={[
        { ...site, coordinate_accuracy_m: null },
        { ...site, id: "coincident", coordinate_accuracy_m: "0" },
      ]}
      selectedId="coincident"
      onSelect={vi.fn()}
    />,
  );
  expect(mocks.circle).not.toHaveBeenCalled();
  expect(mocks.markers).toHaveLength(2);
  expect(mocks.markers[0].point).toEqual(mocks.markers[1].point);
  expect(mocks.markers[1].element).toHaveAttribute("aria-pressed", "true");
});

test("reduced motion disables Leaflet zoom, marker, fade and inertia animations", () => {
  vi.spyOn(window, "matchMedia").mockReturnValue({
    matches: true,
  } as MediaQueryList);
  render(<ProvenanceMap sites={[site]} selectedId={null} onSelect={vi.fn()} />);
  expect(mocks.createMap).toHaveBeenCalledWith(
    expect.anything(),
    expect.objectContaining({
      zoomAnimation: false,
      fadeAnimation: false,
      markerZoomAnimation: false,
      inertia: false,
    }),
  );
});

test.each([false, true])(
  "six-theme switching preserves Origins selection, camera and basemap consent (online=%s)",
  async (online) => {
    mapRuntimeConfig.onlineConfigured = true;
    render(
      <ProvenanceMap sites={[site]} selectedId="site" onSelect={vi.fn()} />,
    );
    await waitFor(() => {
      expect(mocks.map.attributionControl.addAttribution).toHaveBeenCalled();
    });
    if (online)
      fireEvent.click(screen.getByRole("checkbox", { name: "Online basemap" }));
    const fits = mocks.map.fitBounds.mock.calls.length;
    const removals = mocks.layer.remove.mock.calls.length;
    const fetch = vi.spyOn(globalThis, "fetch");
    for (const palette of ["botanical", "herbarium", "mineral"] as const) {
      for (const appearance of ["light", "dark"] as const) {
        act(() => {
          window.florabaseAppearance.setPalette(palette);
          window.florabaseAppearance.setAppearance(appearance);
        });
        expect(mocks.createMap).toHaveBeenCalledTimes(1);
        expect(mocks.tileLayer).toHaveBeenCalledTimes(online ? 1 : 0);
        expect(mocks.map.fitBounds).toHaveBeenCalledTimes(fits);
        expect(mocks.layer.remove).toHaveBeenCalledTimes(removals);
        expect(mocks.map.remove).not.toHaveBeenCalled();
        expect(mocks.markers).toHaveLength(1);
        expect(mocks.markers[0].element).toHaveAttribute(
          "aria-pressed",
          "true",
        );
        expect(
          screen.getByRole("checkbox", { name: "Online basemap" }),
        ).toHaveProperty("checked", online);
        expect(fetch).not.toHaveBeenCalled();
      }
    }
    expect(mocks.circle).toHaveBeenCalledWith(
      [38.166667, 13.35],
      expect.objectContaining({
        radius: 25.5,
        color: "var(--primary)",
        interactive: false,
      }),
    );
  },
);
