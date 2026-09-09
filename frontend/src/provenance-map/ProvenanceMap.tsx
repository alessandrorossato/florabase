import { divIcon, latLngBounds, type Marker as LeafletMarker } from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import {
  Circle,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";

import type { ProvenanceMapSite } from "./api";
import { mapRuntimeConfig } from "./config";

const markerIcon = divIcon({
  className: "provenance-map-marker",
  html: '<span aria-hidden="true"></span>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  popupAnchor: [0, -12],
});

function ViewController({
  sites,
  selected,
}: {
  sites: ProvenanceMapSite[];
  selected: ProvenanceMapSite | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (selected) {
      map.flyTo(
        [Number(selected.latitude), Number(selected.longitude)],
        Math.max(map.getZoom(), 10),
      );
      return;
    }
    const bounds = latLngBounds(
      sites.map((site) => [Number(site.latitude), Number(site.longitude)]),
    );
    if (sites.length === 1) map.setView(bounds.getCenter(), 10);
    else map.fitBounds(bounds, { padding: [36, 36], maxZoom: 12 });
  }, [map, selected, sites]);
  return null;
}

function SiteMarker({
  site,
  selected,
  onSelect,
}: {
  site: ProvenanceMapSite;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const marker = useRef<LeafletMarker | null>(null);
  useEffect(() => {
    if (selected) marker.current?.openPopup();
  }, [selected]);
  const position: [number, number] = [
    Number(site.latitude),
    Number(site.longitude),
  ];
  return (
    <>
      {site.coordinate_accuracy_m !== null &&
        Number(site.coordinate_accuracy_m) > 0 && (
          <Circle
            center={position}
            radius={Number(site.coordinate_accuracy_m)}
            pathOptions={{ color: "#30624b", fillOpacity: 0.08, weight: 1 }}
          />
        )}
      <Marker
        ref={marker}
        icon={markerIcon}
        position={position}
        eventHandlers={{
          click: () => {
            onSelect(site.id);
          },
        }}
        title={site.name}
      >
        <Popup>
          <strong>{site.name}</strong>
          <br />
          {site.geographic_place_path ?? "No named geographic place"}
          <br />
          {site.usage.total} linked{" "}
          {site.usage.total === 1 ? "record" : "records"}
        </Popup>
      </Marker>
    </>
  );
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
  const selected = useMemo(
    () => sites.find(({ id }) => id === selectedId) ?? null,
    [selectedId, sites],
  );
  return (
    <MapContainer
      aria-label="Interactive collection provenance map"
      center={[0, 0]}
      className="provenance-map"
      scrollWheelZoom
      zoom={2}
    >
      <TileLayer
        attribution={mapRuntimeConfig.attribution}
        url={mapRuntimeConfig.tileUrl}
      />
      <ViewController sites={sites} selected={selected} />
      {sites.map((site) => (
        <SiteMarker
          key={site.id}
          site={site}
          selected={site.id === selectedId}
          onSelect={onSelect}
        />
      ))}
    </MapContainer>
  );
}
