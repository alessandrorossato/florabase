import { map as createMap, tileLayer, type Map as LeafletMap } from "leaflet";
import { useEffect, useRef } from "react";

import { mapRuntimeConfig } from "../provenance-map/config";
import { occurrenceTileUrl } from "./api";

export function OccurrenceDensityMap({
  identityId,
  onTileError,
}: {
  identityId: string;
  onTileError: () => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const onTileErrorRef = useRef(onTileError);

  useEffect(() => {
    onTileErrorRef.current = onTileError;
  }, [onTileError]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const map = createMap(container, {
      minZoom: 1,
      maxZoom: 16,
      scrollWheelZoom: true,
    }).setView([20, 0], 2);

    tileLayer(mapRuntimeConfig.tileUrl, {
      attribution: mapRuntimeConfig.attribution,
    }).addTo(map);
    tileLayer(occurrenceTileUrl(identityId), {
      attribution:
        'Occurrence data: <a href="https://www.gbif.org" rel="noreferrer">GBIF.org</a> and contributing publishers',
      maxNativeZoom: 16,
      opacity: 0.82,
    })
      .on("tileerror", () => {
        onTileErrorRef.current();
      })
      .addTo(map);

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [identityId]);

  return (
    <div
      ref={containerRef}
      aria-label="Interactive GBIF occurrence-record density map"
      className="occurrence-density-map"
      role="region"
    />
  );
}
