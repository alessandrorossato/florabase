import {
  circle,
  divIcon,
  latLngBounds,
  map as createMap,
  marker as createMarker,
  tileLayer,
  type Layer,
  type Map as LeafletMap,
  type Marker as LeafletMarker,
} from "leaflet";
import { useEffect, useRef } from "react";

import type { ProvenanceMapSite } from "./api";
import { mapRuntimeConfig } from "./config";

const markerIcon = divIcon({
  className: "provenance-map-marker",
  html: '<span aria-hidden="true"></span>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  popupAnchor: [0, -12],
});

function position(site: ProvenanceMapSite): [number, number] {
  return [Number(site.latitude), Number(site.longitude)];
}

function popupContent(site: ProvenanceMapSite): HTMLElement {
  const container = document.createElement("div");

  const title = document.createElement("strong");
  title.textContent = site.name;
  container.append(title, document.createElement("br"));

  container.append(
    document.createTextNode(
      site.geographic_place_path ?? "No named geographic place",
    ),
    document.createElement("br"),
    document.createTextNode(
      `${String(site.usage.total)} linked ${
        site.usage.total === 1 ? "record" : "records"
      }`,
    ),
  );

  return container;
}

export function ProvenanceMap({
  sites,
  selectedId,
  onSelect,
}: {
  sites: ProvenanceMapSite[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const siteLayersRef = useRef<Layer[]>([]);
  const markersRef = useRef<Map<string, LeafletMarker>>(new Map());
  const onSelectRef = useRef(onSelect);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const map = createMap(container, {
      scrollWheelZoom: true,
    }).setView([0, 0], 2);

    tileLayer(mapRuntimeConfig.tileUrl, {
      attribution: mapRuntimeConfig.attribution,
    }).addTo(map);

    mapRef.current = map;

    const markers = markersRef.current;

    return () => {
      siteLayersRef.current = [];
      markers.clear();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    for (const layer of siteLayersRef.current) {
      layer.remove();
    }

    siteLayersRef.current = [];
    markersRef.current.clear();

    for (const site of sites) {
      const sitePosition = position(site);
      const accuracy = Number(site.coordinate_accuracy_m);

      if (
        site.coordinate_accuracy_m !== null &&
        Number.isFinite(accuracy) &&
        accuracy > 0
      ) {
        const accuracyCircle = circle(sitePosition, {
          radius: accuracy,
          color: "#30624b",
          fillOpacity: 0.08,
          weight: 1,
        }).addTo(map);

        siteLayersRef.current.push(accuracyCircle);
      }

      const siteMarker = createMarker(sitePosition, {
        icon: markerIcon,
        title: site.name,
        keyboard: true,
      })
        .bindPopup(popupContent(site))
        .on("click", () => {
          onSelectRef.current(site.id);
        })
        .addTo(map);

      markersRef.current.set(site.id, siteMarker);
      siteLayersRef.current.push(siteMarker);
    }
  }, [sites]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || sites.length === 0) return;

    const selected = sites.find((site) => site.id === selectedId) ?? null;

    if (selected) {
      map.flyTo(position(selected), Math.max(map.getZoom(), 10));
      markersRef.current.get(selected.id)?.openPopup();
      return;
    }

    const bounds = latLngBounds(sites.map(position));

    if (sites.length === 1) {
      map.setView(bounds.getCenter(), 10);
    } else {
      map.fitBounds(bounds, {
        padding: [36, 36],
        maxZoom: 12,
      });
    }
  }, [selectedId, sites]);

  return (
    <div
      ref={containerRef}
      aria-label="Interactive collection provenance map"
      className="provenance-map"
      role="region"
    />
  );
}
