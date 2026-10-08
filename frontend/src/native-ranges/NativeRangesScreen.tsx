import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { DirectorySearch, PageHeader } from "../components/ReferenceUI";
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
  type Filters,
  type PlaceCoverage,
  type RangeIdentity,
  type RangePlace,
} from "./api";
import { loadGeometry, rangeGeometry } from "./geometry";
import { NativeCoverageMap, type GeometryState } from "./NativeCoverageMap";
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

function Representation({ identity }: { identity: RangeIdentity }) {
  return (
    <span className="native-representation">
      <strong>
        {identity.representation === "living"
          ? "Living"
          : identity.representation === "current"
            ? "Current"
            : "Historical"}
      </strong>
      <span>
        {identity.current_records} current · {identity.retained_records}{" "}
        retained records
      </span>
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
      <h3 id="native-identities-title">Represented species</h3>
      <p className="field-help">
        Select up to 20 species explicitly.{" "}
        {selectedIds.length >= 20
          ? "Selection limit reached; remove a species to choose another."
          : ""}
      </p>
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
                        selectedIds.length >= 20 &&
                        !selectedIds.includes(identity.id)
                      }
                      onChange={() => {
                        select(identity.id);
                      }}
                    />
                    <span className="native-identity-content">
                      <strong>{identity.display_label}</strong>
                      {identity.common_name && (
                        <span>{identity.common_name}</span>
                      )}
                      <Representation identity={identity} />
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
  geometry: GeometryState;
  retryGeometry: () => void;
}
function OverviewPanel({
  filters,
  geometry,
  retryGeometry,
}: MapProps & { filters: Filters }) {
  const [offset, setOffset] = useState(0);
  const read = useCallback(
    (signal: AbortSignal) => getNativeOverview(filters, offset, signal),
    [filters, offset],
  );
  const query = useLocalRead(read);
  if (query.error)
    return <ReadError retry={query.retry} label="collection overview" />;
  if (!query.data) return <p role="status">Loading collection overview…</p>;
  const overview = query.data;
  return (
    <>
      <h3>Collection overview</h3>
      <dl
        className="native-statistics"
        aria-label="Native-range coverage summary"
      >
        <div>
          <dt>Represented identities</dt>
          <dd>{overview.represented}</dd>
        </div>
        <div>
          <dt>With recorded native range</dt>
          <dd>{overview.with_range}</dd>
        </div>
        <div>
          <dt>Without structured range</dt>
          <dd>{overview.without_range}</dd>
        </div>
      </dl>
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
            territories={overview.territories}
            geometry={geometry}
            retry={retryGeometry}
          />
          <h4>Exact recorded places · {overview.places_total}</h4>
          <p className="field-help">
            Counts here describe identities explicitly linked to each recorded
            place. Broad and precise places are preserved together; these counts
            must not be added to infer map coverage.
          </p>
          <RangeList places={overview.places} geometry={geometry} overview />
          <Pages
            offset={offset}
            total={overview.places_total}
            onChange={setOffset}
            label="Recorded place pages"
          />
        </>
      )}
    </>
  );
}

function SelectedPanel({
  id,
  filters,
  geometry,
  retryGeometry,
}: MapProps & { id: string; filters: Filters }) {
  const [offset, setOffset] = useState(0);
  const read = useCallback(
    (signal: AbortSignal) => getNativeSelection(id, filters, offset, signal),
    [id, filters, offset],
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
  const { identity, ranges, territories, total } = query.data;
  return (
    <>
      <h3>{identity.display_label}</h3>
      {identity.common_name && <p>{identity.common_name}</p>}
      <Representation identity={identity} />
      <div className="actions native-links">
        <a href={`#/identities/${id}?tab=reference`}>
          Botanical identity details
        </a>
        <a href={`#/identities/${id}?tab=native-range`}>Edit recorded range</a>
        <a href={`#/species-distribution?identity=${id}`}>
          View occurrence distribution
        </a>
      </div>
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
            territories={territories}
            geometry={geometry}
            selected
            retry={retryGeometry}
          />
          <h4>
            Recorded native range · {total} {total === 1 ? "place" : "places"}
          </h4>
          <RangeList places={ranges} geometry={geometry} />
          <Pages
            offset={offset}
            total={total}
            onChange={setOffset}
            label="Selected native-range pages"
          />
        </>
      )}
    </>
  );
}

