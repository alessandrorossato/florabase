import { useEffect, useState, type SyntheticEvent } from "react";

import { ApiError } from "../auth/api";
import { InfoDisclosure } from "../components/ContextualHelp";
import { OverflowMenu } from "../components/ReferenceUI";
import { OccurrenceMapPanel } from "../occurrence-map/OccurrenceMapPanel";
import {
  confirmExternalTaxonLink,
  getExternalTaxonLink,
  refreshExternalTaxonLink,
  searchExternalTaxa,
  unlinkExternalTaxon,
  type ExternalTaxonLinkResponse,
  type TaxonSearchResponse,
} from "./api";

function providerError(error: unknown): string {
  if (error instanceof ApiError && error.status === 503) {
    return "GBIF is temporarily unavailable or rate limiting requests. Try again later.";
  }
  if (error instanceof ApiError && error.status === 404) {
    return "That GBIF taxon is no longer available.";
  }
  return "Florabase could not complete the GBIF request.";
}

function dateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function gbifTaxonUrl(externalId: string): string {
  return `https://www.gbif.org/taxon/${encodeURIComponent(externalId)}`;
}

function taxonDisplayName(link: ExternalTaxonLinkResponse): string {
  if (!link.authorship || link.scientific_name.endsWith(link.authorship))
    return link.scientific_name;
  return `${link.scientific_name} ${link.authorship}`;
}

