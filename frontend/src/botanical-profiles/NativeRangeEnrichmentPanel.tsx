import { useEffect, useRef, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  getRangeSource,
  searchWcvpTaxa,
  confirmWcvpTaxon,
  createRangeProposal,
  listRangeProposals,
  applyRangeProposal,
  type SourceStatus,
  type WcvpTaxon,
  type RangeProposal,
} from "./enrichment-api";
import "./native-range-enrichment.css";

function eligible(taxon: WcvpTaxon) {
  return (
    taxon.status === "Accepted" &&
    taxon.accepted_id === taxon.external_id &&
    ["Species", "Subspecies", "Variety", "Form"].includes(taxon.rank)
  );
}

export function NativeRangeEnrichmentPanel({
  identityId,
  onApplied,
}: {
  identityId: string;
  onApplied: () => void;
}) {
  const auth = useAuth();
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<SourceStatus | null>(null);
  const [query, setQuery] = useState("");
  const [taxa, setTaxa] = useState<WcvpTaxon[]>([]);
  const [searched, setSearched] = useState(false);
  const [candidate, setCandidate] = useState<WcvpTaxon | null>(null);
  const [proposal, setProposal] = useState<RangeProposal | null>(null);
  const [history, setHistory] = useState<RangeProposal[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [attempt, setAttempt] = useState(0);
  const feedback = useRef<HTMLParagraphElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const operation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!open) return;
    const abort = new AbortController();
    void Promise.all([
      getRangeSource(identityId, abort.signal),
      listRangeProposals(identityId, abort.signal),
    ])
      .then(([status, previous]) => {
        setSource(status);
        setHistory(previous);
      })
      .catch((err: unknown) => {
        if (!abort.signal.aborted) {
          if (err instanceof ApiError && err.status === 401)
            auth.sessionExpired();
          else setError("Could not load the source. Retry source status.");
        }
      });
    return () => {
      abort.abort();
    };
  }, [open, identityId, attempt, auth]);
  useEffect(() => {
    if (source?.available) search.current?.focus();
  }, [source?.available]);
  useEffect(() => {
    if (error || success) feedback.current?.focus();
  }, [error, success]);
  useEffect(
    () => () => {
      operation.current++;
      controller.current?.abort();
    },
    [identityId],
  );

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrf = auth.state.csrfToken;

  async function run(action: () => Promise<void>) {
    if (busy) return;
    const current = ++operation.current;
    setBusy(true);
    setError("");
    setSuccess("");
    setConfirming(false);
    try {
      await action();
    } catch (err: unknown) {
      if (operation.current !== current) return;
      if (err instanceof ApiError && err.status === 401) auth.sessionExpired();
      else
        setError(
          err instanceof ApiError && err.status === 409
            ? "This proposal or its destination changed. Retry source status, reconfirm the taxon if needed, and retrieve a new proposal. No ranges were changed."
            : "The trusted-source request failed. Your recorded ranges and previous evidence remain available. Retry the request.",
        );
    } finally {
      if (operation.current === current) setBusy(false);
    }
  }

  return (
    <section
      className="range-enrichment"
      aria-label="Trusted native-range source"
    >
      {!open ? (
        <button
          type="button"
          className="button--secondary"
          onClick={() => {
            setOpen(true);
          }}
        >
          Check trusted source
        </button>
      ) : (
        <>
          <h5>Review source range</h5>
          <p>
            Compare Kew WCVP evidence with your recorded range. Only reviewed
            mapped Native assertions can be added. Existing ranges are kept.
          </p>
          {!source && !error && <p role="status">Loading source status…</p>}
          {error && (
            <p
              ref={feedback}
              tabIndex={-1}
              role="alert"
              className="notice notice--error"
            >
              {error}
            </p>
          )}
          {success && (
            <p
              ref={feedback}
              tabIndex={-1}
              role="status"
              className="notice notice--success"
            >
              {success}
            </p>
          )}
          <button
            type="button"
            className="button--secondary"
            disabled={busy}
            onClick={() => {
              setError("");
              setAttempt((a) => a + 1);
            }}
          >
            Retry source status
          </button>
          {source && !source.available && (
            <p className="notice">
              {source.message} Recorded ranges remain usable. Ask your
              installation operator to provision the reviewed snapshot.
            </p>
          )}
          {source?.source && (
            <details className="range-source">
              <summary>
                Kew WCVP v{source.source.version} · source and attribution
              </summary>
              <p>
                Archive retrieved {source.source.retrieved_at}. Complete local
                snapshot.
              </p>
              <p>{source.source.citation}</p>
              <p>
                <a
                  href={source.source.license}
                  target="_blank"
                  rel="noreferrer"
                >
                  CC BY 3.0
                </a>{" "}
                ·{" "}
                <a
                  href={source.source.archive_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Official archive
                </a>
              </p>
              <p className="range-checksum">
                SHA-256: {source.source.checksum}
              </p>
              <p>
                Florabase maps only reviewed equivalent TDWG units. Kew cannot
                warrant the quality or accuracy of these data. This service is
                not endorsed by Kew.
              </p>
            </details>
          )}
          {source?.link && (
            <p>
              Confirmed taxon:{" "}
              <strong>
                {source.link.taxon.name} {source.link.taxon.authorship}
              </strong>{" "}
              · {source.link.taxon.rank} · WCVP {source.link.taxon.external_id}
              {source.link.stale &&
                " · Identity or source changed: confirm a match again."}
            </p>
          )}
          {source?.available && (
            <>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void run(async () => {
                    controller.current?.abort();
                    const abort = new AbortController();
                    controller.current = abort;
                    const results = await searchWcvpTaxa(
                      identityId,
                      query,
                      abort.signal,
                    );
                    if (abort.signal.aborted) return;
                    setTaxa(results);
                    setSearched(true);
                    setCandidate(null);
                  });
                }}
              >
                <div className="field">
                  <label htmlFor={`wcvp-query-${identityId}`}>
                    WCVP scientific name (literal prefix)
                  </label>
                  <input
                    ref={search}
                    id={`wcvp-query-${identityId}`}
                    value={query}
                    minLength={2}
                    maxLength={200}
                    required
                    disabled={busy}
                    onChange={(event) => {
                      setQuery(event.currentTarget.value);
                      setCandidate(null);
                      setTaxa([]);
                      setSearched(false);
                    }}
                  />
                </div>
                <button
                  disabled={busy || query.trim().length < 2}
                  type="submit"
                >
                  Search WCVP taxa
                </button>
              </form>
              {searched && (
                <fieldset disabled={busy}>
                  <legend>Review exact taxon · up to 25 results</legend>
                  {taxa.length === 0 && (
                    <p>No matching taxon in this snapshot.</p>
                  )}
                  {taxa.map((taxon) => (
                    <label key={taxon.external_id} className="range-taxon">
                      <input
                        type="radio"
                        name={`wcvp-taxon-${identityId}`}
                        disabled={!eligible(taxon)}
                        checked={candidate?.external_id === taxon.external_id}
                        onChange={() => {
                          setCandidate(taxon);
                        }}
                      />
                      <span>
                        <strong>
                          {taxon.name} {taxon.authorship}
                        </strong>
                        <small>
                          {taxon.rank} · {taxon.status} · WCVP{" "}
                          {taxon.external_id}
                        </small>
                        {taxon.accepted_name &&
                          taxon.accepted_id !== taxon.external_id && (
                            <small>
                              Accepted context: {taxon.accepted_name} ·{" "}
                              {taxon.accepted_id}. Search and confirm that
                              accepted taxon separately.
                            </small>
                          )}
                      </span>
                    </label>
                  ))}
                </fieldset>
              )}
              {candidate && (
                <div className="notice">
                  <p>
                    Confirm{" "}
                    <strong>
                      {candidate.name} {candidate.authorship}
                    </strong>
                    , WCVP {candidate.external_id}, for this Florabase identity.
                    Scientific-name similarity alone does not establish a match.
                  </p>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      void run(async () => {
                        if (!source.source) return;
                        const link = await confirmWcvpTaxon(
                          identityId,
                          candidate,
                          source.source.checksum,
                          csrf,
                        );
                        setSource({ ...source, link });
                        setCandidate(null);
                        setProposal(null);
                        setSelected([]);
                        setSuccess(
                          "WCVP taxon confirmed. Retrieve a proposal to review its distribution.",
                        );
                      });
                    }}
                  >
                    Confirm this taxon
                  </button>
                </div>
              )}
              {source.link && !source.link.stale && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    void run(async () => {
                      const next = await createRangeProposal(identityId, csrf);
                      setProposal(next);
                      setSelected(
                        next.choices
                          .filter((c) => c.change === "ADD")
                          .map((c) => c.place_id),
                      );
                      setHistory(await listRangeProposals(identityId));
                    });
                  }}
                >
                  Retrieve source proposal
                </button>
              )}
            </>
          )}
          {busy && <p role="status">Working with trusted-source evidence…</p>}
          {proposal && (
            <section
              aria-label="Native-range proposal"
              className="range-proposal"
            >
              <h5>Current vs proposed range</h5>
              <p>
                Frozen Kew WCVP v{proposal.source.version} ·{" "}
                {proposal.taxon.name} {proposal.taxon.authorship} · WCVP{" "}
                {proposal.taxon.external_id}
              </p>
              <p>
                Evidence retrieved{" "}
                {new Date(proposal.retrieved_at).toLocaleString()}. Destination
                revision {proposal.destination_version}.
              </p>
              <details className="range-source">
                <summary>Exact proposal source and crosswalk</summary>
                <p>{proposal.source.citation}</p>
                <p>{proposal.source.archive_url}</p>
                <p className="range-checksum">
                  SHA-256: {proposal.source.checksum}
                </p>
                <p>Crosswalk: {proposal.crosswalk_version}</p>
                <p>
                  <a
                    href={proposal.source.license}
                    target="_blank"
                    rel="noreferrer"
                  >
                    CC BY 3.0
                  </a>
                  . Original TDWG assertions are retained below. Kew cannot
                  warrant data accuracy. This service is not endorsed by Kew.
                </p>
              </details>
              {proposal.applied_at && (
                <p className="notice">
                  Applied {new Date(proposal.applied_at).toLocaleString()}. This
                  frozen evidence is retained.
                  {proposal.application && (
                    <>
                      {" "}
                      Added {proposal.application.added.length} ranges; kept{" "}
                      {proposal.application.kept.length}; removed none.
                    </>
                  )}
                </p>
              )}
              {proposal.choices.length === 0 && (
                <p>No current or applicable proposed ranges.</p>
              )}
              <ul className="range-proposal-list">
                {proposal.choices.map((choice) => (
                  <li key={choice.place_id}>
                    <label>
                      <input
                        type="checkbox"
                        checked={selected.includes(choice.place_id)}
                        disabled={
                          busy ||
                          Boolean(proposal.applied_at) ||
                          choice.change === "CURRENT-ONLY"
                        }
                        onChange={(event) => {
                          const checked = event.currentTarget.checked;
                          setConfirming(false);
                          setSelected((ids) =>
                            checked
                              ? [...ids, choice.place_id]
                              : ids.filter((id) => id !== choice.place_id),
                          );
                        }}
                      />
                      <span>
                        <strong>
                          {choice.change}: {choice.name}
                        </strong>
                        <small>{choice.path}</small>
                        {choice.change === "CURRENT-ONLY" && (
                          <small>
                            Recorded range absent from applicable source
                            evidence. Kept.
                          </small>
                        )}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
              <details>
                <summary>
                  Original source evidence ({proposal.assertions.length})
                </summary>
                {proposal.assertions.length === 0 && (
                  <p>No distribution assertions for this taxon.</p>
                )}
                <ul className="range-proposal-list">
                  {proposal.assertions.map((assertion) => (
                    <li key={assertion.assertion_id}>
                      <strong>
                        {assertion.status === "native"
                          ? "Native"
                          : assertion.status === "introduced"
                            ? "Introduced — context only"
                            : "Qualified — context only"}
                        : {assertion.original.area || "Unnamed area"} (
                        {assertion.original.area_code_l3 || "no level-3 code"})
                      </strong>
                      <small>
                        {assertion.mapping === "equivalent"
                          ? "Mapped equivalent unit"
                          : "UNMAPPED SOURCE"}{" "}
                        · {assertion.note}
                      </small>
                      <small>
                        Assertion {assertion.assertion_id} · introduced=
                        {assertion.original.introduced}, extinct=
                        {assertion.original.extinct}, doubtful=
                        {assertion.original.location_doubtful} · TDWG region{" "}
                        {assertion.original.region_code_l2}
                      </small>
                    </li>
                  ))}
                </ul>
              </details>
              {!proposal.applied_at && (
                <>
                  <button
                    type="button"
                    disabled={busy || selected.length === 0}
                    onClick={() => {
                      setConfirming(true);
                    }}
                  >
                    Apply reviewed changes
                  </button>
                  {confirming && (
                    <div
                      className="notice"
                      role="region"
                      aria-label="Confirm native-range Apply"
                    >
                      <p>
                        Add{" "}
                        {
                          proposal.choices.filter(
                            (c) =>
                              selected.includes(c.place_id) &&
                              c.change === "ADD",
                          ).length
                        }{" "}
                        selected ranges. Keep all {proposal.current_ids.length}{" "}
                        existing ranges. Remove none. Apply this frozen WCVP v
                        {proposal.source.version} evidence?
                      </p>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          void run(async () => {
                            const result = await applyRangeProposal(
                              identityId,
                              proposal.id,
                              selected,
                              csrf,
                            );
                            setProposal({
                              ...proposal,
                              applied_at: result.applied_at,
                              application: result,
                            });
                            setSuccess(
                              `Applied ${String(result.added.length)} additions. Kept ${String(result.kept.length)} existing ranges.`,
                            );
                            onApplied();
                            try {
                              setHistory(await listRangeProposals(identityId));
                            } catch (err: unknown) {
                              if (err instanceof ApiError && err.status === 401)
                                auth.sessionExpired();
                              else
                                setError(
                                  "Apply succeeded. Recent proposals could not be refreshed; retry source status.",
                                );
                            }
                          });
                        }}
                      >
                        Confirm Apply
                      </button>
                      <button
                        type="button"
                        className="button--secondary"
                        onClick={() => {
                          setConfirming(false);
                        }}
                      >
                        Cancel Apply
                      </button>
                    </div>
                  )}
                </>
              )}
            </section>
          )}
          {history.length > 0 && (
            <details>
              <summary>Recent retained proposals ({history.length})</summary>
              <ul>
                {history.map((previous) => (
                  <li key={previous.id}>
                    <button
                      type="button"
                      className="button--secondary"
                      disabled={busy}
                      onClick={() => {
                        setProposal(previous);
                        setSelected(previous.application?.added ?? []);
                        setConfirming(false);
                      }}
                    >
                      {previous.taxon.name} ·{" "}
                      {new Date(previous.created_at).toLocaleString()} ·{" "}
                      {previous.applied_at ? "Applied" : "Review pending"}
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </section>
  );
}
