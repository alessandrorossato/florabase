import { useId } from "react";
import type { Territory } from "./api";
import { mapCoverage, type Geometry } from "./geometry";

export type GeometryState =
  { status: "loading" | "error" } | { status: "ready"; data: Geometry };

export function NativeCoverageMap({
  territories,
  geometry,
  selected = false,
  retry,
  contributors,
}: {
  territories: Territory[];
  geometry: GeometryState;
  selected?: boolean;
  retry: () => void;
  contributors?: Partial<Record<string, string[]>>;
}) {
  const id = useId();
  if (geometry.status === "loading")
    return <p role="status">Loading local map boundaries…</p>;
  if (geometry.status === "error")
    return (
      <div role="alert" className="notice notice--error">
        <p>
          Map boundaries could not load. Recorded places remain available below.
        </p>
        <button type="button" onClick={retry}>
          Retry map boundaries
        </button>
      </div>
    );
  if (!("data" in geometry)) return null;
  const data = geometry.data;
  const { available, unavailable } = mapCoverage(territories, data);
  const maximum = Math.max(1, ...available.map((unit) => unit.identity_count));
  const counts = new Map(
    available.map((unit) => [unit.source_code, unit.identity_count]),
  );
  return (
    <figure className="native-map">
      {!available.length && (
        <p role="status" className="notice">
          {contributors
            ? "No selected species has mapped coverage in this filtered view. Use View only to inspect exact recorded places."
            : "No recorded range boundaries can be shown for this view. See the exact recorded places below."}
        </p>
      )}
      <svg
        viewBox={data.viewBox}
        role="img"
        aria-labelledby={`${id}-title ${id}-desc`}
      >
        <title id={`${id}-title`}>
          {selected
            ? "Recorded native-range map for selected species"
            : contributors
              ? "Selected species recorded native-range coverage map"
              : "Collection recorded native-range coverage map"}
        </title>
        <desc id={`${id}-desc`}>
          Shaded territory boundaries show{" "}
          {selected
            ? "the selected identity’s recorded structured range"
            : contributors
              ? "distinct selected species coverage"
              : "distinct represented identity coverage"}
          .{" "}
          {contributors
            ? "Territory counts and contributing species are available in the companion lists."
            : "Exact recorded places and coverage counts are available in the companion lists."}{" "}
          Unshaded areas do not establish absence.
        </desc>
        <rect width="720" height="360" fill="#edf3f1" />
        {Object.entries(data.units).map(([code, path]) => {
          const count = counts.get(code) ?? 0;
          return (
            <path
              key={code}
              d={path}
              fillRule="evenodd"
              fill={
                count
                  ? `hsl(151 35% ${String(72 - (40 * count) / maximum)}%)`
                  : "#d5dfd9"
              }
              stroke="#ffffff"
              strokeWidth="0.55"
            />
          );
        })}
      </svg>
      <figcaption>
        {selected ? (
          <p>Shading shows available boundaries for this recorded range.</p>
        ) : (
          <p className="native-legend">
            <span aria-hidden="true" />
            Lighter to darker: 1–{maximum} distinct{" "}
            {contributors ? "selected species" : "represented identities"} per
            territory map unit.
          </p>
        )}
        <p>
          Broad recorded places use descendant territories only to draw their
          area; those countries are not independently recorded native-range
          assertions. Unshaded means no mapped coverage in this view, not
          species absence.
        </p>
        <p className="field-help">
          Map boundaries:{" "}
          <a
            href="https://www.naturalearthdata.com/about/terms-of-use/"
            target="_blank"
            rel="noreferrer"
          >
            Natural Earth 5.1.1 · 1:110m · public domain
          </a>
          . Generalized de facto boundaries omit some small territories.
          Botanical facts are operator-managed Florabase reference knowledge.
        </p>
      </figcaption>
      {!selected && available.length > 0 && (
        <details className="native-coverage-list" open>
          <summary>Territory map coverage · {available.length} units</summary>
          <p className="field-help">
            Distinct identities whose recorded range covers each drawing unit.
            Counts describe presentation coverage, not plants, abundance,
            occurrences or material origins. One identity counts at most once
            per unit.
          </p>
          <ul>
            {available.map((unit) => (
              <li key={unit.id}>
                <span>{unit.name}</span>
                <strong>
                  {unit.identity_count}{" "}
                  {unit.identity_count === 1 ? "identity" : "identities"}
                </strong>
                {contributors && (
                  <span className="native-contributors">
                    Contributing species: {contributors[unit.id]?.join("; ")}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
      {unavailable.length > 0 && (
        <details>
          <summary>
            Map boundary unavailable · {unavailable.length} territories
          </summary>
          <p className="field-help">
            These canonical territory primitives have no boundary in this map.
            The exact recorded ranges remain valid.
          </p>
          <ul>
            {unavailable.map((unit) => (
              <li key={unit.id}>
                {unit.name} ({unit.source_code}) · {unit.identity_count}{" "}
                {unit.identity_count === 1 ? "identity" : "identities"}
                {contributors && (
                  <span>
                    {" "}
                    · Contributing species: {contributors[unit.id]?.join("; ")}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </figure>
  );
}
