import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { Breadcrumbs } from "../components/CollectionUI";
import {
  getCollectionProvenanceMap,
  type ProvenanceMapRecord,
  type ProvenanceMapResponse,
  type ProvenanceMapSite,
} from "./api";
import { filterMapSites, type MapFilters } from "./filter";
import { ProvenanceMap } from "./ProvenanceMap";

type MapState =
  | { status: "loading" }
  | { status: "ready"; dataset: ProvenanceMapResponse }
  | { status: "error" };

const initialFilters: MapFilters = {
  seedLots: true,
  plants: true,
  identityQuery: "",
};

const lifecycleLabels: Record<string, string> = {
  active: "Active",
  exhausted: "Exhausted",
  discarded: "Discarded",
  lost: "Lost",
  transferred: "Transferred",
  dead: "Dead",
  completed: "Completed",
  reversed: "Reversed",
  reintegrated: "Reintegrated",
};

function recordTypeLabel(record: ProvenanceMapRecord): string {
  if (record.record_type === "seed_lot") return "SeedLot";
  if (record.record_type === "plant_group") return "PlantGroup";
  return "Plant";
}

function recordHref(record: ProvenanceMapRecord): string {
  if (record.record_type === "seed_lot") return `#/seeds/${record.id}`;
  if (record.record_type === "plant_group")
    return `#/plant-groups/${record.id}`;
  return `#/plants/${record.id}`;
}

function coordinates(site: ProvenanceMapSite): string {
  return `${site.latitude}, ${site.longitude}`;
}

