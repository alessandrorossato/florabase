import { identityOriginSites } from "./identityGeography";
import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  getCollectionProvenanceMap,
  type ProvenanceMapSite,
} from "../provenance-map/api";
import { OriginRecords } from "../provenance-map/OriginInspector";
import { ProvenanceMap } from "../provenance-map/ProvenanceMap";

export function IdentityOrigins({
  id,
  initialSites,
}: {
  id: string;
  initialSites?: ProvenanceMapSite[];
}) {
  const auth = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    sites?: ProvenanceMapSite[];
    failed?: boolean;
  } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    if (initialSites) return;
    void getCollectionProvenanceMap(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted)
          setResult({ sites: identityOriginSites(value.sites, id) });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setResult({ failed: true });
      });
    return () => {
      controller.abort();
    };
  }, [id, initialSites, attempt, auth]);
  if (result?.failed)
    return (
      <div role="alert">
        <p>Could not load recorded collection origins.</p>
        <button
          type="button"
          onClick={() => {
            setResult(null);
            setAttempt((n) => n + 1);
          }}
        >
          Retry collection origins
        </button>
      </div>
    );
  const sites = initialSites ?? result?.sites;
  if (!sites) return <p role="status">Loading recorded collection origins…</p>;
  if (!sites.length)
    return (
      <p>
        No directly linked provenance sites with coordinates are recorded for
        this identity. Unmapped or unrecorded origins are not inferred.
      </p>
    );
  const site = sites.find((s) => s.id === selected);
  return (
    <section
      className="identity-origins-view"
      aria-label="Identity collection origins"
    >
      <ProvenanceMap
        sites={sites}
        selectedId={selected}
        onSelect={setSelected}
      />
      <p className="field-help">
        Mapped direct links only, including retained historical material.
        Coordinate-less sites are not included in this map.
      </p>
      <ul className="identity-origin-sites">
        {sites.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className="button--secondary"
              aria-pressed={s.id === selected}
              onClick={() => {
                setSelected(s.id);
              }}
            >
              {s.name} · {s.records.length} linked records
            </button>
          </li>
        ))}
      </ul>
      {site && (
        <div aria-live="polite">
          <h4>{site.name}</h4>
          <p>{site.geographic_place_path ?? "No named area recorded"}</p>
          <p>
            Recorded coordinates: {site.latitude}, {site.longitude}. Accuracy:{" "}
            {site.coordinate_accuracy_m
              ? `${site.coordinate_accuracy_m} m`
              : "not recorded"}
            .
          </p>
          <OriginRecords records={site.records} />
        </div>
      )}
    </section>
  );
}
