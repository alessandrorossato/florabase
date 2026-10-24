import { ActionButton } from "../components/Action";
import { useId, useRef, useState, type RefObject, type ReactNode } from "react";
import { MapLegend } from "../maps/MapLegend";
import { TaskDialog } from "../components/TaskDialog";
import { BotanicalName } from "../components/ReferenceUI";
import { TerritoryInspector } from "./TerritoryInspector";
import type { Filters, RangeIdentity, Territory } from "./api";
import { coverageScale } from "./coverageScale";
import { mapCoverage, type Geometry } from "./geometry";

export type GeometryState =
  { status: "loading" | "error" } | { status: "ready"; data: Geometry };

export interface TerritorySelection {
  codes: string[];
  onChange: (codes: string[]) => void;
}

export function NativeCoverageMap({
  territories,
  geometry,
  selected = false,
  retry,
  contributors,
  coverageRef,
  filters,
  identities,
  comparisonIds,
  colors,
  remove,
  evidence,
  showEvidence,
  evidenceRef,
  territorySelection,
  scopeLabel,
}: {
  territorySelection?: TerritorySelection;
  scopeLabel?: string;
  territories: (Territory & { identity_ids?: string[] })[];
  geometry: GeometryState;
  selected?: boolean;
  retry: () => void;
  contributors?: Partial<Record<string, string[]>>;
  coverageRef?: RefObject<HTMLDivElement | null>;
  evidenceRef?: RefObject<HTMLButtonElement | null>;
  filters?: Filters;
  identities?: RangeIdentity[];
  comparisonIds?: string[];
  colors?: Record<string, string>;
  remove?: (id: string) => void;
  evidence?: ReactNode;
  showEvidence?: (id: string) => void;
}) {
  const id = useId();
  const [localCodes, setLocalCodes] = useState<string[]>([]);
  const inspectedCodes = territorySelection?.codes ?? localCodes;
  const setInspectedCodes = territorySelection?.onChange ?? setLocalCodes;
  const [aboutOpen, setAboutOpen] = useState(false);
  const [mobilePane, setMobilePane] = useState<"map" | "inspector">("map");
  function toggle(code: string) {
    setInspectedCodes(
      inspectedCodes.includes(code)
        ? inspectedCodes.filter((value) => value !== code)
        : [...inspectedCodes, code],
    );
  }
  const [focusedCode, setFocusedCode] = useState<string | null>(null);
  const [activeFocus, setActiveFocus] = useState<string | null>(null);
  const [hoveredCode, setHoveredCode] = useState<string | null>(null);
  const [previewDismissed, setPreviewDismissed] = useState(false);
  const paths = useRef(new Map<string, SVGPathElement>());
  if (!("data" in geometry))
    return (
      <section>
        {geometry.status === "loading" ? (
          <p role="status">Loading local map boundaries…</p>
        ) : (
          <div role="alert" className="notice notice--error">
            <p>
              Map boundaries could not load. Recorded places remain available.
            </p>
            <button type="button" onClick={retry}>
              Retry map boundaries
            </button>
          </div>
        )}
        <button
          ref={evidenceRef}
          type="button"
          onClick={() => {
            setAboutOpen(true);
          }}
        >
          About this map · recorded places and limits
        </button>
        {aboutOpen && (
          <TaskDialog
            title="Data and limitations"
            className="native-evidence-dialog"
            onClose={() => {
              setAboutOpen(false);
            }}
          >
            <ActionButton
              variant="secondary"
              type="button"
              onClick={() => {
                setAboutOpen(false);
              }}
            >
              Done
            </ActionButton>
            {evidence}
          </TaskDialog>
        )}
      </section>
    );
  const data = geometry.data;
  // Keep chosen territories visible even when a species/filter change removes their coverage.
  const regionNames = new Intl.DisplayNames(["en"], { type: "region" });
  const displayed = [
    ...territories,
    ...inspectedCodes
      .filter((code) => !territories.some((unit) => unit.source_code === code))
      .map((code) => ({
        id: `selected-${code}`,
        source_code: code,
        name: regionNames.of(code) ?? code,
        identity_count: 0,
        identity_ids: [] as string[],
      })),
  ];
  const { available, unavailable } = mapCoverage(displayed, data);
  const maximum = Math.max(0, ...available.map((unit) => unit.identity_count));
  const bins = coverageScale(maximum);
  const units = new Map(available.map((unit) => [unit.source_code, unit]));
  const inspected = inspectedCodes;
  const colorLayers = Boolean(
    colors && identities?.length && identities.length <= 5,
  );
  const preview = previewDismissed
    ? undefined
    : units.get(hoveredCode ?? activeFocus ?? "");
  const tabCode = units.has(focusedCode ?? "")
    ? focusedCode
    : available[0]?.source_code;
  const outlines = [
    ...new Set([...inspected, hoveredCode, activeFocus]),
  ].filter((code): code is string => Boolean(code && units.has(code)));
  const title = selected
    ? "Recorded native-range map for selected species"
    : contributors
      ? "Selected species recorded native-range coverage map"
      : "Collection recorded native-range coverage map";
  function unitLabel(unit: Territory) {
    return `${unit.name} · ${String(unit.identity_count)} ${unit.identity_count === 1 ? "identity" : "identities"}`;
  }
  return (
    <>
      <div
        className="native-mobile-spatial-switch"
        role="group"
        aria-label="Map and inspector panels"
      >
        <button
          type="button"
          className="button--secondary"
          aria-pressed={mobilePane === "map"}
          aria-controls={`${id}-map-pane`}
          onClick={() => {
            setMobilePane("map");
          }}
        >
          Show map
        </button>
        <button
          type="button"
          className="button--secondary"
          aria-pressed={mobilePane === "inspector"}
          aria-controls={`${id}-inspector-pane`}
          onClick={() => {
            setMobilePane("inspector");
          }}
        >
          Show territory inspector ({inspected.length})
        </button>
      </div>
      <span className="sr-only" aria-live="polite">
        Selected territories:{" "}
        {inspected
          .map(
            (code) =>
              displayed.find((unit) => unit.source_code === code)?.name ?? code,
          )
          .join(", ") || "none"}
      </span>
      <div className="native-spatial-workspace" data-mobile-pane={mobilePane}>
        <figure id={`${id}-map-pane`} className="native-map">
          {!available.length && (
            <p role="status" className="notice">
              {contributors
                ? "No chosen species has mapped coverage in this filtered view. Use Places to inspect exact recorded evidence."
                : "No recorded range boundaries can be shown for this view. See the exact recorded places below."}
            </p>
          )}
          <div className="native-map-canvas">
            <svg
              viewBox={data.viewBox}
              role="group"
              aria-labelledby={`${id}-title`}
              aria-describedby={`${id}-desc`}
            >
              <title id={`${id}-title`}>{title}</title>
              <desc id={`${id}-desc`}>
                Covered territory buttons show recorded native-range coverage.
                Arrow keys, Home and End move between covered territories; Enter
                or Space toggles a territory. Multiple territories can stay
                selected. Escape dismisses the preview. The territory chooser
                provides the same selection and exact counts. Unshaded areas do
                not establish absence.
              </desc>
              <defs>
                {colorLayers &&
                  available.map((unit) => {
                    const ids = (
                      unit.identity_ids ??
                      identities
                        ?.filter(
                          (identity) =>
                            identities.length === 1 && identity.matches_filters,
                        )
                        .map((identity) => identity.id) ??
                      []
                    ).filter((key) => colors?.[key]);
                    if (ids.length < 2) return null;
                    return (
                      <pattern
                        key={unit.source_code}
                        id={`${id}-overlap-${unit.source_code}`}
                        patternUnits="userSpaceOnUse"
                        width={ids.length * 5}
                        height={ids.length * 5}
                        patternTransform="rotate(35)"
                      >
                        {ids.map((key, index) => (
                          <rect
                            key={key}
                            x={index * 5}
                            y="0"
                            width="5"
                            height={ids.length * 5}
                            fill={colors?.[key]}
                          />
                        ))}
                      </pattern>
                    );
                  })}
                {outlines.map((code) => (
                  <clipPath id={`${id}-clip-${code}`} key={code}>
                    <path
                      d={data.units[code]}
                      fillRule="evenodd"
                      clipRule="evenodd"
                    />
                  </clipPath>
                ))}
              </defs>
              <rect width="720" height="360" className="native-map-water" />
              <g aria-hidden="true" className="native-land-layer">
                {Object.entries(data.units).map(([code, path]) => (
                  <path key={code} d={path} fillRule="evenodd" />
                ))}
              </g>
              <g className="native-coverage-layer">
                {available.map((unit) => {
                  const code = unit.source_code;
                  return (
                    <path
                      key={code}
                      d={data.units[code]}
                      fillRule="evenodd"
                      fill={
                        unit.identity_count === 0
                          ? "var(--native-land)"
                          : colorLayers
                            ? (() => {
                                const ids = (
                                  unit.identity_ids ??
                                  identities
                                    ?.filter(
                                      (identity) =>
                                        identities.length === 1 &&
                                        identity.matches_filters,
                                    )
                                    .map((identity) => identity.id) ??
                                  []
                                ).filter((key) => colors?.[key]);
                                return ids.length > 1
                                  ? `url(#${id}-overlap-${code})`
                                  : colors?.[ids[0]];
                              })()
                            : bins.find((bin) => unit.identity_count <= bin.to)
                                ?.color
                      }
                      className="native-territory"
                      ref={(element) => {
                        if (element) paths.current.set(code, element);
                        else paths.current.delete(code);
                      }}
                      role="button"
                      tabIndex={code === tabCode ? 0 : -1}
                      aria-label={unitLabel(unit)}
                      aria-describedby={
                        preview?.source_code === code
                          ? `${id}-preview`
                          : undefined
                      }
                      aria-pressed={inspected.includes(code)}
                      onFocus={() => {
                        setFocusedCode(code);
                        setActiveFocus(code);
                        setPreviewDismissed(false);
                      }}
                      onBlur={() => {
                        setActiveFocus(null);
                      }}
                      onMouseEnter={() => {
                        setHoveredCode(code);
                        setPreviewDismissed(false);
                      }}
                      onMouseLeave={() => {
                        setHoveredCode(null);
                      }}
                      onClick={() => {
                        toggle(code);
                        setFocusedCode(code);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          setPreviewDismissed(true);
                          return;
                        }
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          toggle(code);
                          return;
                        }
                        const index = available.findIndex(
                          (item) => item.source_code === code,
                        );
                        let next: number;
                        if (event.key === "Home") next = 0;
                        else if (event.key === "End")
                          next = available.length - 1;
                        else if (
                          event.key === "ArrowRight" ||
                          event.key === "ArrowDown"
                        )
                          next = (index + 1) % available.length;
                        else if (
                          event.key === "ArrowLeft" ||
                          event.key === "ArrowUp"
                        )
                          next =
                            (index + available.length - 1) % available.length;
                        else return;
                        event.preventDefault();
                        paths.current.get(available[next].source_code)?.focus();
                      }}
                    />
                  );
                })}
              </g>
              {/* Fixed boundaries never compete with interactive fills or thicker selected edges. */}
              <g
                className="native-boundary-layer"
                aria-hidden="true"
                pointerEvents="none"
              >
                {Object.entries(data.units).map(([code, path]) => (
                  <path
                    key={code}
                    d={path}
                    fill="none"
                    vectorEffect="non-scaling-stroke"
                  />
                ))}
              </g>
              {/* Clip emphasis inside its own territory, above every fill; neighboring land is untouched. */}
              <g
                className="native-emphasis-layer"
                aria-hidden="true"
                pointerEvents="none"
              >
                {outlines.map((code) => (
                  <g key={code} clipPath={`url(#${id}-clip-${code})`}>
                    <path
                      className="native-emphasis-casing"
                      d={data.units[code]}
                      fill="none"
                      vectorEffect="non-scaling-stroke"
                    />
                    {inspected.includes(code) && (
                      <path
                        className="native-selected-outline"
                        d={data.units[code]}
                        fill="none"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                    {code === hoveredCode && (
                      <path
                        className="native-hover-outline"
                        d={data.units[code]}
                        fill="none"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                    {code === activeFocus && (
                      <path
                        className="native-focus-outline"
                        d={data.units[code]}
                        fill="none"
                        vectorEffect="non-scaling-stroke"
                      />
                    )}
                  </g>
                ))}
              </g>
            </svg>
            {preview && (
              <div
                id={`${id}-preview`}
                role="tooltip"
                className="native-map-preview"
              >
                <strong>{preview.name}</strong>
                <span>
                  {preview.identity_count}{" "}
                  {contributors
                    ? "selected species"
                    : preview.identity_count === 1
                      ? "represented identity"
                      : "represented identities"}
                </span>
                {contributors?.[preview.id] && (
                  <small>
                    {(contributors[preview.id] ?? []).slice(0, 3).join(" · ")}
                    {(contributors[preview.id] ?? []).length > 3 ? " · …" : ""}
                  </small>
                )}
                <small>Drawing coverage</small>
              </div>
            )}
          </div>
          <figcaption>
            {identities && (
              <ul
                className="native-comparison-legend"
                aria-label="Comparison species and colors"
              >
                {identities.map((identity) => (
                  <li key={identity.id}>
                    {colorLayers && (
                      <span
                        className="native-color-key"
                        style={{ background: colors?.[identity.id] }}
                        aria-hidden="true"
                      />
                    )}
                    <span>
                      <BotanicalName
                        label={identity.display_label}
                        scientificName={identity.scientific_name}
                      />
                      {!identity.matches_filters ? (
                        <small>Excluded by active filters</small>
                      ) : !identity.native_range_count ? (
                        <small>No structured native range recorded</small>
                      ) : null}
                    </span>
                    {showEvidence && (
                      <button
                        type="button"
                        className="button--quiet"
                        onClick={() => {
                          showEvidence(identity.id);
                        }}
                        aria-label={`Recorded places for ${identity.display_label}`}
                      >
                        Places
                      </button>
                    )}
                    {remove && (
                      <button
                        type="button"
                        className="button--quiet"
                        onClick={() => {
                          remove(identity.id);
                        }}
                        aria-label={`Remove ${identity.display_label}`}
                      >
                        ×
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {colorLayers ? (
              <p className="field-help native-overlap-key">
                <span className="native-overlap-swatch" aria-hidden="true" />
                Stripes combine the colors of all contributing species (2–5).
                Solid color: one species. Inspect for names and counts.
              </p>
            ) : (
              <MapLegend
                label={
                  selected
                    ? "Recorded range"
                    : contributors
                      ? "Distinct selected species per territory"
                      : "Distinct represented identities per territory"
                }
                items={[
                  ...(selected && available.length
                    ? [
                        {
                          label: "Recorded coverage",
                          color: "var(--native-count-high)",
                        },
                      ]
                    : bins),
                  { label: "No mapped coverage", color: "var(--native-land)" },
                ]}
              />
            )}
            <p className="field-help native-map-caption">
              <span>
                Unshaded means no mapped coverage in this view, not species
                absence.
              </span>
              <span>
                Map boundaries:{" "}
                <a
                  href="https://www.naturalearthdata.com/about/terms-of-use/"
                  target="_blank"
                  rel="noreferrer"
                >
                  Natural Earth 5.1.1 · 1:110m · public domain
                </a>
                .
              </span>
            </p>
          </figcaption>
          <button
            ref={evidenceRef}
            type="button"
            className="button--quiet"
            aria-haspopup="dialog"
            onClick={() => {
              setAboutOpen(true);
            }}
          >
            About this map · recorded places and limits
          </button>
        </figure>
        <div id={`${id}-inspector-pane`} ref={coverageRef} tabIndex={-1}>
          <TerritoryInspector
            territories={displayed}
            unavailableCodes={unavailable.map((unit) => unit.source_code)}
            codes={inspected}
            toggle={(code) => {
              toggle(code);
              setFocusedCode(code);
            }}
            clear={() => {
              setInspectedCodes([]);
              paths.current.get(inspected.at(-1) ?? "")?.focus();
            }}
            filters={filters}
            scopeLabel={scopeLabel}
            identities={identities}
            comparisonIds={comparisonIds}
            evidence={showEvidence}
          />
        </div>
      </div>
      {aboutOpen && (
        <TaskDialog
          title="Data and limitations"
          onClose={() => {
            setAboutOpen(false);
          }}
          dismissOnBackdrop
          className="native-evidence-dialog"
        >
          <div className="section-heading">
            <h3>Data and limitations</h3>
            <ActionButton
              variant="secondary"
              type="button"
              onClick={() => {
                setAboutOpen(false);
              }}
            >
              Done
            </ActionButton>
          </div>
          <p>
            Broad recorded places use descendant territories only to draw their
            area; those countries are not independently recorded native-range
            assertions. Counts describe distinct Botanical Identities, not
            plants, abundance, occurrences or material origins. Custom places
            never inherit a parent polygon.
          </p>
          {unavailable.length > 0 && (
            <section>
              <h4>
                Map boundary unavailable · {unavailable.length} territories
              </h4>
              <ul>
                {unavailable.map((unit) => (
                  <li key={unit.id}>
                    {unit.name} ({unit.source_code}) · {unit.identity_count}{" "}
                    identities
                  </li>
                ))}
              </ul>
            </section>
          )}
          {evidence ?? (
            <p>
              Use Places beside a comparison species, or its Botanical Identity
              details, to inspect exact recorded places, including broad and
              unmapped places.
            </p>
          )}
        </TaskDialog>
      )}
    </>
  );
}
