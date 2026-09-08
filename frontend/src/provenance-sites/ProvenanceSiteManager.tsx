import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { ApiError } from "../auth/api";
import type { GeographicPlaceResponse } from "../geographic-places/api";
import {
  createProvenanceSite,
  deleteProvenanceSite,
  listProvenanceSites,
  updateProvenanceSite,
  type ProvenanceSiteResponse,
} from "./api";

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
}: {
  places: GeographicPlaceResponse[];
  csrfToken: string;
}) {
  const [sites, setSites] = useState<ProvenanceSiteResponse[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<SiteForm>(blank);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const nameInput = useRef<HTMLInputElement>(null);

  async function refresh() {
    setSites(await listProvenanceSites());
  }

  useEffect(() => {
    const controller = new AbortController();
    void listProvenanceSites(controller.signal)
      .then((loaded) => {
        setSites(loaded);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setMessage("Florabase could not load ProvenanceSites.");
        }
      });
    return () => {
      controller.abort();
    };
  }, []);

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
    nameInput.current?.focus();
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
      setMessage(`${saved.name} was saved.`);
    } catch (error: unknown) {
      setMessage(
        error instanceof ApiError && error.status === 422
          ? "Check the coordinate pair and accuracy. Latitude and longitude must be entered together."
          : "Florabase could not save this ProvenanceSite.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <section
      className="identity-directory"
      aria-labelledby="provenance-sites-title"
    >
      <h3 id="provenance-sites-title">Precise ProvenanceSites</h3>
      <p>
        Record an exact origin site separately from its named geographic area.
        Coordinates are optional; no geocoding or map request is performed.
      </p>
      <div className="directory-detail-grid">
        <div className="directory-column">
          <button
            type="button"
            onClick={() => {
              setSelectedId(null);
              setForm(blank);
              setMessage(null);
              nameInput.current?.focus();
            }}
          >
            + New ProvenanceSite
          </button>
          {sites.length === 0 ? (
            <p>No ProvenanceSites recorded.</p>
          ) : (
            <ul className="identity-list">
              {sites.map((site) => (
                <li key={site.id}>
                  <button
                    type="button"
                    onClick={() => {
                      select(site);
                    }}
                  >
                    <strong>{site.name}</strong>
                    <small>
                      {site.geographic_place_path ??
                        "No named geographic place"}
                    </small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <form
          className="identity-form"
          onSubmit={(event) => {
            void submit(event);
          }}
          aria-busy={pending}
        >
          <h4>
            {selectedId ? "Edit ProvenanceSite" : "Create ProvenanceSite"}
          </h4>
          <div className="field">
            <label htmlFor="site-name">ProvenanceSite name</label>
            <input
              id="site-name"
              ref={nameInput}
              required
              maxLength={255}
              value={form.name}
              onChange={(event) => {
                setForm({ ...form, name: event.currentTarget.value });
              }}
            />
          </div>
          <div className="field">
            <label htmlFor="site-place">Geographic place (optional)</label>
            <select
              id="site-place"
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
              <label htmlFor="site-longitude">Longitude (WGS84 decimal)</label>
              <input
                id="site-longitude"
                type="number"
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
              maxLength={20000}
              value={form.notes}
              onChange={(event) => {
                setForm({ ...form, notes: event.currentTarget.value });
              }}
            />
          </div>
          <div className="actions">
            <button disabled={pending}>
              {pending ? "Saving…" : "Save ProvenanceSite"}
            </button>
            {selectedId && (
              <button
                type="button"
                className="button--danger"
                disabled={pending}
                onClick={() => {
                  setPending(true);
                  void deleteProvenanceSite(selectedId, csrfToken)
                    .then(async () => {
                      await refresh();
                      setSelectedId(null);
                      setForm(blank);
                      setMessage("The ProvenanceSite was deleted.");
                    })
                    .catch(() => {
                      setMessage(
                        "This ProvenanceSite is used by collection records and cannot be deleted.",
                      );
                    })
                    .finally(() => {
                      setPending(false);
                    });
                }}
              >
                Delete ProvenanceSite
              </button>
            )}
          </div>
          {message && (
            <p role="status" className="notice">
              {message}
            </p>
          )}
        </form>
      </div>
    </section>
  );
}