function ComparisonPanel({
  ids,
  filters,
  geometry,
  retryGeometry,
  remove,
  only,
}: MapProps & {
  ids: string[];
  filters: Filters;
  remove: (id: string) => void;
  only: (id: string) => void;
}) {
  const read = useCallback(
    (signal: AbortSignal) => getNativeComparison(ids, filters, signal),
    [ids, filters],
  );
  const query = useLocalRead(read);
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
      <h3>Selected species comparison</h3>
      <p>
        Each territory counts distinct selected species that match the filters.
        Overlapping recorded ranges count once per species.
      </p>
      <ul className="native-selection-list" aria-label="Selected species">
        {identities.map((identity) => (
          <li key={identity.id}>
            <strong>{identity.display_label}</strong>
            <span>
              {!identity.matches_filters
                ? "Excluded by current filters; no coverage contributed"
                : identity.native_range_count
                  ? `${String(identity.native_range_count)} recorded places`
                  : "No structured native range recorded"}
            </span>
            <div className="actions">
              <button
                type="button"
                className="button--secondary"
                onClick={() => {
                  only(identity.id);
                }}
              >
                View only {identity.display_label}
              </button>
              <button
                type="button"
                className="button--secondary"
                onClick={() => {
                  remove(identity.id);
                }}
              >
                Remove {identity.display_label}
              </button>
            </div>
          </li>
        ))}
        {missing_ids.map((id) => (
          <li key={id}>
            <span>Missing or no longer represented: {id}</span>
            <button
              type="button"
              onClick={() => {
                remove(id);
              }}
            >
              Remove {id}
            </button>
          </li>
        ))}
      </ul>
      <NativeCoverageMap
        territories={territories}
        contributors={contributors}
        geometry={geometry}
        retry={retryGeometry}
      />
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
  const [navigation, setNavigation] = useState(0);
  const reset = useCallback(() => {
    setNavigation((value) => value + 1);
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
  };
  return (
    <section
      className="workspace native-ranges"
      aria-labelledby="native-ranges-title"
    >
      <PageHeader
        title="Native ranges"
        titleId="native-ranges-title"
        eyebrow="Explore"
        description="Explore recorded native-range regions for species represented in your collection."
        actions={null}
      />
      <p className="field-help">
        Native ranges are structured botanical reference knowledge. They are
        distinct from occurrence records and from the recorded origins of your
        own material.
      </p>
      <SavedViews surface="native_ranges" state={view.savedState} />
      <div
        className="native-controls"
        role="group"
        aria-label="Collection representation scope"
      >
        {scopes.map((item) => (
          <button
            key={item.value}
            type="button"
            aria-pressed={scope === item.value}
            className={scope === item.value ? "" : "button--secondary"}
            onClick={() => {
              view.update("scope", item.value);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <p className="field-help">
        Living includes active Plants and Plant groups. Current also includes
        active seeds, sowings and managed stored material. Historical has
        retained evidence with no current material.
      </p>
      <fieldset className="native-category-filters">
        <legend>Collection records</legend>
        <p className="field-help">
          Choose any record types (OR). None selected includes all types within
          the status above.
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
      {invalidSelection && (
        <p role="alert">
          Selection could not be restored: use valid identity IDs and select at
          most 20 distinct species. No IDs were substituted.
        </p>
      )}
      <div className="native-filters">
        <DirectorySearch
          id="native-species-search"
          label="Search species"
          placeholder="Scientific name, common name or cultivar"
          value={q}
          onChange={(value) => {
            view.update("q", Array.from(value).slice(0, 200).join(""));
          }}
        />
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
      </div>
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
          Collection overview
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
          Selected species ({selectedIds.length})
        </button>
      </div>
      <div className="native-workspace">
        <IdentityBrowser
          key={queryKey}
          filters={filters}
          selectedIds={selectedIds}
          select={(id) => {
            view.replace({
              ...view.state,
              identity: selectedIds.includes(id)
                ? selectedIds.filter((value) => value !== id)
                : [...selectedIds, id].sort(),
              mode: "species",
            });
          }}
        />
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
            />
          ) : (
            <>
              {selectedIds.length ? (
                <>
                  <button
                    className="button--secondary"
                    type="button"
                    onClick={() => {
                      view.update("identity", []);
                      speciesMode.current?.focus();
                    }}
                  >
                    Clear selection
                  </button>
                  {selectedIds.length === 1 ? (
                    <SelectedPanel
                      key={`${queryKey}:${selectedIds[0]}`}
                      id={selectedIds[0]}
                      filters={filters}
                      geometry={geometry}
                      retryGeometry={retryGeometry}
                    />
                  ) : (
                    <ComparisonPanel
                      key={`${queryKey}:${selectedIds.join(",")}`}
                      ids={selectedIds}
                      filters={filters}
                      geometry={geometry}
                      retryGeometry={retryGeometry}
                      remove={remove}
                      only={(id) => {
                        view.update("identity", [id]);
                      }}
                    />
                  )}
                </>
              ) : (
                <div className="empty-state">
                  <h3>Select a species</h3>
                  <p>
                    Choose a represented BotanicalIdentity to explore its exact
                    recorded native-range places. Species without a range remain
                    visible.
                  </p>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </section>
  );
}
