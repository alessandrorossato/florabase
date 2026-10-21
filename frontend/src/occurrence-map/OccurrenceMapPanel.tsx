import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import type { ExternalTaxonLinkResponse } from "../botanical-identities/api";
import { MapWorkspace } from "../maps/MapWorkspace";
import { loadWorkspaceChunk } from "../components/workspaceChunk";
import {
  clearOccurrenceEvidence,
  getCachedOccurrenceEvidence,
  refreshOccurrenceEvidence,
  type OccurrenceEvidence,
} from "./api";

const OccurrenceDensityMap = lazy(() =>
  loadWorkspaceChunk(async () => {
    const module = await import("./OccurrenceDensityMap");
    return { default: module.OccurrenceDensityMap };
  }),
);
const number = (value: number) => new Intl.NumberFormat().format(value);
const dateTime = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

export function OccurrenceMapPanel({
  identityId,
  link,
  inspector,
  identityLabel,
}: {
  identityId: string;
  link: Pick<ExternalTaxonLinkResponse, "provider" | "external_id"> | null;
  inspector?: ReactNode;
  identityLabel?: ReactNode;
}) {
  const auth = useAuth();
  const [evidence, setEvidence] = useState<OccurrenceEvidence | null>(null);
  const [checking, setChecking] = useState(Boolean(link));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localOnly, setLocalOnly] = useState(true);
  const csrf =
    auth.state.status === "authenticated" ||
    auth.state.status === "logout-failed"
      ? auth.state.csrfToken
      : null;
  const externalId = link?.external_id;
  const provider = link?.provider;
  useEffect(() => {
    if (!externalId || provider !== "gbif") return;
    const controller = new AbortController();
    void getCachedOccurrenceEvidence(identityId, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) {
          setEvidence(value);
          setChecking(false);
        }
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else {
          setChecking(false);
          setError("Could not read local occurrence evidence.");
        }
      });
    return () => {
      controller.abort();
    };
  }, [identityId, externalId, provider, auth]);
  async function load() {
    if (!csrf || pending) return;
    setPending(true);
    setError(null);
    try {
      const value = await refreshOccurrenceEvidence(identityId, csrf);
      setEvidence(value);
      setLocalOnly(Boolean(value.provider_error));
      if (value.provider_error)
        setError(
          "GBIF refresh failed. Previously saved evidence is still available.",
        );
    } catch (failure) {
      setLocalOnly(true);
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else
        setError(
          "GBIF occurrence evidence is temporarily unavailable. Your Florabase botanical and collection data remain available.",
        );
    } finally {
      setPending(false);
    }
  }
  async function clear() {
    if (!csrf || pending) return;
    setPending(true);
    try {
      await clearOccurrenceEvidence(identityId, csrf);
      setEvidence(null);
      setLocalOnly(true);
      setError(null);
    } catch {
      setError(
        "Could not clear local evidence. The saved evidence remains available.",
      );
    } finally {
      setPending(false);
    }
  }
  const summary = evidence?.summary;
  const controls = (
    <div className="occurrence-evidence-actions">
      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}
      {checking ? (
        <p role="status">Checking local evidence…</p>
      ) : !link ? (
        <p>
          Confirm a GBIF taxon link above before loading occurrence evidence.
          Florabase will not search by the identity name automatically.
        </p>
      ) : (
        <>
          <p className="field-help">
            {summary
              ? !evidence.persisted
                ? "Loaded for this visit · not saved"
                : evidence.stale
                  ? "Locally available · potentially outdated"
                  : "Locally available"
              : "Not downloaded · external evidence has not been requested."}
            {summary && !evidence.persisted
              ? " · This response could not be retained under the provider cache policy."
              : ""}
          </p>
          <button
            type="button"
            disabled={pending || !csrf}
            onClick={() => {
              void load();
            }}
          >
            {pending
              ? "Loading GBIF occurrence evidence…"
              : summary
                ? "Refresh from GBIF"
                : "Load GBIF occurrence map"}
          </button>
          {summary && (
            <button
              type="button"
              className="button--quiet"
              disabled={pending}
              onClick={() => {
                void clear();
              }}
            >
              Clear local evidence for linked taxon
            </button>
          )}
          {summary && (
            <p className="field-help">
              {localOnly
                ? "Viewing saved tiles only. Missing areas will not contact GBIF."
                : "Saving viewed GBIF tiles for this snapshot; only visited areas are available later."}
            </p>
          )}
        </>
      )}
    </div>
  );
  const dataDetails = (
    <details className="distribution-evidence">
      <summary>Data details</summary>
      <p>
        GBIF occurrence data · not native-range data. Counts and downloaded
        tiles are saved locally; there is no complete dataset of individual
        records.
      </p>
      <h4>Occurrence evidence and privacy</h4>
      <p>
        Florabase asks GBIF for the exact linked taxon only after Load or
        Refresh. Collection records, notes, account identity, and physical
        location are not sent. Local evidence reads make no external requests.
        The optional online basemap sends your IP and visible tile area to the
        configured provider.
      </p>
      {summary && (
        <>
          <p>
            Source:{" "}
            <a href={summary.provider_url} target="_blank" rel="noreferrer">
              {summary.source}
            </a>
            . Linked taxon:{" "}
            <a
              href={summary.taxon_provider_url}
              target="_blank"
              rel="noreferrer"
            >
              {summary.taxon_scientific_name}
            </a>
            .
          </p>
          <p>
            Taxonomy: {summary.checklist_name} ·{" "}
            <code>{summary.checklist_key}</code>
          </p>
          <h4>Mapping and quality policy</h4>
          <p>
            The map includes PRESENT records with usable coordinates and
            excludes records GBIF flags as having a geospatial issue.{" "}
            {summary.total_matching_records >= summary.eligible_mapped_records
              ? `${number(summary.total_matching_records - summary.eligible_mapped_records)} matching records are outside this mapped subset.`
              : "The two live counts changed while GBIF processed them, so the eligible mapped count is the map’s current reference."}{" "}
            Provider flags cannot eliminate every uncertainty or error.
          </p>
          <p>
            Hexagons show GBIF recording density at the current zoom, not
            biological abundance. Numeric color thresholds and exact counts per
            bin are not returned. Geographic resolution changes with zoom;
            colors cannot compare different zoom levels.
          </p>
          <p>
            An occurrence means a specimen or observation was recorded; it does
            not mean the taxon is native there. Coordinates may be generalized,
            obscured, uncertain, erroneous, historical, cultivated or
            introduced. No displayed density does not prove species absence.
          </p>
          <p>
            Counts and each viewed tile are obtained separately from a changing
            provider. A snapshot isolates refresh generations, but is not a
            transactionally frozen GBIF dataset. Evicted, missing or unavailable
            tiles remain incomplete; a refresh never silently reuses an older
            generation’s tiles.
          </p>
          <p>
            Attribution: {summary.attribution}. Underlying records retain their
            contributing datasets’ licences and attribution requirements; they
            do not share one blanket licence. Review the{" "}
            <a href={summary.licensing_url} target="_blank" rel="noreferrer">
              GBIF terms and data-user requirements
            </a>
            . Local geographic context: Natural Earth 1:110m, public domain.
          </p>
        </>
      )}
    </details>
  );
  const details = (
    <section
      className="distribution-evidence-inspector"
      aria-label="Selected species evidence"
    >
      {inspector}
      {summary && (
        <dl className="detail-list detail-list--compact occurrence-primary-counts">
          <div>
            <dt>Eligible mapped records</dt>
            <dd>{number(summary.eligible_mapped_records)}</dd>
          </div>
          <div>
            <dt>All matching PRESENT records</dt>
            <dd>{number(summary.total_matching_records)}</dd>
          </div>
          <div>
            <dt>Last checked</dt>
            <dd>{dateTime(summary.retrieved_at)}</dd>
          </div>
        </dl>
      )}
      {controls}
      {dataDetails}
    </section>
  );
  const canvas = (
    <>
      <h3 className="distribution-map-title">
        {identityLabel ?? "Occurrence evidence"}
        {summary ? " · Observed occurrences" : ""}
      </h3>
      {!summary ? (
        <div className="distribution-map-placeholder">
          {controls}
          <p className="field-help">
            GBIF occurrence data · not native-range data
          </p>
        </div>
      ) : summary.eligible_mapped_records === 0 ? (
        <div className="distribution-map-placeholder">
          <h4>No mapped occurrence records</h4>
          <p>
            The confirmed taxon has no records currently satisfying this
            coordinate and quality policy. This is not proof of species absence.
          </p>
        </div>
      ) : (
        <div className="map-canvas-card">
          <Suspense fallback={<p role="status">Loading occurrence map…</p>}>
            <OccurrenceDensityMap
              identityId={identityId}
              generation={evidence.generation}
              localOnly={localOnly}
            />
          </Suspense>
          <div
            className="occurrence-density-legend"
            aria-label="Occurrence density legend"
          >
            <span>Fewer records per hexagonal bin</span>
            <span aria-hidden="true" className="occurrence-density-scale" />
            <span>More records per hexagonal bin</span>
          </div>
          <p className="map-provider-note">
            Recording density, not abundance. Blank areas do not prove absence.
            Only downloaded areas are saved.
          </p>
        </div>
      )}
    </>
  );
  // Avoid duplicate Load controls in the default map pane; the idle inspector retains local context.
  if (inspector)
    return (
      <MapWorkspace
        browserLabel="Inspector"
        browser={
          summary ? (
            details
          ) : (
            <section>
              {inspector}
              {dataDetails}
            </section>
          )
        }
      >
        {canvas}
      </MapWorkspace>
    );
  return (
    <section className="occurrence-map-panel" aria-label="Occurrence evidence">
      {canvas}
      {summary ? details : dataDetails}
    </section>
  );
}
