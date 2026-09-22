import { lazy, Suspense, useState } from "react";

import type { ExternalTaxonLinkResponse } from "../botanical-identities/api";
import { InfoDisclosure } from "../components/ContextualHelp";
import { getOccurrenceMapSummary, type OccurrenceMapSummary } from "./api";

const OccurrenceDensityMap = lazy(async () => {
  const module = await import("./OccurrenceDensityMap");
  return { default: module.OccurrenceDensityMap };
});

type OccurrenceState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; summary: OccurrenceMapSummary }
  | { status: "error" };

function dateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function number(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export function OccurrenceMapPanel({
  identityId,
  link,
}: {
  identityId: string;
  link: ExternalTaxonLinkResponse | null;
}) {
  const [state, setState] = useState<OccurrenceState>({ status: "idle" });

  async function load() {
    setState({ status: "loading" });
    try {
      setState({
        status: "ready",
        summary: await getOccurrenceMapSummary(identityId),
      });
    } catch {
      setState({ status: "error" });
    }
  }

  return (
    <section
      className="occurrence-map-panel"
      aria-labelledby={`occurrence-map-title-${identityId}`}
    >
      <div className="section-heading">
        <div>
          <h4 id={`occurrence-map-title-${identityId}`}>Occurrence evidence</h4>
          <p>GBIF occurrence data · not native-range data</p>
        </div>
      </div>

      {!link ? (
        <div className="empty-state">
          <p>
            Confirm a GBIF taxon link above before loading occurrence evidence.
            Florabase will not search by the identity name automatically.
          </p>
        </div>
      ) : (
        <>
          <InfoDisclosure label="Occurrence evidence and privacy">
            Florabase asks GBIF for the exact linked taxon. Occurrence records
            are evidence of observations, not native-range data. Collection
            records, notes, account identity, and physical location are not
            sent; visible-area basemap tile requests follow the collection-map
            privacy model.
          </InfoDisclosure>
          {state.status === "idle" && (
            <button type="button" onClick={() => void load()}>
              Load GBIF occurrence map
            </button>
          )}
          {state.status === "loading" && (
            <p aria-live="polite">Loading GBIF occurrence summary…</p>
          )}
          {state.status === "error" && (
            <div className="notice notice--error" role="alert">
              <p>
                GBIF occurrence evidence is temporarily unavailable. Your
                Florabase botanical and collection data remain available.
              </p>
              <button type="button" onClick={() => void load()}>
                Retry
              </button>
            </div>
          )}
          {state.status === "ready" && (
            <>
              <button
                className="button--secondary"
                type="button"
                onClick={() => void load()}
              >
                Refresh occurrence evidence
              </button>
              <OccurrenceSummary
                identityId={identityId}
                summary={state.summary}
              />
            </>
          )}
        </>
      )}
    </section>
  );
}

function OccurrenceSummary({
  identityId,
  summary,
}: {
  identityId: string;
  summary: OccurrenceMapSummary;
}) {
  const [tileFailure, setTileFailure] = useState(false);
  const [mapAttempt, setMapAttempt] = useState(0);
  const excluded =
    summary.total_matching_records - summary.eligible_mapped_records;
  return (
    <div className="occurrence-summary" aria-live="polite">
      <dl className="detail-list detail-list--compact">
        <div>
          <dt>Taxon mapped</dt>
          <dd>
            <a
              href={summary.taxon_provider_url}
              target="_blank"
              rel="noreferrer"
            >
              <i>{summary.taxon_scientific_name}</i>
            </a>{" "}
            · <code>{summary.external_taxon_id}</code>
          </dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>
            <a href={summary.provider_url} target="_blank" rel="noreferrer">
              {summary.source}
            </a>
          </dd>
        </div>
        <div>
          <dt>Eligible mapped records</dt>
          <dd>{number(summary.eligible_mapped_records)}</dd>
        </div>
        <div>
          <dt>All matching PRESENT records</dt>
          <dd>{number(summary.total_matching_records)}</dd>
        </div>
        <div>
          <dt>Checked</dt>
          <dd>{dateTime(summary.retrieved_at)}</dd>
        </div>
        <div>
          <dt>Taxonomy</dt>
          <dd>
            {summary.checklist_name} · <code>{summary.checklist_key}</code>
          </dd>
        </div>
      </dl>

      <section aria-labelledby={`quality-title-${identityId}`}>
        <h5 id={`quality-title-${identityId}`}>Mapping and quality policy</h5>
        <p>
          The map includes PRESENT records with usable coordinates and excludes
          records GBIF flags as having a geospatial issue.{" "}
          {excluded >= 0 ? (
            <>
              {number(excluded)} matching{" "}
              {excluded === 1 ? "record is" : "records are"} outside this mapped
              subset.
            </>
          ) : (
            <>
              The two live counts changed while GBIF processed them, so the
              eligible mapped count is the map’s current reference.
            </>
          )}{" "}
          Provider flags cannot eliminate every uncertainty or error.
        </p>
      </section>

      {summary.eligible_mapped_records === 0 ? (
        <div className="empty-state">
          <h5>No mapped occurrence records</h5>
          <p>
            The confirmed taxon is valid, but GBIF currently has no matching
            records that satisfy this map’s coordinate and quality policy.
          </p>
        </div>
      ) : (
        <div className="occurrence-map-layout">
          <div className="map-canvas-card">
            {tileFailure && (
              <div className="notice notice--error" role="alert">
                <p>
                  Some GBIF occurrence tiles could not be loaded. The textual
                  summary remains available.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setTileFailure(false);
                    setMapAttempt((value) => value + 1);
                  }}
                >
                  Reload map tiles
                </button>
              </div>
            )}
            <Suspense
              fallback={<p aria-live="polite">Loading occurrence map…</p>}
            >
              <OccurrenceDensityMap
                key={mapAttempt}
                identityId={identityId}
                onTileError={() => {
                  setTileFailure(true);
                }}
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
              Hexagons show GBIF occurrence-record density at the current zoom,
              not plant abundance. This raster does not expose an exact count
              for each visible bin; the exact overall eligible count is shown
              above.
            </p>
          </div>
        </div>
      )}

      <div className="occurrence-cautions">
        <h5>How to interpret this evidence</h5>
        <p>
          An occurrence means a specimen or observation was recorded; it does
          not mean the taxon is native there. Density reflects sampling and
          reporting effort, not biological abundance. Coordinates may be
          generalized, obscured, uncertain, erroneous, historical, cultivated,
          or introduced.
        </p>
        <p>
          This live view does not modify BotanicalIdentity, BotanicalProfile,
          Florabase’s structured native ranges, or the separate collection
          provenance map.
        </p>
        <p>
          Attribution: {summary.attribution}. Underlying records retain their
          contributing datasets’ licences and attribution requirements; they do
          not share one blanket licence. Review the{" "}
          <a href={summary.licensing_url} target="_blank" rel="noreferrer">
            GBIF terms and data-user requirements
          </a>
          .
        </p>
      </div>
    </div>
  );
}
