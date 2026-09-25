import { useEffect, useRef, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { listBotanicalIdentities } from "../botanical-identities/api";
import { listGeographicPlaces } from "../geographic-places/api";
import { listLocations } from "../locations/api";
import { listProvenanceSites } from "../provenance-sites/api";
import {
  ReferencePicker,
  type ReferenceChoice,
} from "../seed-lots/ReferencePicker";
import { listSuppliers } from "../suppliers/api";
import {
  activeSearch,
  getSearch,
  readSearchState,
  searchHash,
  type SearchKind,
  type SearchResponse,
  type SearchState,
} from "./searchApi";

const labels: Record<SearchKind, string> = {
  seed_lot: "Seed lots",
  sowing: "Sowings",
  plant: "Plants",
  plant_group: "Plant groups",
  event: "Events",
  botanical_identity: "Botanical identities",
  botanical_profile: "Reference knowledge",
  supplier: "Suppliers",
  location: "Locations",
  geographic_place: "Geographic places",
  provenance_site: "Provenance sites",
};
const singular: Record<SearchKind, string> = {
  seed_lot: "Seed lot",
  sowing: "Sowing",
  plant: "Plant",
  plant_group: "Plant group",
  event: "Event",
  botanical_identity: "Botanical identity",
  botanical_profile: "Reference knowledge",
  supplier: "Supplier",
  location: "Location",
  geographic_place: "Geographic place",
  provenance_site: "Provenance site",
};
const categories: { title: string; kinds: SearchKind[] }[] = [
  {
    title: "Collection",
    kinds: ["seed_lot", "sowing", "plant", "plant_group", "event"],
  },
  { title: "Botany", kinds: ["botanical_identity", "botanical_profile"] },
  {
    title: "Reference",
    kinds: ["supplier", "location", "geographic_place", "provenance_site"],
  },
];
const lifecycles: Partial<Record<SearchKind, string[]>> = {
  seed_lot: ["active", "exhausted", "discarded", "lost"],
  sowing: ["active", "reversed", "completed", "failed", "abandoned"],
  plant: [
    "active",
    "reversed",
    "reintegrated",
    "transferred",
    "dead",
    "lost",
    "discarded",
  ],
  plant_group: [
    "active",
    "reversed",
    "transferred",
    "completed",
    "dead",
    "lost",
    "discarded",
  ],
};
const eventKinds = [
  "observation",
  "movement",
  "repotting",
  "flowering",
  "fruiting",
  "pruning",
  "treatment",
  "harvest",
  "extraction",
  "reintegration",
  "transfer",
  "death",
  "loss",
  "discarded",
  "other",
];

interface References {
  identities: ReferenceChoice[];
  locations: ReferenceChoice[];
  suppliers: ReferenceChoice[];
  places: ReferenceChoice[];
  sites: ReferenceChoice[];
}

type ReferencesState =
  | { status: "idle" | "loading" | "error" }
  | { status: "ready"; value: References };

function mergeResults(
  previous: SearchResponse | null,
  next: SearchResponse,
): SearchResponse {
  if (!previous || next.offset === 0) return next;
  return {
    ...next,
    groups: previous.groups.map((group) => ({
      ...group,
      items: [
        ...group.items,
        ...(next.groups.find((part) => part.kind === group.kind)?.items ?? []),
      ],
    })),
  };
}

export function useDashboardSearch() {
  const auth = useAuth();
  const [state, setState] = useState<SearchState>(readSearchState);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(activeSearch(readSearchState()));
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [offset, setOffset] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [references, setReferences] = useState<ReferencesState>({
    status: "idle",
  });
  const [referenceAttempt, setReferenceAttempt] = useState(0);
  const filterButton = useRef<HTMLButtonElement>(null);

  const active = activeSearch(state);
  const hasReferenceFilter = Boolean(
    state.identityId ||
    state.locationId ||
    state.supplierId ||
    state.provenancePlaceId ||
    state.provenanceSiteId,
  );

  useEffect(() => {
    const sync = () => {
      const next = readSearchState();
      setState(next);
      setOffset(0);
      setResponse(null);
      setError(false);
      setLoading(activeSearch(next));
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    const timer = window.setTimeout(
      () => {
        void getSearch(state, offset, controller.signal)
          .then((next) => {
            if (controller.signal.aborted) return;
            setResponse((current) => mergeResults(current, next));
            setLoading(false);
          })
          .catch((reason: unknown) => {
            if (controller.signal.aborted) return;
            if (reason instanceof ApiError && reason.status === 401)
              auth.sessionExpired();
            else {
              setError(true);
              setLoading(false);
            }
          });
      },
      offset === 0 ? 280 : 0,
    );
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [state, offset, attempt, active, auth]);

  useEffect(() => {
    if ((!filtersOpen && !hasReferenceFilter) || references.status !== "idle")
      return;
    const controller = new AbortController();
    void Promise.all([
      listBotanicalIdentities(controller.signal),
      listLocations(controller.signal),
      listSuppliers(controller.signal),
      listGeographicPlaces(controller.signal),
      listProvenanceSites(controller.signal),
    ])
      .then(([identities, locations, suppliers, places, sites]) => {
        if (controller.signal.aborted) return;
        setReferences({
          status: "ready",
          value: {
            identities: identities.map((item) => ({
              id: item.id,
              label: item.display_label,
            })),
            locations: locations.map((item) => ({
              id: item.id,
              label: item.display_path,
            })),
            suppliers: suppliers.map((item) => ({
              id: item.id,
              label: item.name,
            })),
            places: places.map((item) => ({
              id: item.id,
              label: item.display_path,
            })),
            sites: sites.map((item) => ({ id: item.id, label: item.name })),
          },
        });
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        if (reason instanceof ApiError && reason.status === 401)
          auth.sessionExpired();
        else setReferences({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [
    filtersOpen,
    hasReferenceFilter,
    references.status,
    referenceAttempt,
    auth,
  ]);

  function apply(next: SearchState, typing = false) {
    const url = searchHash(next);
    if (url !== window.location.hash) {
      if (typing && active) window.history.replaceState(null, "", url);
      else window.history.pushState(null, "", url);
    }
    setState(next);
    setResponse(null);
    setOffset(0);
    setError(false);
    setLoading(activeSearch(next));
  }

  function update<Key extends keyof SearchState>(
    key: Key,
    value: SearchState[Key],
  ) {
    apply({ ...state, [key]: value });
  }

  function clear() {
    apply({
      ...state,
      q: "",
      kinds: [],
      identityId: "",
      lifecycle: "",
      locationId: "",
      supplierId: "",
      provenancePlaceId: "",
      provenanceSiteId: "",
      eventKind: "",
      year: "",
    });
    setFiltersOpen(false);
  }

  const singleKind = state.kinds.length === 1 ? state.kinds[0] : undefined;
  const lifecycleOptions = singleKind ? lifecycles[singleKind] : undefined;
  const filterCount =
    state.kinds.length +
    [
      state.identityId,
      state.lifecycle,
      state.locationId,
      state.supplierId,
      state.provenancePlaceId,
      state.provenanceSiteId,
      state.eventKind,
      state.year,
    ].filter(Boolean).length;
  const filterChips: { key: keyof SearchState; label: string }[] = [
    ...state.kinds.map((kind) => ({
      key: "kinds" as const,
      label: labels[kind],
    })),
    ...(
      [
        "identityId",
        "lifecycle",
        "locationId",
        "supplierId",
        "provenancePlaceId",
        "provenanceSiteId",
        "eventKind",
        "year",
      ] as const
    )
      .filter((key) => Boolean(state[key]))
      .map((key) => {
        const name = {
          identityId: "Identity",
          lifecycle: "Lifecycle",
          locationId: "Location",
          supplierId: "Supplier",
          provenancePlaceId: "Geographic place",
          provenanceSiteId: "Provenance site",
          eventKind: "Event kind",
          year: "Year",
        }[key];
        const choices =
          references.status === "ready"
            ? {
                identityId: references.value.identities,
                locationId: references.value.locations,
                supplierId: references.value.suppliers,
                provenancePlaceId: references.value.places,
                provenanceSiteId: references.value.sites,
              }
            : null;
        const label =
          choices && key in choices
            ? (choices[key as keyof typeof choices].find(
                (item) => item.id === state[key],
              )?.label ?? state[key])
            : state[key];
        return { key, label: `${name}: ${label}` };
      }),
  ];

  return {
    active,
    header: (
      <div className="dashboard-search-controls">
        <div className="field dashboard-search-field">
          <label htmlFor="dashboard-search">Search your collection</label>
          <input
            id="dashboard-search"
            type="search"
            placeholder="Search your collection…"
            value={state.q}
            onChange={(event) => {
              apply({ ...state, q: event.currentTarget.value }, true);
            }}
          />
        </div>
        <button
          ref={filterButton}
          type="button"
          className="button--secondary"
          aria-expanded={filtersOpen}
          aria-controls="dashboard-search-filters"
          onClick={() => {
            setFiltersOpen((open) => !open);
          }}
        >
          Filters{filterCount ? ` (${String(filterCount)})` : ""}
        </button>
      </div>
    ),
    content: (
      <>
        <section
          id="dashboard-search-filters"
          className="dashboard-filter-panel"
          aria-label="Search filters"
          hidden={!filtersOpen}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setFiltersOpen(false);
              filterButton.current?.focus();
            }
          }}
        >
          <div className="section-heading">
            <h3>Filters</h3>
            <button
              type="button"
              className="button--quiet"
              onClick={() => {
                setFiltersOpen(false);
                filterButton.current?.focus();
              }}
            >
              Close
            </button>
          </div>
          <fieldset className="dashboard-kind-filters">
            <legend>Record type</legend>
            {categories.map((category) => (
              <div key={category.title}>
                <strong>{category.title}</strong>
                {category.kinds.map((kind) => (
                  <label key={kind}>
                    <input
                      type="checkbox"
                      checked={state.kinds.includes(kind)}
                      onChange={(event) => {
                        const next = event.currentTarget.checked
                          ? [...state.kinds, kind]
                          : state.kinds.filter((item) => item !== kind);
                        apply({
                          ...state,
                          kinds: next,
                          lifecycle: "",
                          eventKind: "",
                          year: "",
                        });
                      }}
                    />
                    {labels[kind]}
                  </label>
                ))}
              </div>
            ))}
          </fieldset>
          <p className="field-hint">
            Collection filters below apply to recorded relationships. Location
            includes descendants; geographic provenance matches the exact
            recorded place or site.
          </p>
          {references.status === "idle" || references.status === "loading" ? (
            <p role="status">Loading filter choices…</p>
          ) : null}
          {references.status === "error" && (
            <div className="notice notice--error" role="alert">
              <p>Could not load filter choices.</p>
              <button
                type="button"
                onClick={() => {
                  setReferences({ status: "idle" });
                  setReferenceAttempt((value) => value + 1);
                }}
              >
                Retry
              </button>
            </div>
          )}
          {references.status === "ready" && (
            <div className="dashboard-reference-filters">
              <ReferencePicker
                label="Botanical identity"
                choices={references.value.identities}
                value={state.identityId}
                onChange={(id) => {
                  update("identityId", id);
                }}
              />
              <ReferencePicker
                label="Collection location"
                choices={references.value.locations}
                value={state.locationId}
                onChange={(id) => {
                  update("locationId", id);
                }}
              />
              <ReferencePicker
                label="Supplier"
                choices={references.value.suppliers}
                value={state.supplierId}
                onChange={(id) => {
                  update("supplierId", id);
                }}
              />
              <ReferencePicker
                label="Geographic provenance place"
                choices={references.value.places}
                value={state.provenancePlaceId}
                onChange={(id) => {
                  update("provenancePlaceId", id);
                }}
              />
              <ReferencePicker
                label="Provenance site"
                choices={references.value.sites}
                value={state.provenanceSiteId}
                onChange={(id) => {
                  update("provenanceSiteId", id);
                }}
              />
            </div>
          )}
          <div className="dashboard-filter-details">
            {lifecycleOptions && (
              <div className="field">
                <label htmlFor="search-lifecycle">
                  {singleKind ? labels[singleKind] : "Record"} lifecycle
                </label>
                <select
                  id="search-lifecycle"
                  value={state.lifecycle}
                  onChange={(event) => {
                    update("lifecycle", event.currentTarget.value);
                  }}
                >
                  <option value="">Any lifecycle</option>
                  {lifecycleOptions.map((value) => (
                    <option value={value} key={value}>
                      {value.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {singleKind === "event" && (
              <div className="field">
                <label htmlFor="search-event-kind">Event kind</label>
                <select
                  id="search-event-kind"
                  value={state.eventKind}
                  onChange={(event) => {
                    update("eventKind", event.currentTarget.value);
                  }}
                >
                  <option value="">Any kind</option>
                  {eventKinds.map((value) => (
                    <option value={value} key={value}>
                      {value.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {singleKind &&
              ["seed_lot", "sowing", "plant", "plant_group", "event"].includes(
                singleKind,
              ) && (
                <div className="field">
                  <label htmlFor="search-year">
                    {singleKind === "seed_lot"
                      ? "Acquisition"
                      : singleKind === "sowing"
                        ? "Sowing"
                        : singleKind === "event"
                          ? "Occurred"
                          : "Collection entry"}{" "}
                    year
                  </label>
                  <input
                    id="search-year"
                    type="number"
                    min="1"
                    max="9999"
                    value={state.year}
                    onChange={(event) => {
                      update("year", event.currentTarget.value);
                    }}
                  />
                  <small>
                    Matches the recorded year without assuming a month or day.
                  </small>
                </div>
              )}
          </div>
        </section>
        {active && (
          <section
            aria-labelledby="dashboard-search-results"
            className="dashboard-results"
          >
            <div className="dashboard-results-heading">
              <button
                type="button"
                className="dashboard-results-back"
                onClick={clear}
              >
                ← Back to Dashboard
              </button>
              <h3 id="dashboard-search-results">Search results</h3>
              {!error && response && response.total > 0 && (
                <p role="status">
                  {response.total} matching{" "}
                  {response.total === 1 ? "record" : "records"}
                </p>
              )}
            </div>
            {filterChips.length > 0 && (
              <div
                className="dashboard-filter-chips"
                aria-label="Active filters"
              >
                {filterChips.map((chip, index) => (
                  <button
                    type="button"
                    key={`${chip.key}-${String(index)}`}
                    onClick={() => {
                      if (chip.key === "kinds")
                        apply({
                          ...state,
                          kinds: state.kinds.filter((_, at) => at !== index),
                          lifecycle: "",
                          eventKind: "",
                          year: "",
                        });
                      else apply({ ...state, [chip.key]: "" });
                    }}
                  >
                    Remove {chip.label} ×
                  </button>
                ))}
                <button
                  type="button"
                  className="button--quiet"
                  onClick={() => {
                    apply({
                      ...state,
                      kinds: [],
                      identityId: "",
                      lifecycle: "",
                      locationId: "",
                      supplierId: "",
                      provenancePlaceId: "",
                      provenanceSiteId: "",
                      eventKind: "",
                      year: "",
                    });
                  }}
                >
                  Clear filters
                </button>
              </div>
            )}
            {loading && !response && (
              <p role="status">Searching your collection…</p>
            )}
            {error && (
              <div className="notice notice--error" role="alert">
                <p>Search could not be completed. Results may be incomplete.</p>
                <button
                  type="button"
                  onClick={() => {
                    setError(false);
                    setLoading(true);
                    setAttempt((value) => value + 1);
                  }}
                >
                  Retry search
                </button>
              </div>
            )}
            {!error && response?.total === 0 && (
              <div className="empty-state">
                <p>No records match this search and its filters.</p>
              </div>
            )}
            {!error && response && response.total > 0 && (
              <>
                {categories.map((category) => {
                  const groups = response.groups.filter((group) =>
                    category.kinds.includes(group.kind),
                  );
                  if (!groups.length) return null;
                  return (
                    <section
                      key={category.title}
                      className="dashboard-result-category"
                      aria-label={category.title}
                    >
                      <h4>{category.title}</h4>
                      {groups.map((group) => (
                        <section
                          key={group.kind}
                          className="dashboard-result-group"
                          aria-label={labels[group.kind]}
                        >
                          <h5>
                            {labels[group.kind]}{" "}
                            <span>
                              ·{" "}
                              {group.items.length === group.total
                                ? `${String(group.total)} ${group.total === 1 ? "result" : "results"}`
                                : `showing ${String(group.items.length)} of ${String(group.total)}`}
                            </span>
                          </h5>
                          <ul>
                            {group.items.map((item) => {
                              const context = item.context.trim();
                              const showContext =
                                context &&
                                context.toLocaleLowerCase() !==
                                  item.title.trim().toLocaleLowerCase() &&
                                context !== singular[item.kind] &&
                                context !== labels[item.kind] &&
                                context !== "Collection location";
                              const metadata =
                                item.kind === "botanical_identity" &&
                                showContext
                                  ? context
                                  : item.kind === "botanical_profile"
                                    ? "Botanical profile"
                                    : `${singular[item.kind]}${showContext ? ` · ${context}` : ""}`;
                              return (
                                <li key={item.id}>
                                  <a
                                    href={item.href}
                                    aria-label={`${singular[item.kind]}: ${item.title}${showContext ? `. ${context}` : ""}`}
                                  >
                                    <strong>{item.title}</strong>
                                    <span>{metadata}</span>
                                  </a>
                                </li>
                              );
                            })}
                          </ul>
                        </section>
                      ))}
                    </section>
                  );
                })}
                {response.groups.some(
                  (group) => group.items.length < group.total,
                ) && (
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={loading}
                    onClick={() => {
                      setOffset((value) => value + 20);
                      setLoading(true);
                    }}
                  >
                    {loading ? "Loading more…" : "Show more results"}
                  </button>
                )}
              </>
            )}
          </section>
        )}
      </>
    ),
  };
}
