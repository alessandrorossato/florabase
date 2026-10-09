import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  getIdentityTaxonomy,
  searchCandidates,
  confirmLink,
  unlink,
  type IdentityTaxonomy,
  type Candidate,
} from "./api";
import "./taxonomy.css";

export function IdentityTaxonomyPanel({
  identityId,
  updatedAt,
  summary = false,
}: {
  identityId: string;
  updatedAt: string;
  summary?: boolean;
}) {
  const auth = useAuth();
  const csrfToken = "csrfToken" in auth.state ? auth.state.csrfToken : null;
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    data?: IdentityTaxonomy;
    failed?: boolean;
  } | null>(null);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState<{ query: string } | null>(null);
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const key = `${identityId}:${updatedAt}:${String(attempt)}`;
  useEffect(() => {
    const controller = new AbortController();
    void getIdentityTaxonomy(identityId, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setResult({ key, failed: true });
      });
    return () => {
      controller.abort();
    };
  }, [identityId, key, auth]);
  useEffect(() => {
    if (!submitted) return;
    const controller = new AbortController();
    void searchCandidates(identityId, submitted.query, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setCandidates(data);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          if (error instanceof ApiError && error.status === 401)
            auth.sessionExpired();
          else
            setError(
              "Could not search the local taxonomy source. Retry search.",
            );
        }
      });
    return () => {
      controller.abort();
    };
  }, [identityId, submitted, auth]);
  const current = result?.key === key ? result : null;
  const data = current?.data;
  const link = data?.link;
  const valid =
    link &&
    !link.stale &&
    data.source_available &&
    link.evidence.source.checksum === data.source?.checksum &&
    link.evidence.source.version === data.source.version &&
    !data.message;
  const linkUrl = `#/identities/${identityId}?tab=taxonomy`;
  async function mutate(remove = false) {
    if (!csrfToken || !data || busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (remove && link) await unlink(identityId, link.version, csrfToken);
      else if (candidate && data.source)
        await confirmLink(
          identityId,
          {
            source_taxon_id: candidate.taxon.source_taxon_id,
            checksum: data.source.checksum,
            expected_version: link?.version ?? null,
            identity_updated_at: updatedAt,
          },
          csrfToken,
        );
      setCandidate(null);
      setCandidates(null);
      setSubmitted(null);
      setAttempt(attempt + 1);
      setNotice(
        remove
          ? "Taxonomy link removed."
          : "Taxonomy link confirmed. Botanical identity names are unchanged.",
      );
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else
        setError(
          error instanceof ApiError && error.status === 409
            ? "Identity or link changed. Reload taxonomy and review again."
            : "Could not save the taxonomy link. Retry after reviewing the source.",
        );
    } finally {
      setBusy(false);
    }
  }
  const breadcrumb = valid && (
    <nav aria-label="Taxonomy classification">
      <ol className="taxonomy-path">
        {link.evidence.classification.map((taxon) => (
          <li key={taxon.source_taxon_id}>
            <a href={`#/taxonomy?taxon=${taxon.source_taxon_id}`}>
              {taxon.scientific_name}
            </a>{" "}
            <span className="taxonomy-meta">{taxon.rank}</span>
          </li>
        ))}
      </ol>
    </nav>
  );
  if (summary)
    return (
      <section className="taxonomy-panel" aria-label="Taxonomy">
        <h3>Taxonomy</h3>
        {breadcrumb}
        <a href={linkUrl}>
          {link ? "Review taxonomy source" : "Link taxonomy source"}
        </a>
        {link && !valid && (
          <p>
            {link.stale
              ? "Identity changed since source confirmation."
              : (data.message ??
                "Taxonomy source is unavailable or differs from the confirmed version.")}
          </p>
        )}
        {valid && (
          <>
            <p>
              <a
                href={`#/taxonomy?taxon=${link.evidence.classification.at(-1)?.source_taxon_id ?? ""}`}
              >
                View in Taxonomy
              </a>
            </p>
            <Related data={data} />
          </>
        )}
      </section>
    );
  return (
    <section className="taxonomy-panel" aria-label="Taxonomy source">
      <h3>Taxonomy source</h3>
      <p>
        Confirm a WFO classification after reviewing the exact name, authorship
        and hierarchy. Local scientific names and collection Lineage remain
        unchanged.
      </p>
      {!current && <p role="status">Loading taxonomy source…</p>}
      {current?.failed && <p role="alert">Could not load taxonomy source.</p>}
      <button
        type="button"
        className="button--secondary"
        onClick={() => {
          setAttempt(attempt + 1);
          setCandidate(null);
          setCandidates(null);
          setSubmitted(null);
          setError(null);
        }}
      >
        Reload taxonomy
      </button>
      {data && (
        <>
          {!data.source_available && (
            <p>Taxonomy source unavailable. {data.message}</p>
          )}
          {data.source && (
            <p>
              World Flora Online — {data.source.version} ·{" "}
              <a href={data.source.license} target="_blank" rel="noreferrer">
                CC0
              </a>{" "}
              ·{" "}
              <a
                href="https://zenodo.org/records/20782718"
                target="_blank"
                rel="noreferrer"
              >
                Source release
              </a>
            </p>
          )}
          {link && (
            <>
              <h4>Confirmed source name</h4>
              <p>
                {link.evidence.taxon.scientific_name}{" "}
                {link.evidence.taxon.authorship} · {link.evidence.taxon.rank} ·{" "}
                {link.evidence.taxon.taxonomic_status} ·{" "}
                {link.evidence.taxon.source_taxon_id}
              </p>
              <p>
                Confirmed release {link.evidence.source.version} ·{" "}
                {new Date(link.confirmed_at).toLocaleDateString()}
              </p>
              {link.evidence.taxon.taxonomic_status === "synonym" && (
                <p>
                  WFO treats this name as a synonym of{" "}
                  {link.evidence.classification.at(-1)?.scientific_name}. This
                  is advisory.
                </p>
              )}
              {!valid && (
                <p>
                  {link.stale
                    ? "Identity changed since source confirmation; review before placement."
                    : (data.message ??
                      "Source version differs from confirmed evidence.")}
                </p>
              )}
              {breadcrumb}
              <button
                type="button"
                className="button--secondary"
                disabled={busy}
                onClick={() => {
                  void mutate(true);
                }}
              >
                Unlink taxonomy source
              </button>
            </>
          )}
          {!link && <p>No taxonomy source is linked.</p>}
          {data.source_available && (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                setCandidates(null);
                setCandidate(null);
                setError(null);
                setSubmitted({ query: query.trim() });
              }}
            >
              <label className="taxonomy-search">
                Search WFO names
                <input
                  value={query}
                  minLength={2}
                  maxLength={200}
                  required
                  onChange={(event) => {
                    setQuery(event.target.value);
                  }}
                />
              </label>
              <button type="submit">Search taxonomy source</button>
            </form>
          )}
          {submitted && !candidates && !error && (
            <p role="status">Searching local source…</p>
          )}
          {candidates && (
            <>
              <p>
                {candidates.length
                  ? "Select a candidate to inspect. Results are limited to 25 literal name-prefix matches."
                  : "No source candidates match this prefix."}
              </p>
              <ul>
                {candidates.map((item) => (
                  <li key={item.taxon.source_taxon_id}>
                    <button
                      type="button"
                      className="button--secondary"
                      aria-pressed={
                        candidate?.taxon.source_taxon_id ===
                        item.taxon.source_taxon_id
                      }
                      onClick={() => {
                        setCandidate(item);
                      }}
                    >
                      {item.taxon.scientific_name} {item.taxon.authorship} ·{" "}
                      {item.taxon.rank} · {item.taxon.taxonomic_status} ·{" "}
                      {item.taxon.source_taxon_id}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
          {candidate && (
            <div className="notice">
              <h4>Review exact source taxon</h4>
              <p>
                {candidate.taxon.scientific_name} {candidate.taxon.authorship} ·{" "}
                {candidate.taxon.source_taxon_id} · {candidate.taxon.rank} ·{" "}
                {candidate.taxon.taxonomic_status}
              </p>
              {candidate.taxon.taxonomic_status === "synonym" && (
                <p>
                  WFO treats this name as a synonym of{" "}
                  {candidate.classification.at(-1)?.scientific_name}.
                </p>
              )}
              <ol className="taxonomy-path">
                {candidate.classification.map((taxon) => (
                  <li key={taxon.source_taxon_id}>
                    {taxon.scientific_name} · {taxon.rank}
                  </li>
                ))}
              </ol>
              {!candidate.classification.length && (
                <p>
                  This source name has no classified usage. It cannot be placed
                  in collection taxonomy.
                </p>
              )}
              {link && (
                <p>
                  Confirmation replaces the current taxonomy link to{" "}
                  {link.evidence.taxon.scientific_name}.
                </p>
              )}
              <button
                type="button"
                disabled={
                  busy ||
                  !data.source_available ||
                  !candidate.classification.length
                }
                onClick={() => {
                  void mutate();
                }}
              >
                Confirm taxonomy link
              </button>
            </div>
          )}
          {valid && <Related data={data} />}
        </>
      )}
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
    </section>
  );
}
function Related({ data }: { data: IdentityTaxonomy }) {
  return (
    <section aria-label="Related in my collection">
      <h4>Related in my collection</h4>
      <p>
        Taxonomic classification, without a claim about genetic distance. All
        represented collection identities.
      </p>
      {data.related?.length ? (
        <ul>
          {data.related.map((peer) => (
            <li key={peer.identity.id}>
              <a href={`#/identities/${peer.identity.id}`}>
                {peer.identity.display_label}
              </a>{" "}
              · {peer.relation}
            </li>
          ))}
        </ul>
      ) : (
        <p>
          No other represented identities share a classified genus, family or
          order.
        </p>
      )}
    </section>
  );
}
