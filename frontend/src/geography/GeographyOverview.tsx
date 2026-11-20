import { useEffect, useState, type ReactNode } from "react";
import {
  ApiError,
  isExpectedAuthCancellation,
  type ProtectedRequestCapability,
} from "../auth/api";
import { useAuth } from "../auth/context";
import { ActionLink } from "../components/Action";
import { getNativeOverview, listNativeIdentities } from "../native-ranges/api";
import { getCollectionProvenanceMap } from "../provenance-map/api";
import { recordHref, uniqueRecords } from "../provenance-map/model";
import { listRepresentedIdentities } from "../species-distribution/api";
import { GeographyHeader } from "./GeographyHeader";

const filters = { q: "", scope: "all", withRange: false, record: [] } as const;

async function nativeSummary(
  signal: AbortSignal,
  capability: ProtectedRequestCapability,
) {
  const [overview, page] = await Promise.all([
    getNativeOverview({ ...filters, record: [] }, 0, capability, signal),
    listNativeIdentities(
      { ...filters, withRange: true, record: [] },
      0,
      capability,
      signal,
    ),
  ]);
  return (
    <>
      <p className="geography-coverage">
        <strong>
          {overview.with_range} <span>of {overview.represented}</span>
        </strong>
        represented identities with structured ranges
      </p>
      <dl className="geography-summary-facts">
        <div>
          <dt>Without structured ranges</dt>
          <dd>{overview.without_range}</dd>
        </div>
        <div>
          <dt>Recorded named areas</dt>
          <dd>{overview.places_total}</dd>
        </div>
      </dl>
      {overview.with_range === 0 && (
        <p className="field-help">
          No structured native ranges recorded for represented identities.
        </p>
      )}
      {page.items.length > 0 && (
        <details className="geography-summary-links">
          <summary>Linked Botanical Identities</summary>
          <ul aria-label="Example identities with structured ranges">
            {page.items.slice(0, 2).map((identity) => (
              <li key={identity.id}>
                <a href={`#/identities/${identity.id}?tab=reference`}>
                  {identity.display_label}
                </a>
                {" · "}
                <a
                  href={`#/geography/native-ranges?mode=species&identity=${identity.id}`}
                >
                  Explore range
                </a>
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
async function distributionSummary(
  signal: AbortSignal,
  capability: ProtectedRequestCapability,
) {
  const page = await listRepresentedIdentities(
    "",
    "all",
    0,
    capability,
    signal,
  );
  return (
    <>
      <p className="geography-coverage">
        <strong>
          {page.occurrence_ready} <span>of {page.total}</span>
        </strong>
        represented identities with eligible confirmed GBIF links
      </p>
      <dl className="geography-summary-facts">
        <div>
          <dt>Represented identities</dt>
          <dd>{page.total}</dd>
        </div>
        <div>
          <dt>Occurrence counts</dt>
          <dd>Not checked here</dd>
        </div>
      </dl>
      <p className="field-help">
        {page.total
          ? "Inspect the selected species’ local cache or explicitly load GBIF evidence. Unknown occurrence totals are not zero."
          : "No collection identities represented yet. Add collection material to explore occurrence evidence."}
      </p>
    </>
  );
}
async function originsSummary(
  signal: AbortSignal,
  capability: ProtectedRequestCapability,
) {
  const data = await getCollectionProvenanceMap(capability, signal);
  const records = uniqueRecords(data.sites);
  return (
    <>
      <p className="geography-coverage">
        <strong>
          {data.sites.length} <span>of {data.total_provenance_sites}</span>
        </strong>
        recorded provenance sites with coordinates
      </p>
      <dl className="geography-summary-facts">
        <div>
          <dt>Without coordinates</dt>
          <dd>{data.coordinate_less_sites}</dd>
        </div>
        <div>
          <dt>Direct records at mapped sites</dt>
          <dd>{records.length}</dd>
        </div>
      </dl>
      <p className="field-help">
        {data.total_provenance_sites
          ? "Includes retained historical records. Record counts are not material quantities."
          : "No provenance sites recorded. Record operator-confirmed origins on collection material to establish links."}
      </p>
      {data.sites.length > 0 && (
        <details className="geography-summary-links">
          <summary>Linked sites and source records</summary>
          <ul aria-label="Example provenance sites">
            {data.sites.slice(0, 2).map((site) => (
              <li key={site.id}>
                <a href={`#/geography/${site.id}`}>{site.name}</a>
              </li>
            ))}
          </ul>
          {records.length > 0 && (
            <p>
              Source record:{" "}
              <a href={recordHref(records[0])}>
                {records[0].label ??
                  records[0].botanical_identity.display_label}
              </a>
            </p>
          )}
        </details>
      )}
    </>
  );
}

function EvidenceSummary({
  load,
}: {
  load: (
    signal: AbortSignal,
    capability: ProtectedRequestCapability,
  ) => Promise<ReactNode>;
}) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "error" }
    | { status: "ready"; content: ReactNode }
  >({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    void load(controller.signal, capability)
      .then((content) => {
        if (!controller.signal.aborted) setState({ status: "ready", content });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) sessionExpired();
        else setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, authorized, capability, load, sessionExpired]);
  if (state.status === "loading")
    return <p role="status">Loading local evidence…</p>;
  if (state.status === "error")
    return (
      <div role="alert">
        <p>
          Could not load this local summary. The workspace is still available.
        </p>
        <button
          type="button"
          className="button--secondary"
          onClick={() => {
            setState({ status: "loading" });
            setAttempt(attempt + 1);
          }}
        >
          Retry summary
        </button>
      </div>
    );
  return state.content;
}

export function GeographyOverview() {
  return (
    <section
      className="workspace geography-overview"
      aria-labelledby="geography-overview-title"
    >
      <GeographyHeader
        view="overview"
        description="Geographic evidence, botanical distribution and recorded collection provenance."
      />
      <div className="geography-overview-intro">
        <h3>Geographic overview</h3>
        <p>
          Three distinct evidence types. Explore existing coverage or manage
          geographic records.
        </p>
      </div>
      <h3 className="geography-coverage-title">Geographic coverage</h3>
      <div className="geography-destinations">
        <section aria-labelledby="geography-native-title">
          <div className="geography-summary-heading">
            <h4 id="geography-native-title">Native ranges</h4>
            <p className="geography-summary-description">
              Structured native-area assertions, separate from observed
              occurrences.
            </p>
          </div>
          <div className="geography-summary-body">
            <EvidenceSummary load={nativeSummary} />
          </div>
          <ActionLink
            href="#/geography/native-ranges"
            className="button-link button--secondary"
            icon="layers"
          >
            Explore native ranges
          </ActionLink>
        </section>
        <section aria-labelledby="geography-distribution-title">
          <div className="geography-summary-heading">
            <h4 id="geography-distribution-title">Species distribution</h4>
            <p className="geography-summary-description">
              Observed occurrence density; neither native range nor abundance.
            </p>
          </div>
          <div className="geography-summary-body">
            <EvidenceSummary load={distributionSummary} />
          </div>
          <ActionLink
            href="#/geography/species-distribution"
            className="button-link button--secondary"
            icon="layers"
          >
            Explore species distribution
          </ActionLink>
        </section>
        <section aria-labelledby="geography-origins-title">
          <div className="geography-summary-heading">
            <h4 id="geography-origins-title">Collection origins</h4>
            <p className="geography-summary-description">
              Operator-confirmed origins, separate from Suppliers and storage
              Locations.
            </p>
          </div>
          <div className="geography-summary-body">
            <EvidenceSummary load={originsSummary} />
          </div>
          <ActionLink
            href="#/geography/origins"
            className="button-link button--secondary"
            icon="layers"
          >
            Explore collection origins
          </ActionLink>
        </section>
      </div>
      <section
        className="geography-records"
        aria-labelledby="geography-records-title"
      >
        <h3 id="geography-records-title">Geographic records</h3>
        <p>
          Named places and precise provenance sites used by collection records.
        </p>
        <div>
          <a href="#/geography/places" aria-label="Places">
            <strong>Places</strong>
            <span>Hierarchical geographic places, canonical and local</span>
          </a>
          <a href="#/geography/sites" aria-label="Provenance sites">
            <strong>Provenance sites</strong>
            <span>
              Precise collection-origin sites and recorded coordinates
            </span>
          </a>
        </div>
      </section>
    </section>
  );
}