function SiteDetails({ site }: { site: ProvenanceMapSite }) {
  return (
    <section className="map-site-detail" aria-labelledby="map-site-title">
      <div className="map-site-detail__header">
        <div>
          <p className="eyebrow">Selected provenance site</p>
          <h3 id="map-site-title">{site.name}</h3>
          <p>{site.geographic_place_path ?? "No named geographic place"}</p>
        </div>
        <a href={`#/geography/${site.id}`}>Edit site</a>
      </div>
      <dl className="detail-list detail-list--compact">
        <div>
          <dt>Coordinates</dt>
          <dd>{coordinates(site)}</dd>
        </div>
        <div>
          <dt>Accuracy</dt>
          <dd>
            {site.coordinate_accuracy_m === null
              ? "Not recorded"
              : `± ${site.coordinate_accuracy_m} m`}
          </dd>
        </div>
      </dl>
      <p>
        {site.usage.total} linked{" "}
        {site.usage.total === 1 ? "record" : "records"}: {site.usage.seed_lots}{" "}
        SeedLots, {site.usage.plants} Plants, {site.usage.plant_groups}{" "}
        PlantGroups
      </p>
      <ul className="map-record-list">
        {site.records.map((record) => (
          <li key={`${record.record_type}:${record.id}`}>
            <div>
              <span className="card-type">{recordTypeLabel(record)}</span>
              <a href={recordHref(record)}>
                {record.label ?? record.botanical_identity.display_label}
              </a>
              <a
                className="map-identity-link"
                href={`#/identities/${record.botanical_identity.id}`}
              >
                Botanical identity: {record.botanical_identity.display_label}
              </a>
            </div>
            <span
              className={`lifecycle-badge lifecycle-badge--${record.is_active ? "active" : "historical"}`}
            >
              {lifecycleLabels[record.lifecycle] ?? record.lifecycle}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ProvenanceMapScreen() {
  const auth = useAuth();
  const [state, setState] = useState<MapState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [filters, setFilters] = useState<MapFilters>(initialFilters);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getCollectionProvenanceMap(controller.signal)
      .then((dataset) => {
        setState({ status: "ready", dataset });
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

  return (
    <section
      className="screen map-screen"
      aria-labelledby="provenance-map-title"
    >
      <Breadcrumbs
        items={[{ label: "Collection", href: "#/dashboard" }, { label: "Map" }]}
      />
      <header className="screen-heading">
        <div>
          <p className="eyebrow">Collection provenance</p>
          <h2 id="provenance-map-title">
            Where your recorded material originated
          </h2>
          <p>
            Markers are precise ProvenanceSites linked directly to collection
            records—not current Locations, Supplier addresses, or botanical
            native ranges.
          </p>
        </div>
        <a className="button-link button--secondary" href="#/geography">
          Manage provenance sites
        </a>
      </header>

      {state.status === "loading" && (
        <p aria-live="polite">Loading provenance map…</p>
      )}
      {state.status === "error" && (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load the collection provenance map.</p>
          <button
            type="button"
            onClick={() => {
              setState({ status: "loading" });
              setAttempt((value) => value + 1);
            }}
          >
            Retry
          </button>
        </div>
      )}
      {state.status === "ready" &&
        state.dataset.total_provenance_sites === 0 && (
          <div className="empty-state">
            <h3>No ProvenanceSites recorded</h3>
            <p>
              Add a precise origin through Geography or while recording an
              acquisition. Coordinates are optional until the site is ready to
              map.
            </p>
            <a href="#/geography">Open Geography</a>
          </div>
        )}
      {state.status === "ready" &&
        state.dataset.total_provenance_sites > 0 &&
        state.dataset.sites.length === 0 && (
          <div className="empty-state">
            <h3>No provenance sites have coordinates</h3>
            <p>
              Only ProvenanceSites with stored latitude and longitude can be
              mapped.
            </p>
            <a href="#/geography">Add coordinates in Geography</a>
          </div>
        )}
      {state.status === "ready" && state.dataset.sites.length > 0 && (
        <>
          <fieldset className="map-filters">
            <legend>Filter linked collection records</legend>
            <label>
              <input
                type="checkbox"
                checked={filters.seedLots}
                onChange={(event) => {
                  const checked = event.currentTarget.checked;
                  setFilters((current) => ({ ...current, seedLots: checked }));
                }}
              />
              SeedLots
            </label>
            <label>
              <input
                type="checkbox"
                checked={filters.plants}
                onChange={(event) => {
                  const checked = event.currentTarget.checked;
                  setFilters((current) => ({ ...current, plants: checked }));
                }}
              />
              Plants and PlantGroups
            </label>
            <label className="map-identity-filter">
              Botanical identity
              <input
                type="search"
                value={filters.identityQuery}
                placeholder="Search scientific name"
                onChange={(event) => {
                  const identityQuery = event.currentTarget.value;
                  setFilters((current) => ({
                    ...current,
                    identityQuery,
                  }));
                }}
              />
            </label>
          </fieldset>
          {visibleSites.length === 0 ? (
            <div className="empty-state" aria-live="polite">
              <h3>No provenance sites match the current filters</h3>
              <button
                type="button"
                onClick={() => {
                  setFilters(initialFilters);
                }}
              >
                Clear filters
              </button>
            </div>
          ) : (
            <div className="map-layout">
              <div className="map-canvas-card">
                <ProvenanceMap
                  sites={visibleSites}
                  selectedId={selected?.id ?? null}
                  onSelect={(id) => {
                    setSelectedId(id);
                  }}
                />
                <p className="map-provider-note">
                  The basemap provider receives ordinary tile requests for the
                  visible area, never Florabase record names or metadata.
                </p>
              </div>
              <aside
                className="map-companion"
                aria-label="Mapped provenance sites"
              >
                <h3>{visibleSites.length} mapped provenance sites</h3>
                <p>Select a site to inspect its filtered collection records.</p>
                <ul className="map-site-list">
                  {visibleSites.map((site) => (
                    <li key={site.id}>
                      <button
                        type="button"
                        aria-pressed={site.id === selected?.id}
                        onClick={() => {
                          setSelectedId(site.id);
                        }}
                      >
                        <strong>{site.name}</strong>
                        <span>
                          {site.geographic_place_path ??
                            "No named geographic place"}
                        </span>
                        <small>
                          {coordinates(site)} · {site.usage.total} linked
                        </small>
                      </button>
                    </li>
                  ))}
                </ul>
              </aside>
              {selected ? (
                <SiteDetails site={selected} />
              ) : (
                <p className="map-selection-prompt">
                  Select a marker or a site in the companion list to inspect
                  linked records.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
