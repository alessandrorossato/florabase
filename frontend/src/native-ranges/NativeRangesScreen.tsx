import { GeographyHeader } from "../geography/GeographyHeader";
import { ActionLink, ActionButton } from "../components/Action";
import {
  DirectoryFilterSelect,
  DirectoryTools,
} from "../components/DirectoryTools";
import { TaskDialog } from "../components/TaskDialog";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { BotanicalName, DirectorySearch } from "../components/ReferenceUI";
import { SavedViews } from "../saved-views/SavedViews";
import {
  directoryState,
  recordCategories,
  type RecordCategory,
} from "../saved-views/state";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import {
  getNativeOverview,
  getNativeComparison,
  getNativeSelection,
  listNativeIdentities,
  type Overview,
  type SelectedRanges,
  type Filters,
  type PlaceCoverage,
  type RangeIdentity,
  type RangePlace,
} from "./api";
import { loadGeometry, mapCoverage, rangeGeometry } from "./geometry";
import {
  NativeCoverageMap,
  type GeometryState,
  type TerritorySelection,
} from "./NativeCoverageMap";
import { reconcileColors } from "./comparison";
import { MapWorkspace } from "../maps/MapWorkspace";
import "./native-ranges.css";

const scopes = [
  { value: "all", label: "All represented" },
  { value: "living", label: "Living" },
  { value: "current", label: "Current" },
  { value: "historical", label: "Historical" },
] as const;

function useLocalRead<T>(read: (signal: AbortSignal) => Promise<T>) {
  const auth = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    read: typeof read;
    attempt: number;
    data?: T;
    error?: "missing" | "failed";
  } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void read(controller.signal)
        .then((data) => {
          if (!controller.signal.aborted) setResult({ read, attempt, data });
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return;
          if (error instanceof ApiError && error.status === 401)
            auth.sessionExpired();
          else
            setResult({
              read,
              attempt,
              error:
                error instanceof ApiError && error.status === 404
                  ? "missing"
                  : "failed",
            });
        });
    }, 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [read, attempt, auth]);
  const current =
    result?.read === read && result.attempt === attempt ? result : null;
  return {
    data: current?.data,
    error: current?.error,
    retry: () => {
      setAttempt((value) => value + 1);
    },
  };
}

function ReadError({ retry, label }: { retry: () => void; label: string }) {
  return (
    <div role="alert" className="notice notice--error">
      <p>Could not load {label}.</p>
      <button type="button" onClick={retry}>
        Retry {label}
      </button>
    </div>
  );
}

function Pages({
  offset,
  total,
  onChange,
  label,
}: {
  offset: number;
  total: number;
  onChange: (offset: number) => void;
  label: string;
}) {
  if (offset === 0 && total <= 50) return null;
  return (
    <nav className="actions native-pages" aria-label={label}>
      <button
        type="button"
        className="button--secondary"
        disabled={offset === 0}
        onClick={() => {
          onChange(Math.max(0, offset - 50));
        }}
      >
        Previous
      </button>
      <span>Page {Math.floor(offset / 50) + 1}</span>
      <button
        type="button"
        className="button--secondary"
        disabled={offset + 50 >= total || offset >= 100000}
        onClick={() => {
          onChange(offset + 50);
        }}
      >
        Next
      </button>
    </nav>
  );
}

function Representation({
  identity,
  compact = false,
}: {
  identity: RangeIdentity;
  compact?: boolean;
}) {
  return (
    <span className="native-representation">
      <strong>
        {identity.representation === "living"
          ? "Living"
          : identity.representation === "current"
            ? "Current"
            : "Historical"}
      </strong>
      {!compact && (
        <span>
          {identity.current_records} current · {identity.retained_records}{" "}
          retained records
        </span>
      )}
    </span>
  );
}