export function ExternalBotanicalDataPanel({
  identityId,
  scientificName,
  csrfToken,
  view = "all",
}: {
  identityId: string;
  scientificName: string;
  csrfToken: string;
  view?: "all" | "source" | "occurrences";
}) {
  const [link, setLink] = useState<ExternalTaxonLinkResponse | null>(null);
  const [loadingLink, setLoadingLink] = useState(true);
  const [query, setQuery] = useState(scientificName);
  const [search, setSearch] = useState<TaxonSearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [changing, setChanging] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getExternalTaxonLink(identityId, controller.signal)
      .then(setLink)
      .catch(() => {
        if (!controller.signal.aborted)
          setError("Florabase could not load the external taxon link.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingLink(false);
      });
    return () => {
      controller.abort();
    };
  }, [identityId]);

  async function runSearch(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearching(true);
    setError(null);
    try {
      setSearch(await searchExternalTaxa(identityId, query));
    } catch (requestError: unknown) {
      setSearch(null);
      setError(providerError(requestError));
    } finally {
      setSearching(false);
    }
  }

  async function selectTaxon(externalId: string, scientificName: string) {
    setBusyId(externalId);
    setError(null);
    try {
      setLink(
        await confirmExternalTaxonLink(
          identityId,
          externalId,
          scientificName,
          csrfToken,
        ),
      );
      setChanging(false);
      setSearch(null);
    } catch (requestError: unknown) {
      setError(providerError(requestError));
    } finally {
      setBusyId(null);
    }
  }

  async function refresh() {
    setBusyId("refresh");
    setError(null);
    try {
      setLink(await refreshExternalTaxonLink(identityId, csrfToken));
    } catch (requestError: unknown) {
      setError(providerError(requestError));
    } finally {
      setBusyId(null);
    }
  }

  async function remove() {
    setBusyId("unlink");
    setError(null);
    try {
      await unlinkExternalTaxon(identityId, csrfToken);
      setLink(null);
      setChanging(false);
    } catch (requestError: unknown) {
      setError(providerError(requestError));
    } finally {
      setBusyId(null);
    }
  }

  const showSearch = !link || changing;
  return (
    <section
      className={`external-botany external-botany--${view}`}
      aria-labelledby={`external-botany-title-${view}`}
    >
      <div className="section-heading">
        <h3 id={`external-botany-title-${view}`}>
          {view === "occurrences" ? "Occurrences" : "External botanical source"}
        </h3>
      </div>
      {loadingLink && <p role="status">Loading external reference…</p>}
      {error && (
        <div className="notice notice--error" role="alert">
          {error}
        </div>
      )}
      {view !== "occurrences" && !loadingLink && link && (
        <article className="external-link-card">
          <div>
            <p className="eyebrow">Catalogue of Life XR via GBIF</p>
            <h4>
              <i>{taxonDisplayName(link)}</i>
            </h4>
            <p>
              {[link.rank, link.taxonomic_status, link.family, link.kingdom]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {link.accepted_name &&
              link.accepted_external_id !== link.external_id && (
                <p>
                  <strong>Accepted name:</strong> {link.accepted_name}
                </p>
              )}
            <p>
              GBIF taxon ID: <code>{link.external_id}</code>
            </p>
            <p>
              Last successful refresh: {dateTime(link.last_refreshed_at)}
              {link.stale ? " · cached data is stale" : ""}
            </p>
            {link.refresh_error && (
              <p className="notice notice--warning" role="status">
                Refresh failed ({link.refresh_error}); retained cached data is
                shown.
              </p>
            )}
          </div>
          <div className="actions">
            <a
              className="button-link button--secondary"
              href={gbifTaxonUrl(link.external_id)}
              target="_blank"
              rel="noreferrer"
            >
              View taxon on GBIF
            </a>
            <button
              className="button--secondary"
              disabled={busyId !== null}
              type="button"
              onClick={() => void refresh()}
            >
              {busyId === "refresh" ? "Refreshing…" : "Refresh"}
            </button>
            <OverflowMenu>
              <>
                <button
                  className="button--secondary"
                  disabled={busyId !== null}
                  type="button"
                  onClick={() => {
                    setChanging((value) => !value);
                  }}
                >
                  {changing ? "Cancel change" : "Change link"}
                </button>
                <button
                  className="button--danger"
                  disabled={busyId !== null}
                  type="button"
                  onClick={() => {
                    void remove();
                  }}
                >
                  {busyId === "unlink" ? "Unlinking…" : "Unlink"}
                </button>
              </>
            </OverflowMenu>
          </div>
        </article>
      )}
      {view !== "occurrences" && !loadingLink && showSearch && (
        <div className="external-search">
          <InfoDisclosure label="About GBIF search and linking">
            Searching sends this botanical name to GBIF. A match never changes
            Florabase identity or profile data until you explicitly confirm it.
          </InfoDisclosure>
          <form onSubmit={(event) => void runSearch(event)}>
            <div className="field">
              <label htmlFor={`external-query-${identityId}`}>
                Scientific-name search
              </label>
              <input
                id={`external-query-${identityId}`}
                maxLength={255}
                required
                value={query}
                onChange={(event) => {
                  setQuery(event.currentTarget.value);
                }}
              />
            </div>
            <button disabled={searching} type="submit">
              {searching ? "Searching GBIF…" : "Search GBIF"}
            </button>
          </form>
          {search && (
            <div aria-live="polite">
              {search.stale && (
                <p className="notice notice--warning">
                  GBIF could not be reached. Cached results from{" "}
                  {dateTime(search.fetched_at)} are shown.
                </p>
              )}
              {search.candidates.length === 0 ? (
                <div className="empty-state">
                  <p>
                    No GBIF candidates found. Adjust the query and try again.
                  </p>
                </div>
              ) : (
                <div className="external-candidates">
                  {search.candidates.map((candidate) => (
                    <article
                      key={candidate.external_id}
                      className="source-choice"
                    >
                      <h4>
                        <i>{candidate.scientific_name}</i>
                        {candidate.authorship ? ` ${candidate.authorship}` : ""}
                      </h4>
                      <p>
                        {[
                          candidate.rank,
                          candidate.taxonomic_status,
                          candidate.family,
                          candidate.kingdom,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                      {candidate.accepted_name &&
                        candidate.accepted_external_id !==
                          candidate.external_id && (
                          <p>
                            <strong>Accepted name:</strong>{" "}
                            {candidate.accepted_name}
                          </p>
                        )}
                      <p>
                        ID <code>{candidate.external_id}</code>
                        {candidate.match_type
                          ? ` · ${candidate.match_type} match`
                          : ""}
                        {candidate.confidence !== null
                          ? ` · confidence ${String(candidate.confidence)}`
                          : ""}
                      </p>
                      {(candidate.issues?.length ?? 0) > 0 && (
                        <p>GBIF flags: {candidate.issues?.join(", ")}</p>
                      )}
                      <button
                        disabled={busyId !== null}
                        type="button"
                        onClick={() =>
                          void selectTaxon(
                            candidate.external_id,
                            candidate.scientific_name,
                          )
                        }
                      >
                        {busyId === candidate.external_id
                          ? "Linking…"
                          : link
                            ? "Confirm replacement"
                            : "Confirm GBIF link"}
                      </button>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {view !== "source" && !loadingLink && (
        <OccurrenceMapPanel
          key={`${identityId}:${link?.external_id ?? "unlinked"}`}
          identityId={identityId}
          link={link}
        />
      )}
    </section>
  );
}
