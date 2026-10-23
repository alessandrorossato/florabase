import {
  circle,
  divIcon,
  latLngBounds,
  map as createMap,
  marker as createMarker,
  polygon,
  tileLayer,
  type Layer,
  type Map as LeafletMap,
  type Marker as LeafletMarker,
  type TileLayer,
} from "leaflet";
import { useEffect, useRef, useState } from "react";
import { loadGeometry } from "../native-ranges/geometry";
import { mapRuntimeConfig } from "./config";
import "./origins.css";

export interface MapPoint {
  id: string;
  name: string;
  geographic_place_path: string | null;
  latitude: string;
  longitude: string;
  coordinate_accuracy_m?: string | null;
  usage?: { total?: number };
}
const markerIcon = (selected: boolean, unlinked: boolean) =>
  divIcon({
    className: `provenance-map-marker origins-marker${selected ? " origins-marker--selected" : ""}${unlinked ? " origins-marker--unlinked" : ""}`,
    html: '<span aria-hidden="true"></span>',
    iconSize: [44, 44],
    iconAnchor: [22, 22],
    tooltipAnchor: [0, -22],
  });
function position(site: MapPoint): [number, number] {
  return [Number(site.latitude), Number(site.longitude)];
}
function tooltipContent(site: MapPoint): HTMLElement {
  const container = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = site.name;
  container.append(
    title,
    document.createElement("br"),
    document.createTextNode(
      site.usage?.total != null
        ? `${String(site.usage.total)} linked ${site.usage.total === 1 ? "record" : "records"}`
        : "Stored provenance site",
    ),
  );
  return container;
}
function bindMarkerInteractions(
  marker: LeafletMarker,
  siteId: string,
  onSelect: (id: string) => void,
) {
  const element = marker.getElement();
  if (!element || element.dataset.originsInteractions === "bound") return;
  element.dataset.originsInteractions = "bound";
  element.dataset.siteId = siteId;
  element.addEventListener("focus", () => marker.openTooltip());
  element.addEventListener("blur", () => marker.closeTooltip());
  element.addEventListener("keydown", (event) => {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      onSelect(siteId);
    }
  });
}
function fitSites(map: LeafletMap, sites: MapPoint[]) {
  if (sites.length)
    map.fitBounds(latLngBounds(sites.map(position)), {
      padding: [36, 36],
      maxZoom: 12,
      animate: false,
    });
}