function IdentityBrowser({
  filters,
  selectedIds,
  select,
}: {
  filters: Filters;
  selectedIds: string[];
  select: (id: string) => void;
}) {
  const [offset, setOffset] = useState(0);
  const read = useCallback(
    (signal: AbortSignal) => listNativeIdentities(filters, offset, signal),
    [filters, offset],
  );
  const query = useLocalRead(read);
  return (
    <section
      className="native-browser"
      aria-labelledby="native-identities-title"
    >
      <h3 id="native-identities-title" className="sr-only">
        Represented species
      </h3>
      {selectedIds.length >= 5 && (
        <p role="status" className="field-help">
          Selection limit reached; remove a species to choose another.
        </p>
      )}
      {query.error ? (
        <ReadError retry={query.retry} label="represented species" />
      ) : !query.data ? (
        <p role="status">Loading represented species…</p>
      ) : (
        <>
          <p className="directory-results" role="status">
            {query.data.total} represented identities
          </p>
          {!query.data.items.length ? (
            <p className="empty-state">
              No represented identities match these filters.
            </p>
          ) : (
            <ul className="native-identities">
              {query.data.items.map((identity) => (
                <li key={identity.id}>
                  <label className="native-identity">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(identity.id)}
                      disabled={
                        selectedIds.length >= 5 &&
                        !selectedIds.includes(identity.id)
                      }
                      onChange={() => {
                        select(identity.id);
                      }}
                    />
                    <span className="native-identity-content">
                      <strong>
                        <BotanicalName
                          label={identity.display_label}
                          scientificName={identity.scientific_name}
                        />
                      </strong>
                      {identity.common_name && (
                        <span>{identity.common_name}</span>
                      )}
                      <Representation identity={identity} compact />
                      <small>
                        {identity.native_range_count
                          ? `${String(identity.native_range_count)} recorded native-range ${identity.native_range_count === 1 ? "place" : "places"}`
                          : "No structured native range recorded"}
                        {selectedIds.includes(identity.id) ? " · Selected" : ""}
                      </small>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}
          <Pages
            offset={offset}
            total={query.data.total}
            onChange={setOffset}
            label="Represented species pages"
          />
        </>
      )}
    </section>
  );
}

function RangeList({
  places,
  geometry,
  overview = false,
}: {
  places: (RangePlace | PlaceCoverage)[];
  geometry: GeometryState;
  overview?: boolean;
}) {
  return (
    <ul className="native-recorded-places">
      {places.map((place) => {
        const broad =
          place.place_kind === "canonical" &&
          place.source_code_type === "un_m49";
        const mapping =
          "data" in geometry ? rangeGeometry(place, geometry.data) : null;
        const unavailable =
          place.place_kind === "custom" ||
          !["un_m49", "iso_3166_1_alpha_2"].includes(
            place.source_code_type ?? "",
          );
        return (
          <li key={place.id}>
            <div className="native-place-heading">
              <strong>{place.name}</strong>
              {overview && "identity_count" in place && (
                <span>
                  {place.identity_count}{" "}
                  {place.identity_count === 1 ? "identity" : "identities"}
                </span>
              )}
            </div>
            <small>{place.display_path}</small>
            <span className="field-help">
              {place.place_kind === "custom"
                ? "Custom recorded place"
                : broad
                  ? "Broad recorded range"
                  : "Recorded territory / named area"}{" "}
              ·{" "}
              {unavailable || (mapping && !mapping.codes.length)
                ? "Map boundary unavailable"
                : mapping
                  ? mapping.missing.length
                    ? `Partial map: ${String(mapping.codes.length)} of ${String(mapping.codes.length + mapping.missing.length)} territory boundaries available`
                    : "Map boundary available"
                  : geometry.status === "error"
                    ? "Map boundaries unavailable while the asset cannot load"
                    : "Checking local map boundaries…"}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

interface MapProps {
  territorySelection?: TerritorySelection;
  geometry: GeometryState;
  retryGeometry: () => void;
}
function revealDetails(element: HTMLElement | null) {
  if (!element) return;
  element.focus();
  element.scrollIntoView({ block: "start" });
}

function NativeMetric({
  label,
  value,
  context,
  onClick,
}: {
  label: string;
  value: number | string;
  context: string;
  onClick?: () => void;
}) {
  const compactLabels: Record<string, string> = {
    "Represented identities": "Represented",
    "With recorded native range": "With ranges",
    "Without structured range": "Without ranges",
    "Mapped territories": "Territories",
    "Exact recorded places": "Recorded places",
  };
  const content = (
    <>
      <span className="ui-metric__label native-metric-label-full">{label}</span>
      <span
        className="ui-metric__label native-metric-label-short"
        aria-hidden="true"
      >
        {compactLabels[label] ?? label}
      </span>
      <strong className="ui-metric__value">{value}</strong>
      <span className="ui-metric__context">{context}</span>
    </>
  );
  return onClick ? (
    <button
      type="button"
      className="ui-metric native-metric"
      aria-label={`${label}: ${String(value)}`}
      onClick={onClick}
    >
      {content}
    </button>
  ) : (
    <div
      className="ui-metric native-metric"
      role="group"
      aria-label={`${label}: ${String(value)}`}
    >
      {content}
    </div>
  );
}

function RecordedEvidence({
  filters,
  geometry,
  id,
}: {
  filters: Filters;
  geometry: GeometryState;
  id?: string;
}) {
  const [offset, setOffset] = useState(0);
  const read = useCallback(
    (signal: AbortSignal): Promise<Overview | SelectedRanges> =>
      id
        ? getNativeSelection(id, filters, offset, signal)
        : getNativeOverview(filters, offset, signal),
    [id, filters, offset],
  );
  const query = useLocalRead<Overview | SelectedRanges>(read);
  if (query.error)
    return <ReadError retry={query.retry} label="recorded places" />;
  if (!query.data) return <p role="status">Loading recorded places…</p>;
  const places = "ranges" in query.data ? query.data.ranges : query.data.places;
  const total =
    "total" in query.data ? query.data.total : query.data.places_total;
  return (
    <>
      <h4>
        {id ? "Recorded native range" : "Exact recorded places"} · {total}{" "}
        {id ? (total === 1 ? "place" : "places") : ""}
      </h4>
      <p className="field-help">
        Explicit broad, precise and custom places remain separate evidence.
        Counts cannot be added to infer map coverage.
      </p>
      <RangeList places={places} geometry={geometry} overview={!id} />
      <Pages
        offset={offset}
        total={total}
        onChange={setOffset}
        label={id ? "Selected native-range pages" : "Recorded place pages"}
      />
    </>
  );
}

function OverviewPanel({
  territorySelection,
  filters,
  geometry,
  retryGeometry,
  choose,
}: MapProps & {
  filters: Filters;
  choose: (withRange?: boolean) => void;
}) {
  const coverage = useRef<HTMLDivElement>(null);
  const places = useRef<HTMLButtonElement>(null);
  const read = useCallback(
    (signal: AbortSignal) => getNativeOverview(filters, 0, signal),
    [filters],
  );
  const query = useLocalRead(read);
  if (query.error)
    return <ReadError retry={query.retry} label="collection overview" />;
  if (!query.data) return <p role="status">Loading collection overview…</p>;
  const overview = query.data;
  const mapped =
    "data" in geometry
      ? mapCoverage(overview.territories, geometry.data)
      : null;
  return (
    <>
      <h3 className="sr-only">Collection overview</h3>
      <div
        className="native-statistics"
        role="group"
        aria-label="Native-range coverage summary"
      >
        <NativeMetric
          label="Represented identities"
          value={overview.represented}
          context="Browse species →"
          onClick={() => {
            choose();
          }}
        />
        <NativeMetric
          label="With recorded native range"
          value={overview.with_range}
          context="Browse ranged species →"
          onClick={() => {
            choose(true);
          }}
        />
        <NativeMetric
          label="Without structured range"
          value={overview.without_range}
          context="Reference knowledge not recorded"
        />
        <NativeMetric
          label="Mapped territories"
          value={
            mapped
              ? mapped.available.length
              : geometry.status === "error"
                ? "—"
                : "…"
          }
          context={
            mapped
              ? `${String(mapped.unavailable.length)} boundaries unavailable${mapped.available.length ? " · Details →" : ""}`
              : geometry.status === "error"
                ? "Boundaries unavailable"
                : "Checking boundaries"
          }
          onClick={
            mapped?.available.length
              ? () => {
                  revealDetails(coverage.current);
                }
              : undefined
          }
        />
        <NativeMetric
          label="Exact recorded places"
          value={overview.places_total}
          context={
            overview.places_total
              ? "Broad, precise and custom →"
              : "No recorded places"
          }
          onClick={
            overview.places_total
              ? () => {
                  places.current?.click();
                }
              : undefined
          }
        />
      </div>
      {overview.represented === 0 ? (
        <p className="empty-state" role="status">
          No represented identities match this collection view. Reference-only
          identities are excluded.
        </p>
      ) : overview.with_range === 0 ? (
        <p className="empty-state" role="status">
          None of these represented identities has a structured native range
          recorded. Select a species to edit its recorded range.
        </p>
      ) : (
        <>
          <NativeCoverageMap
            territorySelection={territorySelection}
            territories={overview.territories}
            geometry={geometry}
            retry={retryGeometry}
            coverageRef={coverage}
            filters={filters}
            evidenceRef={places}
            evidence={
              <RecordedEvidence filters={filters} geometry={geometry} />
            }
          />
        </>
      )}
    </>
  );
}

function SelectedPanel({
  territorySelection,
  id,
  filters,
  geometry,
  retryGeometry,
  colors,
  remove,
  evidenceOnly = false,
}: MapProps & {
  id: string;
  filters: Filters;
  colors?: Record<string, string>;
  remove?: (id: string) => void;
  evidenceOnly?: boolean;
}) {
  const read = useCallback(
    (signal: AbortSignal) => getNativeSelection(id, filters, 0, signal),
    [id, filters],
  );
  const query = useLocalRead(read);
  if (query.error === "missing")
    return (
      <div role="alert" className="notice">
        <p>
          The selected identity is missing or no longer represented in your
          collection. Clear the selection or choose another species.
        </p>
        <p className="field-help">Selected identity: {id}</p>
      </div>
    );
  if (query.error)
    return <ReadError retry={query.retry} label="selected species" />;
  if (!query.data) return <p role="status">Loading selected species…</p>;
  const { identity, territories, total } = query.data;
  const recorded = (
    <RecordedEvidence filters={filters} geometry={geometry} id={id} />
  );
  if (evidenceOnly)
    return (
      <section>
        <h3>
          <BotanicalName
            label={identity.display_label}
            scientificName={identity.scientific_name}
          />
        </h3>
        {recorded}
        <ActionLink icon="edit" href={`#/identities/${id}?tab=native-range`}>
          Edit recorded range
        </ActionLink>
      </section>
    );
  return (
    <>
      <h3>
        <BotanicalName
          label={identity.display_label}
          scientificName={identity.scientific_name}
        />
      </h3>
      {!identity.matches_scope || !identity.matches_filters ? (
        <p role="status" className="notice">
          The selected identity no longer matches these collection filters.
          Change the filters or clear the selection.
        </p>
      ) : total === 0 ? (
        <div className="empty-state" role="status">
          <h4>No structured native range recorded</h4>
          <p>
            Use Edit recorded range to open the existing native-range manager in
            Reference details. Distribution prose and occurrence evidence are
            not mapped.
          </p>
        </div>
      ) : (
        <>
          <NativeCoverageMap
            territorySelection={territorySelection}
            territories={territories}
            geometry={geometry}
            selected
            retry={retryGeometry}
            filters={filters}
            identities={[identity]}
            comparisonIds={[id]}
            colors={colors}
            remove={remove}
            evidence={recorded}
          />
        </>
      )}
      {identity.common_name && <p>{identity.common_name}</p>}
      <Representation identity={identity} />
      <div className="actions native-links">
        <a href={`#/identities/${id}?tab=reference`}>
          Botanical identity details
        </a>
        <ActionLink icon="edit" href={`#/identities/${id}?tab=native-range`}>
          Edit recorded range
        </ActionLink>
        <a href={`#/species-distribution?identity=${id}`}>
          View occurrence distribution
        </a>
      </div>
    </>
  );
}

function ComparisonPanel({
  territorySelection,
  ids,
  filters,
  geometry,
  retryGeometry,
  remove,
  only,
  colors,
}: MapProps & {
  ids: string[];
  filters: Filters;
  remove: (id: string) => void;
  only: (id: string) => void;
  colors?: Record<string, string>;
}) {
  const read = useCallback(
    (signal: AbortSignal) => getNativeComparison(ids, filters, signal),
    [ids, filters],
  );
  const query = useLocalRead(read);
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  if (query.error)
    return (
      <ReadError retry={query.retry} label="selected species comparison" />
    );
  if (!query.data)
    return <p role="status">Loading selected species comparison…</p>;
  const { identities, missing_ids, territories } = query.data;
  const labels = new Map(
    identities.map((identity) => [identity.id, identity.display_label]),
  );
  const contributors = Object.fromEntries(
    territories.map((unit) => [
      unit.id,
      unit.identity_ids.map((id) => labels.get(id) ?? id),
    ]),
  );
  return (
    <>
      <h3 className="sr-only">Selected species comparison</h3>
      {ids.length > 5 && (
        <p role="status" className="notice">
          This saved selection contains {ids.length} identities. All are
          preserved in count-based coverage. Remove identities explicitly to use
          five-color comparison.
        </p>
      )}
      <NativeCoverageMap
        territorySelection={territorySelection}
        territories={territories}
        contributors={contributors}
        geometry={geometry}
        retry={retryGeometry}
        filters={filters}
        identities={identities}
        comparisonIds={ids}
        colors={ids.length <= 5 ? colors : undefined}
        remove={remove}
        showEvidence={setEvidenceId}
      />
      <p className="field-help">
        Each territory counts distinct selected species that match the filters.
        Overlapping recorded ranges count once per species.
      </p>
      {missing_ids.map((id) => (
        <p key={id}>
          Missing or no longer represented: {id}{" "}
          <button
            type="button"
            onClick={() => {
              remove(id);
            }}
          >
            Remove {id}
          </button>
        </p>
      ))}
      {identities.length === 1 && (
        <button
          type="button"
          className="button--quiet"
          onClick={() => {
            only(identities[0].id);
          }}
        >
          View only {identities[0].display_label}
        </button>
      )}
      {evidenceId && (
        <TaskDialog
          title="Recorded native-range evidence"
          className="native-evidence-dialog"
          dismissOnBackdrop
          onClose={() => {
            setEvidenceId(null);
          }}
        >
          <ActionButton
            variant="secondary"
            type="button"
            onClick={() => {
              setEvidenceId(null);
            }}
          >
            Done
          </ActionButton>
          <SelectedPanel
            id={evidenceId}
            filters={filters}
            geometry={geometry}
            retryGeometry={retryGeometry}
            evidenceOnly
          />
        </TaskDialog>
      )}
    </>
  );
}

const categoryLabels: Record<RecordCategory, string> = {
  seed_lot: "Seeds",
  sowing: "Sowings",
  plant: "Plants",
  plant_group: "Plant groups",
  stored_material: "Stored material",
};

export function NativeRangesScreen() {
  const [territoryCodes, setTerritoryCodes] = useState<string[]>([]);
  const territorySelection = {
    codes: territoryCodes,
    onChange: setTerritoryCodes,
  };
  const [navigation, setNavigation] = useState(0);
  const reset = useCallback(() => {
    setNavigation((value) => value + 1);
    setTerritoryCodes([]);
  }, []);
  const view = useDirectoryView("native_ranges", reset);
  const {
    q,
    scope,
    mode,
    identity: selectedIds,
    withRange,
    record,
  } = view.state;
  const [colorState, setColorState] = useState<{
    ids: string;
    colors: Record<string, string>;
  }>({ ids: "", colors: {} });
  const colorKey = selectedIds.join(",");
  if (colorState.ids !== colorKey)
    setColorState({
      ids: colorKey,
      colors: reconcileColors(selectedIds, colorState.colors),
    });
  const colors = colorState.colors;
  const filters = useMemo(
    () => ({ q, scope, withRange, record }),
    [q, scope, withRange, record],
  );
  const [geometryAttempt, setGeometryAttempt] = useState(0);
  const [geometryResult, setGeometryResult] = useState<{
    attempt: number;
    state: GeometryState;
  } | null>(null);
  const geometry: GeometryState =
    geometryResult?.attempt === geometryAttempt
      ? geometryResult.state
      : { status: "loading" };
  const speciesMode = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    let active = true;
    void loadGeometry()
      .then((data) => {
        if (active)
          setGeometryResult({
            attempt: geometryAttempt,
            state: { status: "ready", data },
          });
      })
      .catch(() => {
        if (active)
          setGeometryResult({
            attempt: geometryAttempt,
            state: { status: "error" },
          });
      });
    return () => {
      active = false;
    };
  }, [geometryAttempt]);
  const retryGeometry = () => {
    setGeometryAttempt((value) => value + 1);
  };
  const queryKey = JSON.stringify([q, scope, withRange, record, navigation]);
  const rawIds = new URLSearchParams(
    window.location.hash.split("?", 2)[1],
  ).getAll("identity");
  const invalidSelection =
    rawIds.length > 0 && !directoryState("native_ranges", { identity: rawIds });
  const remove = (id: string) => {
    view.update(
      "identity",
      selectedIds.filter((value) => value !== id),
    );
    speciesMode.current?.focus();
  };
  const [chooserOpen, setChooserOpen] = useState(false);
  const chooserTrigger = useRef<HTMLButtonElement>(null);
  const chooserInvoker = useRef<HTMLElement | null>(null);
  const closeChooser = () => {
    setChooserOpen(false);
    // A filter or selection can replace the KPI that opened the dialog.
    requestAnimationFrame(() => {
      if (!chooserInvoker.current?.isConnected) chooserTrigger.current?.focus();
    });
  };
  const choose = (ranged = false) => {
    chooserInvoker.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    if (ranged) view.update("withRange", true);
    setChooserOpen(true);
  };
  const resetFilters = () => {
    view.replace({ ...view.state, scope: "all", record: [], withRange: false });
  };
  return (
    <section
      className="workspace native-ranges"
      aria-labelledby="geography-native-ranges-title"
    >
      <GeographyHeader
        view="native-ranges"
        description="Structured botanical ranges, distinct from occurrences and material origins."
        actions={null}
        tools={
          <DirectoryTools
            name="Native ranges"
            search={
              <DirectorySearch
                id="native-species-search"
                label="Search species"
                hideLabel
                placeholder="Scientific name, common name or cultivar"
                value={q}
                onChange={(value) => {
                  view.update("q", Array.from(value).slice(0, 200).join(""));
                }}
              />
            }
            savedViews={
              <SavedViews
                surface="native_ranges"
                state={view.savedState}
                presentation="dialog"
              />
            }
            actions={
              <button
                type="button"
                className="button--secondary"
                ref={chooserTrigger}
                aria-haspopup="dialog"
                aria-expanded={chooserOpen}
                onClick={() => {
                  choose();
                }}
              >
                Choose species
              </button>
            }
            filters={
              <>
                <div className="representation-filter">
                  <DirectoryFilterSelect
                    label="Collection representation"
                    value={scope}
                    options={scopes}
                    onChange={(scope) => {
                      view.update("scope", scope);
                    }}
                  />
                </div>
                <p className="field-help">
                  Living includes active Plants and Plant groups. Current also
                  includes active seeds, sowings and managed stored material.
                  Historical has retained evidence with no current material.
                </p>
                <fieldset className="native-category-filters">
                  <legend>Collection records</legend>
                  <p className="field-help">
                    Choose any record types (OR). None selected includes all
                    types within the status above.
                  </p>
                  {recordCategories.map((category) => (
                    <label key={category}>
                      <input
                        type="checkbox"
                        checked={record.includes(category)}
                        onChange={() => {
                          view.update(
                            "record",
                            recordCategories.filter((value) =>
                              value === category
                                ? !record.includes(value)
                                : record.includes(value),
                            ),
                          );
                        }}
                      />
                      {categoryLabels[category]}
                    </label>
                  ))}
                </fieldset>
                <label className="native-range-only">
                  <input
                    type="checkbox"
                    checked={withRange}
                    onChange={(event) => {
                      view.update("withRange", event.currentTarget.checked);
                    }}
                  />
                  With native range only
                </label>
              </>
            }
            onReset={resetFilters}
            activeFilters={[
              ...(q
                ? [
                    {
                      label: "Search",
                      value: q,
                      onRemove: () => {
                        view.update("q", "");
                      },
                    },
                  ]
                : []),
              ...(scope !== "all"
                ? [
                    {
                      label: "Representation",
                      value:
                        scopes.find((item) => item.value === scope)?.label ??
                        scope,
                      onRemove: () => {
                        view.update("scope", "all");
                      },
                    },
                  ]
                : []),
              ...(record.length
                ? [
                    {
                      label: "Records",
                      value: record
                        .map((category) => categoryLabels[category])
                        .join(", "),
                      onRemove: () => {
                        view.update("record", []);
                      },
                    },
                  ]
                : []),
              ...(withRange
                ? [
                    {
                      label: "Range",
                      value: "With native range only",
                      onRemove: () => {
                        view.update("withRange", false);
                      },
                    },
                  ]
                : []),
            ]}
          />
        }
      />
      {invalidSelection && (
        <p role="alert">
          Selection could not be restored: use valid identity IDs and select at
          most 20 distinct species. No IDs were substituted.
        </p>
      )}
      <div className="native-mode-toolbar">
        <div
          className="native-controls"
          role="group"
          aria-label="Native ranges mode"
        >
          <button
            type="button"
            aria-pressed={mode === "overview"}
            className={mode === "overview" ? "" : "button--secondary"}
            onClick={() => {
              view.update("mode", "overview");
            }}
          >
            Explore all
          </button>
          <button
            ref={speciesMode}
            type="button"
            aria-pressed={mode === "species"}
            className={mode === "species" ? "" : "button--secondary"}
            onClick={() => {
              view.update("mode", "species");
            }}
          >
            Compare species ({selectedIds.length})
          </button>
        </div>
        {selectedIds.length > 0 && (
          <ActionButton
            icon="clear-selection"
            className="button--quiet"
            type="button"
            onClick={() => {
              view.update("identity", []);
              speciesMode.current?.focus();
            }}
          >
            Clear selection
          </ActionButton>
        )}
      </div>
      <MapWorkspace>
        <section
          className="native-panel"
          aria-label={
            mode === "overview"
              ? "Collection native-range overview"
              : "Selected species native range"
          }
        >
          {mode === "overview" ? (
            <OverviewPanel
              key={queryKey}
              filters={filters}
              geometry={geometry}
              retryGeometry={retryGeometry}
              choose={choose}
              territorySelection={territorySelection}
            />
          ) : selectedIds.length === 1 ? (
            <SelectedPanel
              key={`${queryKey}:${selectedIds[0]}`}
              id={selectedIds[0]}
              filters={filters}
              geometry={geometry}
              retryGeometry={retryGeometry}
              colors={colors}
              territorySelection={territorySelection}
              remove={remove}
            />
          ) : selectedIds.length > 1 ? (
            <ComparisonPanel
              key={`${queryKey}:${selectedIds.join(",")}`}
              ids={selectedIds}
              filters={filters}
              geometry={geometry}
              retryGeometry={retryGeometry}
              remove={remove}
              colors={colors}
              territorySelection={territorySelection}
              only={(id) => {
                view.update("identity", [id]);
                speciesMode.current?.focus();
              }}
            />
          ) : (
            <div className="empty-state">
              <h3>Select a species</h3>
              <p>
                Choose a represented BotanicalIdentity to explore its exact
                recorded native-range places. Species without a range remain
                visible.
              </p>
              <button
                type="button"
                onClick={() => {
                  choose();
                }}
              >
                Choose species to compare
              </button>
            </div>
          )}
        </section>
      </MapWorkspace>
      {chooserOpen && (
        <TaskDialog
          title="Choose represented species"
          className="native-species-dialog"
          dismissOnBackdrop
          onClose={closeChooser}
        >
          <div className="section-heading">
            <h3>Choose species</h3>
            <ActionButton
              variant="secondary"
              type="button"
              className="button--secondary"
              onClick={closeChooser}
            >
              Done
            </ActionButton>
          </div>
          <DirectorySearch
            id="native-chooser-search"
            label="Find represented species"
            placeholder="Scientific name, common name or cultivar"
            value={q}
            onChange={(value) => {
              view.update("q", Array.from(value).slice(0, 200).join(""));
            }}
          />
          <p className="field-help">
            Search filters this workspace; selected species stay selected.
          </p>
          <p className="native-chooser-summary" role="status">
            {selectedIds.length} species selected · maximum 5 color layers.{" "}
            {selectedIds.length > 0 && (
              <button
                type="button"
                className="button--quiet"
                onClick={() => {
                  view.update("identity", []);
                }}
              >
                Clear chosen species
              </button>
            )}
          </p>
          <IdentityBrowser
            key={queryKey}
            filters={filters}
            selectedIds={selectedIds}
            select={(id) => {
              if (!selectedIds.includes(id) && selectedIds.length >= 5) return;
              view.replace({
                ...view.state,
                identity: selectedIds.includes(id)
                  ? selectedIds.filter((value) => value !== id)
                  : [...selectedIds, id].sort(),
                mode: "species",
              });
            }}
          />
        </TaskDialog>
      )}
    </section>
  );
}
