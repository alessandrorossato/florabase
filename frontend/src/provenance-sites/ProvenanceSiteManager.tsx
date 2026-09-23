import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { FieldHelp } from "../components/ContextualHelp";
import {
  OverflowMenu,
  QuickPreview,
  StatStrip,
} from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import type { GeographicPlaceResponse } from "../geographic-places/api";
import {
  createProvenanceSite,
  deleteProvenanceSite,
  listProvenanceSites,
  updateProvenanceSite,
  type ProvenanceSiteResponse,
} from "./api";

const ProvenanceMap = lazy(async () => {
  const module = await import("../provenance-map/ProvenanceMap");
  return { default: module.ProvenanceMap };
});

interface SiteForm {
  name: string;
  geographicPlaceId: string;
  latitude: string;
  longitude: string;
  accuracy: string;
  notes: string;
}

const blank: SiteForm = {
  name: "",
  geographicPlaceId: "",
  latitude: "",
  longitude: "",
  accuracy: "",
  notes: "",
};

export function ProvenanceSiteManager({
  places,
  csrfToken,
  initialSiteId,
  mode = "browse",
  query = "",
  onPlaceSelect,
}: {
  places: GeographicPlaceResponse[];
  csrfToken: string;
  initialSiteId?: string;
  mode?: "browse" | "map";
  query?: string;
  onPlaceSelect?: (id: string) => void;
}) {
  const [sites, setSites] = useState<ProvenanceSiteResponse[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<SiteForm>(blank);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const nameInput = useRef<HTMLInputElement>(null);

  async function refresh() {
    setSites(await listProvenanceSites());
  }

  useEffect(() => {
    const controller = new AbortController();
    void listProvenanceSites(controller.signal)
      .then((loaded) => {
        setSites(loaded);
        setLoading(false);
        setLoadError(false);
        const initial = loaded.find(({ id }) => id === initialSiteId);
        if (initial) {
          setSelectedId(initial.id);
          setForm({
            name: initial.name,
            geographicPlaceId: initial.geographic_place_id ?? "",
            latitude: initial.latitude ?? "",
            longitude: initial.longitude ?? "",
            accuracy: initial.coordinate_accuracy_m ?? "",
            notes: initial.notes ?? "",
          });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setLoadError(true);
          setLoading(false);
        }
      });
    return () => {
      controller.abort();
    };
  }, [initialSiteId]);

  function select(site: ProvenanceSiteResponse) {
    setSelectedId(site.id);
    setForm({
      name: site.name,
      geographicPlaceId: site.geographic_place_id ?? "",
      latitude: site.latitude ?? "",
      longitude: site.longitude ?? "",
      accuracy: site.coordinate_accuracy_m ?? "",
      notes: site.notes ?? "",
    });
    setMessage(null);
  }

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage(null);
    const payload = {
      name: form.name,
      geographic_place_id: form.geographicPlaceId || null,
      latitude: form.latitude || null,
      longitude: form.longitude || null,
      coordinate_accuracy_m: form.accuracy || null,
      notes: form.notes || null,
    };
    try {
      const saved = selectedId
        ? await updateProvenanceSite(selectedId, payload, csrfToken)
        : await createProvenanceSite(payload, csrfToken);
      await refresh();
      select(saved);
      setEditing(false);
      setMessage(`${saved.name} was saved.`);
    } catch (error: unknown) {
      setMessage(
        error instanceof ApiError && error.status === 422
          ? "Check the coordinate pair and accuracy. Latitude and longitude must be entered together."
          : "Florabase could not save this provenance site.",
      );
    } finally {
      setPending(false);
    }
  }

  const needle = query.trim().toLocaleLowerCase();
  const visible = useMemo(
    () =>
      sites.filter(
        (site) =>
          !needle ||
          [site.name, site.geographic_place_path].some((value) =>
            value?.toLocaleLowerCase().includes(needle),
          ),
      ),
    [sites, needle],
  );
  const mapped = useMemo(
    () =>
      visible.filter(
        (
          site,
        ): site is ProvenanceSiteResponse & {
          latitude: string;
          longitude: string;
        } => site.latitude != null && site.longitude != null,
      ),
    [visible],
  );
  const mapPoints = useMemo(
    () =>
      mapped.map((site) => ({
        id: site.id,
        name: site.name,
        geographic_place_path: site.geographic_place_path,
        latitude: site.latitude,
        longitude: site.longitude,
        coordinate_accuracy_m: site.coordinate_accuracy_m,
      })),
    [mapped],
  );
  const listed = mode === "map" ? mapped : visible;
  const selected = listed.find((site) => site.id === selectedId) ?? null;

  return (
    <section
      aria-labelledby="provenance-sites-title"
      className="provenance-sites-workspace"
    >
      <header className="section-heading">
        <div>
          <p className="eyebrow">Precise collection origins</p>
          <h3 id="provenance-sites-title">Provenance sites</h3>
        </div>
        <button
          type="button"
          onClick={() => {
            setSelectedId(null);
            setForm(blank);
            setMessage(null);
            setEditing(true);
          }}
        >
          New provenance site
        </button>
      </header>
      {!editing && message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      {loading && (
        <p role="status" className="notice">
          Loading provenance sites…
        </p>
      )}
      {loadError && (
        <div role="alert" className="notice notice--error">
          <p>Florabase could not load provenance sites.</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              setLoadError(false);
              void refresh()
                .then(() => {
                  setLoading(false);
                })
                .catch(() => {
                  setLoadError(true);
                  setLoading(false);
                });
            }}
          >
            Retry sites
          </button>
        </div>
      )}
      {!loading && !loadError && sites.length === 0 && (
        <p className="empty-state">No provenance sites recorded.</p>
      )}
      {!loading && !loadError && sites.length > 0 && listed.length === 0 && (
        <p className="empty-state" role="status">
          {mode === "map"
            ? "No coordinate-bearing sites match this view."
            : "No provenance sites match this search."}
        </p>
      )}
      {mode === "map" && mapped.length > 0 && (
        <div className="geography-map-layout">
          <div className="map-canvas-card">
            <Suspense fallback={<p role="status">Loading map…</p>}>
              <ProvenanceMap
                sites={mapPoints}
                selectedId={
                  mapped.some((site) => site.id === selectedId)
                    ? selectedId
                    : null
                }
                onSelect={(id) => {
                  const site = mapped.find((item) => item.id === id);
                  if (site) select(site);
                }}
                label="Geography map of stored provenance sites"
              />
            </Suspense>
            <p className="map-provider-note">
              Only stored WGS84 coordinates are mapped. Basemap tiles use the
              configured provider.
            </p>
          </div>
        </div>
      )}
      {listed.length > 0 && (
        <div
          className={
            mode === "map" ? "geography-map-companion" : "reference-split"
          }
        >
          <div className="site-directory-column">
            <h4>{mode === "map" ? "Mapped sites" : "Site directory"}</h4>
            <ul className="identity-list">
              {listed.map((site) => (
                <li key={site.id}>
                  <button
                    type="button"
                    className="identity-list-item"
                    aria-pressed={site.id === selectedId}
                    onClick={() => {
                      select(site);
                    }}
                  >
                    <span>{site.name}</span>
                    <small>
                      {site.geographic_place_path ??
                        "No named geographic place"}
                      {site.latitude !== null && site.longitude !== null
                        ? " · Mapped"
                        : " · No coordinates"}
                    </small>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <QuickPreview>
            {selected ? (
              <article className="record-inspector">
                <p className="eyebrow">Provenance site</p>
                <h3>{selected.name}</h3>
                <dl className="record-facts">
                  <div>
                    <dt>Geographic place</dt>
                    <dd>
                      {selected.geographic_place_id && onPlaceSelect ? (
                        <button
                          type="button"
                          className="text-link"
                          onClick={() => {
                            if (selected.geographic_place_id)
                              onPlaceSelect(selected.geographic_place_id);
                          }}
                        >
                          {selected.geographic_place_path}
                        </button>
                      ) : (
                        (selected.geographic_place_path ??
                        "No named geographic place")
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Coordinates</dt>
                    <dd>
                      {selected.latitude != null && selected.longitude != null
                        ? `${selected.latitude}, ${selected.longitude}`
                        : "Not recorded"}
                    </dd>
                  </div>
                  {selected.coordinate_accuracy_m != null && (
                    <div>
                      <dt>Accuracy</dt>
                      <dd>± {selected.coordinate_accuracy_m} m</dd>
                    </div>
                  )}
                  {selected.notes && (
                    <div>
                      <dt>Notes</dt>
                      <dd className="preserve-lines">{selected.notes}</dd>
                    </div>
                  )}
                </dl>
                <StatStrip
                  label="Direct collection links"
                  items={[
                    { label: "Seed lots", value: selected.usage.seed_lots },
                    { label: "Plants", value: selected.usage.plants },
                    {
                      label: "Plant groups",
                      value: selected.usage.plant_groups,
                    },
                  ]}
                />
                <div className="actions">
                  <button
                    type="button"
                    className="button--secondary"
                    onClick={() => {
                      setEditing(true);
                    }}
                  >
                    Edit
                  </button>
                  <OverflowMenu ariaLabel="More provenance site actions">
                    <button
                      type="button"
                      className="button--danger"
                      disabled={pending}
                      onClick={() => {
                        if (!window.confirm(`Delete ${selected.name}?`)) return;
                        setPending(true);
                        void deleteProvenanceSite(selected.id, csrfToken)
                          .then(async () => {
                            await refresh();
                            setSelectedId(null);
                            setMessage("The provenance site was deleted.");
                          })
                          .catch((error: unknown) => {
                            setMessage(
                              error instanceof ApiError && error.status === 409
                                ? "This provenance site is used by collection records and cannot be deleted."
                                : "Florabase could not delete this provenance site.",
                            );
                          })
                          .finally(() => {
                            setPending(false);
                          });
                      }}
                    >
                      Delete provenance site
                    </button>
                  </OverflowMenu>
                </div>
              </article>
            ) : (
              <div className="preview-empty">
                <h3>Select a provenance site</h3>
                <p>Choose a site from the list or map.</p>
              </div>
            )}
          </QuickPreview>
        </div>
      )}
      {editing && (
        <TaskDialog
          title={selectedId ? "Edit provenance site" : "New provenance site"}
          onClose={() => {
            setEditing(false);
          }}
        >
          <form
            className="identity-form"
            onSubmit={(event) => {
              void submit(event);
            }}
            aria-busy={pending}
          >
            <h4>
              {selectedId ? "Edit provenance site" : "Create provenance site"}
            </h4>
            <div className="field">
              <label htmlFor="site-name">Provenance site name</label>
              <input
                aria-describedby="provenance-site-name-help"
                id="site-name"
                ref={nameInput}
                disabled={pending}
                required
                maxLength={255}
                value={form.name}
                onChange={(event) => {
                  setForm({ ...form, name: event.currentTarget.value });
                }}
              />
              <FieldHelp id="provenance-site-name-help">
                A precise place where biological material originated or was
                collected, not its current collection Location.
              </FieldHelp>
            </div>
            <div className="field">
              <label htmlFor="site-place">Geographic place (optional)</label>
              <select
                id="site-place"
                disabled={pending}
                value={form.geographicPlaceId}
                onChange={(event) => {
                  setForm({
                    ...form,
                    geographicPlaceId: event.currentTarget.value,
                  });
                }}
              >
                <option value="">Not recorded</option>
                {places.map((place) => (
                  <option
                    key={place.id}
                    value={place.id}
                    disabled={Boolean(place.retired_at)}
                  >
                    {place.display_path}
                  </option>
                ))}
              </select>
            </div>
            <div className="coordinate-fields">
              <div className="field">
                <label htmlFor="site-latitude">Latitude (WGS84 decimal)</label>
                <input
                  id="site-latitude"
                  type="number"
                  disabled={pending}
                  step="0.000001"
                  min="-90"
                  max="90"
                  value={form.latitude}
                  onChange={(event) => {
                    setForm({ ...form, latitude: event.currentTarget.value });
                  }}
                />
              </div>
              <div className="field">
                <label htmlFor="site-longitude">
                  Longitude (WGS84 decimal)
                </label>
                <input
                  id="site-longitude"
                  type="number"
                  disabled={pending}
                  step="0.000001"
                  min="-180"
                  max="180"
                  value={form.longitude}
                  onChange={(event) => {
                    setForm({ ...form, longitude: event.currentTarget.value });
                  }}
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="site-accuracy">
                Coordinate accuracy in metres (optional)
              </label>
              <input
                id="site-accuracy"
                disabled={pending}
                type="number"
                step="0.001"
                min="0"
                value={form.accuracy}
                onChange={(event) => {
                  setForm({ ...form, accuracy: event.currentTarget.value });
                }}
              />
            </div>
            <div className="field">
              <label htmlFor="site-notes">Notes (optional)</label>
              <textarea
                id="site-notes"
                disabled={pending}
                maxLength={20000}
                value={form.notes}
                onChange={(event) => {
                  setForm({ ...form, notes: event.currentTarget.value });
                }}
              />
            </div>
            <div className="actions">
              <button
                type="button"
                className="button--secondary"
                disabled={pending}
                onClick={() => {
                  setEditing(false);
                }}
              >
                Cancel
              </button>
              <button disabled={pending}>
                {pending ? "Saving…" : "Save provenance site"}
              </button>
            </div>
            {message && (
              <p role="status" className="notice">
                {message}
              </p>
            )}
          </form>
        </TaskDialog>
      )}
    </section>
  );
}
