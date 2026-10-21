import {
  map as createMap,
  polygon,
  tileLayer,
  type Map as LeafletMap,
  type TileLayer,
  type TileEvent,
} from "leaflet";
import { useEffect, useRef, useState } from "react";
import { mapRuntimeConfig } from "../provenance-map/config";
import { loadGeometry } from "../native-ranges/geometry";
import { occurrenceTileUrl } from "./api";
import { EvidenceTiles, type TileStatus } from "./EvidenceTiles";

export function OccurrenceDensityMap({
  identityId,
  generation,
  localOnly = true,
}: {
  identityId: string;
  generation?: string | null;
  localOnly?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const overlayRef = useRef<EvidenceTiles | null>(null);
  const onlineRef = useRef<TileLayer | null>(null);
  const [status, setStatus] = useState<TileStatus>({
    failed: 0,
    missing: 0,
    pending: 0,
  });
  const basemapFailures = useRef(new Map<HTMLImageElement, string>());
  const [basemapErrors, setBasemapErrors] = useState(0);
  const [online, setOnline] = useState(false);
  const [localMapError, setLocalMapError] = useState(false);
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const map = createMap(container, {
      minZoom: 1,
      maxZoom: 16,
      scrollWheelZoom: true,
    }).setView([20, 0], 2);
    mapRef.current = map;
    map.createPane("occurrence-context").style.zIndex = "150";
    map.createPane("occurrence-basemap").style.zIndex = "180";
    let active = true;
    void loadGeometry()
      .then((geometry) => {
        if (!active) return;
        // The bundled asset uses x=(longitude+180)*2, y=(90-latitude)*2.
        // Reproject vertices through Leaflet; never stretch an equirectangular image onto Mercator.
        for (const path of Object.values(geometry.units)) {
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
            pane: "occurrence-context",
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
        if (active) setLocalMapError(true);
      });
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(() => {
            if (container.clientWidth > 0 && container.clientHeight > 0)
              map.invalidateSize({ pan: false });
          });
    observer?.observe(container);
    return () => {
      active = false;
      observer?.disconnect();
      overlayRef.current?.cancel();
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
      onlineRef.current = null;
    };
  }, [identityId]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const overlay = new EvidenceTiles((coords) => {
      const base = occurrenceTileUrl(identityId)
        .replace("{z}", String(coords.z))
        .replace("{x}", String(coords.x))
        .replace("{y}", String(coords.y));
      return `${base}?${new URLSearchParams({ ...(generation ? { generation } : {}), local_only: String(localOnly) })}`;
    }, setStatus).addTo(map);
    overlayRef.current = overlay;
    return () => {
      overlay.cancel();
      overlay.remove();
      overlayRef.current = null;
    };
  }, [identityId, generation, localOnly]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !online) return;
    const layer = tileLayer(mapRuntimeConfig.tileUrl, {
      pane: "occurrence-basemap",
      attribution: mapRuntimeConfig.attribution,
    }).addTo(map);
    onlineRef.current = layer;
    const failed = new Map<HTMLImageElement, string>();
    basemapFailures.current = failed;
    const update = (event: TileEvent, error: boolean) => {
      if (!(event.tile instanceof HTMLImageElement)) return;
      if (error) failed.set(event.tile, event.tile.src);
      else failed.delete(event.tile);
      setBasemapErrors(failed.size);
    };
    layer.on("tileerror", (event) => {
      update(event, true);
    });
    layer.on("tileload tileunload", (event) => {
      update(event as TileEvent, false);
    });
    return () => {
      layer.remove();
      onlineRef.current = null;
      setBasemapErrors(0);
    };
  }, [online, identityId]);
  return (
    <>
      <div className="occurrence-layer-status" aria-live="polite">
        {(status.failed > 0 || status.missing > 0) && (
          <div role="status" className="notice">
            <p>
              {status.failed > 0
                ? `${String(status.failed)} GBIF tiles unavailable. `
                : ""}
              {status.missing > 0
                ? `${String(status.missing)} areas have no saved tile for this snapshot. `
                : ""}
              Counts remain readable.
              {localOnly
                ? " Viewing local evidence only; use Refresh from GBIF to download missing areas."
                : ""}
            </p>
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                overlayRef.current?.retryFailed();
              }}
            >
              Retry missing occurrence tiles
            </button>
          </div>
        )}
        {basemapErrors > 0 && (
          <div className="notice" role="status">
            <p>
              Online basemap tiles are incomplete. Occurrence evidence is
              separate.
            </p>
            <button
              type="button"
              onClick={() => {
                for (const [tile, url] of basemapFailures.current)
                  tile.setAttribute("src", url);
              }}
            >
              Retry online basemap tiles
            </button>
          </div>
        )}
        {localMapError && (
          <p role="status">
            Local geographic context unavailable. Density and counts remain
            accessible.
          </p>
        )}
      </div>
      <div
        ref={containerRef}
        aria-label="Interactive GBIF occurrence-record density map"
        className="occurrence-density-map"
        role="region"
        tabIndex={0}
      />
      <label className="occurrence-online-basemap">
        <input
          type="checkbox"
          checked={online}
          onChange={(event) => {
            setOnline(event.target.checked);
          }}
        />{" "}
        Online basemap{" "}
        <span className="field-help">
          Optional · sends your IP and viewed area to the configured provider.
        </span>
      </label>
    </>
  );
}