export function ProvenanceMap({
  sites,
  selectedId,
  onSelect,
  label = "Interactive collection provenance map",
}: {
  sites: MapPoint[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  label?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const layersRef = useRef<Layer[]>([]);
  const markersRef = useRef<Map<string, LeafletMarker>>(new Map());
  const onSelectRef = useRef(onSelect);
  const lastBoundsRef = useRef("");
  const onlineRef = useRef<TileLayer | null>(null);
  const [online, setOnline] = useState(false);
  const [tileFailed, setTileFailed] = useState(false);
  const [localError, setLocalError] = useState(false);
  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const map = createMap(container, {
      zoomAnimation: !reducedMotion,
      fadeAnimation: !reducedMotion,
      markerZoomAnimation: !reducedMotion,
      inertia: !reducedMotion,
      scrollWheelZoom: true,
      minZoom: 1,
      maxZoom: 19,
    }).setView([20, 0], 2);
    mapRef.current = map;
    map.createPane("origins-context").style.zIndex = "150";
    let active = true;
    void loadGeometry()
      .then((geometry) => {
        if (!active) return;
        for (const path of Object.values(geometry.units)) {
          // Existing bundled equirectangular drawing vertices, reprojected through Leaflet.
          const rings = path
            .split("M")
            .filter(Boolean)
            .map((ring) =>
              ring
                .replace(/Z/g, "")
                .split("L")
                .map((point) => {
                  const [x, y] = point.split(",").map(Number);
                  return [
                    Math.max(-85.051, Math.min(85.051, 90 - y / 2)),
                    x / 2 - 180,
                  ] as [number, number];
                }),
            );
          polygon(rings, {
            pane: "origins-context",
            interactive: false,
            color: "var(--border-strong)",
            weight: 0.5,
            fillColor: "var(--surface)",
            fillOpacity: 1,
          }).addTo(map);
        }
        map.attributionControl.addAttribution(
          'Context: <a href="https://www.naturalearthdata.com/">Natural Earth</a> · 1:110m, public domain',
        );
      })
      .catch(() => {
        if (active) setLocalError(true);
      });
    const resize = () => {
      if (container.clientWidth > 0 && container.clientHeight > 0)
        map.invalidateSize({ pan: false, animate: false });
    };
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(resize);
    observer?.observe(container);
    window.addEventListener("resize", resize);
    const markers = markersRef.current;
    return () => {
      active = false;
      observer?.disconnect();
      window.removeEventListener("resize", resize);
      layersRef.current = [];
      markers.clear();
      map.remove();
      mapRef.current = null;
      lastBoundsRef.current = "";
    };
  }, []);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !online || !mapRuntimeConfig.onlineConfigured || tileFailed)
      return;
    const layer = tileLayer(mapRuntimeConfig.tileUrl, {
      attribution: mapRuntimeConfig.attribution,
      // Send only the app origin across origins, as required by public tile policies.
      // Hash/query/record IDs are never included. Leave User-Agent and cache behavior native.
      referrerPolicy: "strict-origin-when-cross-origin",
    }).addTo(map);
    onlineRef.current = layer;
    layer.on("tileerror", () => {
      layer.remove();
      onlineRef.current = null;
      setOnline(false);
      setTileFailed(true);
    });
    return () => {
      layer.remove();
      onlineRef.current = null;
    };
  }, [online, tileFailed]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    for (const layer of layersRef.current) layer.remove();
    layersRef.current = [];
    markersRef.current.clear();
    for (const site of sites) {
      const accuracy = Number(site.coordinate_accuracy_m);
      if (
        site.coordinate_accuracy_m != null &&
        Number.isFinite(accuracy) &&
        accuracy > 0
      ) {
        layersRef.current.push(
          circle(position(site), {
            radius: accuracy,
            color: "var(--primary)",
            fillOpacity: 0.08,
            weight: 1,
            interactive: false,
          }).addTo(map),
        );
      }
      const marker = createMarker(position(site), {
        icon: markerIcon(false, site.usage?.total === 0),
        title: `${site.name} · ${site.geographic_place_path ?? "No named geographic place"} · ${String(site.usage?.total ?? "Unknown")} linked ${site.usage?.total === 1 ? "record" : "records"}`,
        keyboard: true,
        autoPanOnFocus: false,
        riseOnHover: true,
      })
        .bindTooltip(tooltipContent(site), { direction: "top" })
        .on("click", () => {
          onSelectRef.current(site.id);
        })
        .addTo(map);
      markersRef.current.set(site.id, marker);
      layersRef.current.push(marker);
    }
    // Record-only filtering and selection must preserve a manually chosen viewport.
    const boundsKey = sites
      .map((site) => `${site.id}:${site.latitude}:${site.longitude}`)
      .sort()
      .join("|");
    if (boundsKey !== lastBoundsRef.current) {
      fitSites(map, sites);
      lastBoundsRef.current = boundsKey;
    }
  }, [sites]);
  useEffect(() => {
    for (const site of sites) {
      const selected = site.id === selectedId;
      const marker = markersRef.current.get(site.id);
      marker?.setIcon(markerIcon(selected, site.usage?.total === 0));
      if (marker)
        bindMarkerInteractions(marker, site.id, (id) => {
          onSelectRef.current(id);
        });
      marker?.setZIndexOffset(selected ? 1000 : 0);
      marker?.getElement()?.setAttribute("aria-pressed", String(selected));
    }
  }, [sites, selectedId]);
  return (
    <>
      <div className="origins-map-controls">
        <button
          type="button"
          className="button--secondary"
          disabled={!sites.length}
          onClick={() => {
            if (mapRef.current) fitSites(mapRef.current, sites);
          }}
        >
          Fit visible sites
        </button>
        <label>
          <input
            type="checkbox"
            checked={online}
            disabled={!mapRuntimeConfig.onlineConfigured || tileFailed}
            onChange={(event) => {
              setOnline(event.currentTarget.checked);
            }}
          />
          Online basemap
        </label>
        <span className="origins-marker-key">
          <span aria-hidden="true">●</span> Recorded site · rings show accuracy
        </span>
      </div>
      <div
        ref={containerRef}
        aria-label={label}
        className="provenance-map"
        role="region"
      />
      {tileFailed && (
        <p className="notice" role="status">
          Online basemap unavailable; it has been hidden. Local geography and
          recorded sites remain usable. Check the provider's access policy and
          configuration before trying on a new visit.
        </p>
      )}
      {localError && (
        <p className="notice" role="status">
          Local overview unavailable. Recorded coordinates and the site list
          remain available.
        </p>
      )}
      <p className="origins-provider-note">
        {online
          ? "Online tiles disclose the viewed area, app origin and client network information to the configured provider; no Florabase names, IDs or botanical metadata are sent."
          : `Local overview · generalized 1:110m geography, not street-level detail. Markers retain exact recorded coordinates.${mapRuntimeConfig.onlineConfigured ? " Online detail is optional." : " Online detail is not enabled for this deployment."}`}
      </p>
    </>
  );
}
