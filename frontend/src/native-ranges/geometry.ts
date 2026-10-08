import type { RangePlace, Territory } from "./api";

export interface Geometry {
  source: string;
  version: string;
  license: string;
  scale: string;
  viewBox: string;
  units: Record<string, string>;
  regions: Record<string, string[]>;
}

// A separate static chunk: neither other routes nor initial application code load it.
export async function loadGeometry(): Promise<Geometry> {
  return (await import("./data/world-110m.json")).default;
}
export function rangeGeometry(place: RangePlace, geometry: Geometry) {
  const codes =
    place.place_kind !== "canonical"
      ? []
      : place.source_code_type === "iso_3166_1_alpha_2" && place.source_code
        ? [place.source_code]
        : place.source_code_type === "un_m49" && place.source_code
          ? (geometry.regions[place.source_code] ?? [])
          : [];
  return {
    codes: codes.filter((code) => Boolean(geometry.units[code])),
    missing: codes.filter((code) => !geometry.units[code]),
  };
}
export function mapCoverage(territories: Territory[], geometry: Geometry) {
  return {
    available: territories.filter((unit) =>
      Boolean(geometry.units[unit.source_code]),
    ),
    unavailable: territories.filter(
      (unit) => !geometry.units[unit.source_code],
    ),
  };
}
