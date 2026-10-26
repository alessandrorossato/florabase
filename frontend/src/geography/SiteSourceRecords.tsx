import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { OriginRecords } from "../provenance-map/OriginInspector";
import "../provenance-map/origins.css";
import {
  getCollectionProvenanceMap,
  type ProvenanceMapRecord,
} from "../provenance-map/api";

export function SiteSourceRecords({
  siteId,
  hasCoordinates,
}: {
  siteId: string;
  hasCoordinates: boolean;
}) {
  const auth = useAuth();
  const [records, setRecords] = useState<ProvenanceMapRecord[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!hasCoordinates) return;
    const controller = new AbortController();
    void getCollectionProvenanceMap(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted)
          setRecords(
            data.sites.find((site) => site.id === siteId)?.records ?? [],
          );
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setFailed(true);
      });
    return () => {
      controller.abort();
    };
  }, [siteId, hasCoordinates, auth, attempt]);
  return (
    <section className="record-section" aria-label="Linked source records">
      <h4>Linked source records</h4>
      {!hasCoordinates ? (
        <p>
          Exact record links are currently available only for sites with
          coordinates through Collection origins. Usage totals above still
          include records without coordinates.
        </p>
      ) : failed ? (
        <div role="alert">
          <p>Could not load source records.</p>
          <button
            type="button"
            className="button--secondary"
            onClick={() => {
              setFailed(false);
              setAttempt(attempt + 1);
            }}
          >
            Retry source records
          </button>
        </div>
      ) : records === null ? (
        <p role="status">Loading source records…</p>
      ) : records.length ? (
        <OriginRecords records={records} />
      ) : (
        <p>No directly linked source records in Collection origins.</p>
      )}
      <a href="#/map">Explore collection origins</a>
    </section>
  );
}
