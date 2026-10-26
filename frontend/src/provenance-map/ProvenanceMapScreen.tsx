import { GeographyHeader } from "../geography/GeographyHeader";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { DirectoryTools } from "../components/DirectoryTools";
import { DirectorySearch } from "../components/ReferenceUI";
import { MapWorkspace } from "../maps/MapWorkspace";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { getCollectionProvenanceMap, type ProvenanceMapResponse } from "./api";
import { filterMapSites } from "./filter";
import { identityGroups, uniqueRecords } from "./model";
import { OriginBreakdown, type Breakdown } from "./OriginBreakdown";
import { OriginInspector } from "./OriginInspector";
import { ProvenanceMap } from "./ProvenanceMap";

type MapState =
  | { status: "loading" }
  | { status: "ready"; dataset: ProvenanceMapResponse }
  | { status: "error" };

export function ProvenanceMapScreen() {
  const auth = useAuth();
  const [state, setState] = useState<MapState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [breakdown, setBreakdown] = useState<Breakdown | null>(null);
  const resetInspection = useCallback(() => {
    setSelectedId(null);
    setBreakdown(null);
  }, []);
  const view = useDirectoryView("provenance_map", resetInspection);
  const filters = useMemo(
    () => ({
      seedLots: view.state.seed_lots,
      plants: view.state.plants,
      identityQuery: view.state.q,
    }),
    [view.state],
  );
  useEffect(() => {
    const controller = new AbortController();
    void getCollectionProvenanceMap(controller.signal)
      .then((dataset) => {
        if (!controller.signal.aborted) setState({ status: "ready", dataset });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, auth]);
  const visibleSites = useMemo(
    () =>
      state.status === "ready"
        ? filterMapSites(state.dataset.sites, filters)
        : [],
    [filters, state],
  );
  const selected = visibleSites.find(({ id }) => id === selectedId) ?? null;
  // Clear excluded selection permanently; relaxing filters must not resurrect it.
  if (selectedId && !selected) setSelectedId(null);
  const records = uniqueRecords(visibleSites);
  const identities = identityGroups(records);
  const filtered = Boolean(
    view.state.q.trim() || !view.state.seed_lots || !view.state.plants,
  );
  const clearFilters = () => {
    view.replace({ q: "", seed_lots: true, plants: true });
  };
  return (
    <section
      className="workspace collection-origins"
      aria-labelledby="geography-origins-title"
    >
      <GeographyHeader
        view="origins"
        description="Recorded origins of physical collection material."
        tools={
          <DirectoryTools
            name="Collection origins"
            search={
              <DirectorySearch
                id="origins-query"
                label="Botanical identity"
                placeholder="Search botanical identities"
                value={view.state.q}
                onChange={(q) => {
                  view.update("q", q);
                }}
                hideLabel
              />
            }
            savedViews={
              <SavedViews
                surface="provenance_map"
                state={view.savedState}
                presentation="dialog"
              />
            }
            actions={
              <a
                className="button-link button--secondary"
                href="#/geography?mode=sites"
              >
                Manage provenance sites
              </a>
            }
            filters={
              <fieldset className="origins-categories">
                <legend>Directly linked record categories</legend>
                <label>
                  <input
                    type="checkbox"
                    checked={view.state.seed_lots}
                    onChange={(event) => {
                      view.update("seed_lots", event.currentTarget.checked);
                    }}
                  />
                  <span>Seed lots</span>
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={view.state.plants}
                    onChange={(event) => {
                      view.update("plants", event.currentTarget.checked);
                    }}
                  />
                  <span>Plants and plant groups</span>
                </label>
                <p className="field-help">
                  Includes retained historical records. Botanical search matches
                  recorded identity labels only.
                </p>
              </fieldset>
            }
            activeFilters={[
              ...(!view.state.seed_lots
                ? [
                    {
                      label: "SeedLots",
                      value: "Excluded",
                      onRemove: () => {
                        view.update("seed_lots", true);
                      },
                    },
                  ]
                : []),
              ...(!view.state.plants
                ? [
                    {
                      label: "Plants and PlantGroups",
                      value: "Excluded",
                      onRemove: () => {
                        view.update("plants", true);
                      },
                    },
                  ]
                : []),
            ]}
            onReset={() => {
              view.replace({ ...view.state, seed_lots: true, plants: true });
            }}
          />
        }
      />
      {state.status === "loading" && (
        <p role="status">Loading collection origins…</p>
      )}
      {state.status === "error" && (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load collection origins.</p>
          <button
            type="button"
            onClick={() => {
              setState({ status: "loading" });
              setAttempt(attempt + 1);
            }}
          >
            Retry
          </button>
        </div>
      )}
      {state.status === "ready" && (
        <>
          <div
            className="origins-overview"
            aria-label="Collection origin counts"
          >
            <button
              type="button"
              className="button--quiet"
              onClick={() => {
                setBreakdown("sites");
              }}
            >
              <strong>{visibleSites.length}</strong>{" "}
              <span>
                Mapped sites
                <small>
                  {filtered
                    ? `of ${String(state.dataset.sites.length)} total · filtered`
                    : "all mapped sites"}
                </small>
              </span>
            </button>
            <button
              type="button"
              className="button--quiet"
              onClick={() => {
                setBreakdown("records");
              }}
            >
              <strong>{records.length}</strong>{" "}
              <span>
                Directly linked records
                <small>
                  {filtered ? "filtered · mapped sites" : "at mapped sites"}
                </small>
              </span>
            </button>
            <button
              type="button"
              className="button--quiet"
              onClick={() => {
                setBreakdown("identities");
              }}
            >
              <strong>{identities.length}</strong>{" "}
              <span>
                Botanical identities
                <small>
                  {filtered ? "filtered · mapped sites" : "at mapped sites"}
                </small>
              </span>
            </button>
            <a href="#/geography?mode=sites">
              <strong>{state.dataset.coordinate_less_sites}</strong>{" "}
              <span>
                Without coordinates<small>all sites · Geography ↗</small>
              </span>
            </a>
          </div>
          {state.dataset.sites.length === 0 ? (
            <div className="empty-state">
              <h3>
                {state.dataset.total_provenance_sites === 0
                  ? "No provenance sites recorded"
                  : "No provenance sites have coordinates"}
              </h3>
              <p>
                {state.dataset.total_provenance_sites === 0
                  ? "Add a recorded origin through Geography or while recording an acquisition."
                  : "Sites without coordinates remain valid records. Add a stored latitude and longitude to place a site on this map."}
              </p>
              <a href="#/geography?mode=sites">
                Open provenance sites in Geography
              </a>
            </div>
          ) : (
            <MapWorkspace
              browserLabel="Inspector"
              browser={
                <OriginInspector
                  key={visibleSites.map(({ id }) => id).join(",")}
                  sites={visibleSites}
                  selected={selected}
                  onSelect={setSelectedId}
                  onClear={() => {
                    setSelectedId(null);
                  }}
                />
              }
            >
              <div
                className="origins-canvas"
                onKeyDown={(event) => {
                  if (event.key === "Escape" && selectedId) {
                    setSelectedId(null);
                  }
                }}
              >
                {visibleSites.length === 0 && (
                  <div className="origins-empty" role="status">
                    <h3>No provenance sites match the current filters</h3>
                    <button
                      type="button"
                      className="button--secondary"
                      onClick={clearFilters}
                    >
                      Clear filters
                    </button>
                  </div>
                )}
                <ProvenanceMap
                  sites={visibleSites}
                  selectedId={selected?.id ?? null}
                  onSelect={setSelectedId}
                />
              </div>
            </MapWorkspace>
          )}
          {selected && (
            <p className="sr-only" role="status">
              Selected site: {selected.name}, {selected.usage.total} directly
              linked records.
            </p>
          )}
          <p className="origins-evidence-note">
            Recorded direct origins only · record counts are not material
            quantities.
          </p>
          {breakdown && (
            <OriginBreakdown
              kind={breakdown}
              sites={visibleSites}
              onClose={() => {
                setBreakdown(null);
              }}
              onSelect={setSelectedId}
            />
          )}
        </>
      )}
    </section>
  );
}
