import { useEffect, useState, type SyntheticEvent } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { FieldLabel } from "../components/FieldLabel";
import { BotanicalName } from "../components/ReferenceUI";
import {
  correctBotanicalIdentityAcceptedName,
  getBotanicalIdentityReconciliation,
  mergeDuplicateBotanicalIdentity,
  type AcceptedNameSuggestionResponse,
  type BotanicalIdentityResponse,
  type CollidingIdentitySummary,
  type IdentityReconciliationResponse,
} from "./api";

const STATUS_KIND_LABELS: Record<string, string> = {
  initial_recorded: "Original acquisition / recorded name",
  former_accepted: "Former accepted name",
  merged_duplicate: "Merged duplicate identity name",
  source_synonym: "Source synonym",
  operator_synonym: "Operator synonym",
};

function errorMessage(error: unknown, fallback: string): string {
  if (
    error instanceof ApiError &&
    typeof error.body === "object" &&
    error.body !== null &&
    "detail" in error.body
  ) {
    const detail = (error.body as { detail?: unknown }).detail;
    if (
      typeof detail === "object" &&
      detail !== null &&
      "message" in detail &&
      typeof (detail as { message?: unknown }).message === "string"
    ) {
      return (detail as { message: string }).message;
    }
  }
  return fallback;
}

export function IdentityReconciliationPanel({
  identity,
  csrfToken,
  onIdentityUpdated,
}: {
  identity: BotanicalIdentityResponse;
  csrfToken: string;
  onIdentityUpdated: (updated: BotanicalIdentityResponse) => Promise<void>;
}) {
  const auth = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; data: IdentityReconciliationResponse }
  >({ status: "loading" });

  const [selectedSuggestion, setSelectedSuggestion] =
    useState<AcceptedNameSuggestionResponse | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualName, setManualName] = useState(identity.scientific_name);
  const [manualCultivar, setManualCultivar] = useState(
    identity.cultivar_name ?? "",
  );
  const [manualCommonName, setManualCommonName] = useState(
    identity.common_name ?? "",
  );
  const [correctionNotes, setCorrectionNotes] = useState("");
  const [acknowledgeConflict, setAcknowledgeConflict] = useState(false);

  const [mergeTarget, setMergeTarget] =
    useState<CollidingIdentitySummary | null>(null);
  const [keepSurvivorProfile, setKeepSurvivorProfile] = useState(false);
  const [mergeNotes, setMergeNotes] = useState("");

  const [busy, setBusy] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getBotanicalIdentityReconciliation(identity.id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setState({ status: "ready", data });
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) {
          auth.sessionExpired();
          return;
        }
        setState({
          status: "error",
          message:
            "Could not load accepted-name reconciliation evidence. Retry to inspect suggestions.",
        });
      });
    return () => {
      controller.abort();
    };
  }, [identity.id, identity.updated_at, attempt, auth]);

  async function submitSuggestionCorrection(
    event: SyntheticEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    if (busy || !selectedSuggestion || state.status !== "ready") return;
    setBusy(true);
    setMutationError(null);
    setNotice(null);
    try {
      const updated = await correctBotanicalIdentityAcceptedName(
        identity.id,
        {
          scientific_name: selectedSuggestion.accepted_scientific_name,
          cultivar_name: identity.cultivar_name ?? null,
          common_name: identity.common_name ?? null,
          identity_updated_at: state.data.identity.updated_at,
          source_provider: selectedSuggestion.source_provider,
          source_version: selectedSuggestion.source_version ?? null,
          source_checksum: selectedSuggestion.source_checksum ?? null,
          link_version: selectedSuggestion.link_version ?? null,
          matched_taxon_id: selectedSuggestion.matched_taxon_id,
          accepted_taxon_id: selectedSuggestion.accepted_taxon_id,
          accepted_authorship: selectedSuggestion.accepted_authorship ?? null,
          acknowledge_conflict: acknowledgeConflict,
          notes: correctionNotes.trim() || null,
        },
        csrfToken,
      );
      setSelectedSuggestion(null);
      setCorrectionNotes("");
      setAcknowledgeConflict(false);
      setState({ status: "ready", data: updated });
      await onIdentityUpdated(updated.identity);
      setNotice(
        `Accepted name corrected to ${updated.identity.display_label}. Historical name provenance is preserved.`,
      );
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
        return;
      }
      setMutationError(
        errorMessage(
          error,
          "Florabase could not apply the accepted-name correction.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitManualCorrection(
    event: SyntheticEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    if (busy || state.status !== "ready") return;
    setBusy(true);
    setMutationError(null);
    setNotice(null);
    try {
      const updated = await correctBotanicalIdentityAcceptedName(
        identity.id,
        {
          scientific_name: manualName,
          cultivar_name: manualCultivar.trim() || null,
          common_name: manualCommonName.trim() || null,
          identity_updated_at: state.data.identity.updated_at,
          source_provider: "operator",
          acknowledge_conflict: acknowledgeConflict,
          notes: correctionNotes.trim() || null,
        },
        csrfToken,
      );
      setManualOpen(false);
      setCorrectionNotes("");
      setAcknowledgeConflict(false);
      setState({ status: "ready", data: updated });
      await onIdentityUpdated(updated.identity);
      setNotice(
        `Accepted name corrected to ${updated.identity.display_label}. Historical name provenance is preserved.`,
      );
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
        return;
      }
      setMutationError(
        errorMessage(
          error,
          "Florabase could not apply the manual accepted-name correction.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitDuplicateMerge(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !mergeTarget || state.status !== "ready") return;
    setBusy(true);
    setMutationError(null);
    setNotice(null);
    try {
      const updated = await mergeDuplicateBotanicalIdentity(
        identity.id,
        {
          survivor_identity_id: mergeTarget.id,
          duplicate_updated_at: state.data.identity.updated_at,
          survivor_updated_at: mergeTarget.updated_at,
          profile_resolution: keepSurvivorProfile
            ? "keep_survivor"
            : "fail_on_conflict",
          notes: mergeNotes.trim() || null,
        },
        csrfToken,
      );
      setMergeTarget(null);
      setKeepSurvivorProfile(false);
      setMergeNotes("");
      await onIdentityUpdated(updated.identity);
      window.location.hash = `#/identities/${updated.identity.id}?tab=taxonomy`;
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
        return;
      }
      setMutationError(
        errorMessage(
          error,
          "Florabase could not merge the duplicate botanical identity.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="taxonomy-panel identity-reconciliation-panel"
      aria-label="Accepted-name reconciliation"
    >
      <h3>Accepted-name reconciliation</h3>
      <p>
        Inspect advisory accepted-name evidence, review version or cross-source
        conflicts, and explicitly confirm corrections without losing the name
        under which material was acquired or recorded.
      </p>

      {state.status === "loading" && (
        <p role="status">Loading accepted-name reconciliation…</p>
      )}
      {state.status === "error" && (
        <div className="notice notice--error" role="alert">
          <p>{state.message}</p>
          <button
            type="button"
            className="button--secondary"
            onClick={() => {
              setState({ status: "loading" });
              setAttempt((n) => n + 1);
            }}
          >
            Retry reconciliation check
          </button>
        </div>
      )}

      {mutationError && (
        <div className="notice notice--error" role="alert">
          <p>{mutationError}</p>
        </div>
      )}
      {notice && <p role="status">{notice}</p>}

      {state.status === "ready" && (
        <>
          <div className="reconciliation-provenance">
            <h4>Name provenance</h4>
            <p>
              <strong>Current active name:</strong>{" "}
              <BotanicalName
                label={state.data.identity.display_label}
                scientificName={state.data.identity.scientific_name}
              />
            </p>
            <p>
              <strong>Original recorded name:</strong>{" "}
              <BotanicalName
                label={state.data.original_display_label}
                scientificName={state.data.original_scientific_name}
              />
            </p>
            {state.data.former_names.length > 0 ? (
              <div>
                <h5>Retained historical &amp; merged names</h5>
                <ul>
                  {state.data.former_names.map((item) => (
                    <li key={item.id}>
                      <BotanicalName
                        label={item.display_label}
                        scientificName={item.scientific_name}
                      />
                      {item.authorship ? ` ${item.authorship}` : ""} ·{" "}
                      {STATUS_KIND_LABELS[item.status_kind] ?? item.status_kind}{" "}
                      · Source: {item.source_provider}
                      {item.source_version ? ` (${item.source_version})` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="field-help">
                No superseded names recorded yet; this identity retains its
                initial recorded name.
              </p>
            )}
          </div>

          {state.data.conflicts.length > 0 && (
            <div
              className="notice notice--warning"
              role="region"
              aria-label="Reconciliation conflicts"
            >
              <h4>Source &amp; identity conflicts</h4>
              <ul>
                {state.data.conflicts.map((conflict, idx) => (
                  <li key={`${conflict.kind}-${String(idx)}`}>
                    {conflict.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {state.data.source_assessments.length > 0 && (
            <div>
              <h4>Advisory source assessments</h4>
              <ul>
                {state.data.source_assessments.map((assessment, idx) => (
                  <li
                    key={`${assessment.source_provider}-${assessment.source_version ?? "default"}-${String(idx)}`}
                  >
                    <strong>{assessment.source_label}</strong>:{" "}
                    {assessment.status ?? "Unresolved"}
                    {assessment.scientific_name
                      ? ` · ${assessment.scientific_name}`
                      : ""}
                    {assessment.accepted_scientific_name &&
                    assessment.accepted_scientific_name.toLowerCase() !==
                      (assessment.scientific_name ?? "").toLowerCase()
                      ? ` → Accepted: ${assessment.accepted_scientific_name}`
                      : ""}
                    {assessment.stale ? " · (Stale link)" : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h4>Accepted-name suggestions</h4>
            {state.data.suggestions.length === 0 ? (
              <p>
                No advisory accepted-name changes are currently suggested by
                linked or local sources.
              </p>
            ) : (
              <ul>
                {state.data.suggestions.map((suggestion) => (
                  <li key={suggestion.suggestion_id}>
                    <p>
                      <strong>{suggestion.source_label}</strong> treats{" "}
                      <em>{suggestion.matched_scientific_name}</em>{" "}
                      {suggestion.matched_authorship ?? ""} (
                      {suggestion.matched_status}) as a synonym of{" "}
                      <strong>
                        <em>{suggestion.accepted_scientific_name}</em>
                      </strong>{" "}
                      {suggestion.accepted_authorship ?? ""} (
                      {suggestion.accepted_taxon_id}).
                    </p>
                    {suggestion.advisory_note && (
                      <p className="field-help">{suggestion.advisory_note}</p>
                    )}
                    {suggestion.colliding_identity ? (
                      <div className="notice">
                        <p>
                          <strong>Duplicate identity collision:</strong>{" "}
                          <a
                            href={`#/identities/${suggestion.colliding_identity.id}`}
                          >
                            {suggestion.colliding_identity.display_label}
                          </a>{" "}
                          already exists in your collection (Seed lots:{" "}
                          {
                            suggestion.colliding_identity.collection_counts
                              .seed_lots
                          }
                          , Plants:{" "}
                          {
                            suggestion.colliding_identity.collection_counts
                              .plants
                          }
                          , Plant groups:{" "}
                          {
                            suggestion.colliding_identity.collection_counts
                              .plant_groups
                          }
                          ). In-place renaming is refused so identities are
                          never merged silently.
                        </p>
                        <button
                          type="button"
                          className="button--secondary"
                          disabled={busy}
                          onClick={() => {
                            setSelectedSuggestion(null);
                            setManualOpen(false);
                            setMergeTarget(
                              suggestion.colliding_identity ?? null,
                            );
                            setKeepSurvivorProfile(false);
                            setMutationError(null);
                          }}
                        >
                          Review duplicate-identity reconciliation
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="button--secondary"
                        disabled={busy || suggestion.stale}
                        onClick={() => {
                          setMergeTarget(null);
                          setManualOpen(false);
                          setSelectedSuggestion(suggestion);
                          setAcknowledgeConflict(false);
                          setMutationError(null);
                        }}
                      >
                        Review accepted-name correction
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selectedSuggestion && (
            <form
              className="notice"
              aria-label="Confirm accepted-name correction"
              onSubmit={(event) => void submitSuggestionCorrection(event)}
            >
              <h4>Confirm accepted-name correction</h4>
              <p>
                Correct <strong>{state.data.identity.display_label}</strong> in
                place to{" "}
                <strong>{selectedSuggestion.accepted_scientific_name}</strong>{" "}
                {selectedSuggestion.accepted_authorship ?? ""} based on{" "}
                <strong>{selectedSuggestion.source_label}</strong> (
                {selectedSuggestion.accepted_taxon_id}).
              </p>
              <p className="field-help">
                This updates the BotanicalIdentity in place without changing its
                UUID or moving collection holdings, and records{" "}
                {state.data.identity.display_label} in the historical name
                ledger.
              </p>
              {state.data.has_source_conflict && (
                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={acknowledgeConflict}
                    onChange={(event) => {
                      setAcknowledgeConflict(event.currentTarget.checked);
                    }}
                  />{" "}
                  I have reviewed the conflicting source assessments and want to
                  apply this accepted name
                </label>
              )}
              <div className="field">
                <label htmlFor="reconciliation-suggestion-notes">
                  Reconciliation notes (optional)
                </label>
                <textarea
                  id="reconciliation-suggestion-notes"
                  rows={2}
                  maxLength={2000}
                  value={correctionNotes}
                  onChange={(event) => {
                    setCorrectionNotes(event.currentTarget.value);
                  }}
                />
              </div>
              <div className="actions">
                <button
                  type="button"
                  className="button--secondary"
                  disabled={busy}
                  onClick={() => {
                    setSelectedSuggestion(null);
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={
                    busy ||
                    (state.data.has_source_conflict && !acknowledgeConflict)
                  }
                >
                  {busy
                    ? "Applying correction…"
                    : "Confirm accepted-name correction"}
                </button>
              </div>
            </form>
          )}

          {mergeTarget && (
            <form
              className="notice"
              aria-label="Confirm duplicate-identity reconciliation"
              onSubmit={(event) => void submitDuplicateMerge(event)}
            >
              <h4>Confirm duplicate-identity reconciliation</h4>
              <p>
                Reconcile duplicate identity{" "}
                <strong>{state.data.identity.display_label}</strong> into
                survivor <strong>{mergeTarget.display_label}</strong>.
              </p>
              <p className="field-help">
                All Seed lots (
                {state.data.identity.collection_counts?.seed_lots ?? 0}), Plants
                ({state.data.identity.collection_counts?.plants ?? 0}), Plant
                groups (
                {state.data.identity.collection_counts?.plant_groups ?? 0}), and
                planned activities on {state.data.identity.display_label} will
                be transactionally repointed to {mergeTarget.display_label}, and{" "}
                {state.data.identity.display_label} will be retained as a merged
                historical name on the survivor.
              </p>
              {mergeTarget.has_conflicting_profile_fields && (
                <div>
                  <p>
                    <strong>Reference profile conflict:</strong> Both identities
                    have differing text in:{" "}
                    {(mergeTarget.conflicting_profile_fields ?? []).join(", ")}.
                  </p>
                  <label className="checkbox-field">
                    <input
                      type="checkbox"
                      checked={keepSurvivorProfile}
                      onChange={(event) => {
                        setKeepSurvivorProfile(event.currentTarget.checked);
                      }}
                    />{" "}
                    Keep survivor ({mergeTarget.display_label}) profile text for
                    conflicting fields
                  </label>
                </div>
              )}
              <div className="field">
                <label htmlFor="reconciliation-merge-notes">
                  Merge notes (optional)
                </label>
                <textarea
                  id="reconciliation-merge-notes"
                  rows={2}
                  maxLength={2000}
                  value={mergeNotes}
                  onChange={(event) => {
                    setMergeNotes(event.currentTarget.value);
                  }}
                />
              </div>
              <div className="actions">
                <button
                  type="button"
                  className="button--secondary"
                  disabled={busy}
                  onClick={() => {
                    setMergeTarget(null);
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={
                    busy ||
                    (mergeTarget.has_conflicting_profile_fields &&
                      !keepSurvivorProfile)
                  }
                >
                  {busy
                    ? "Merging duplicate identity…"
                    : "Confirm duplicate merge and repoint holdings"}
                </button>
              </div>
            </form>
          )}

          <div>
            {!manualOpen ? (
              <button
                type="button"
                className="button--secondary"
                disabled={busy}
                onClick={() => {
                  setSelectedSuggestion(null);
                  setMergeTarget(null);
                  setManualName(state.data.identity.scientific_name);
                  setManualCultivar(state.data.identity.cultivar_name ?? "");
                  setManualCommonName(state.data.identity.common_name ?? "");
                  setManualOpen(true);
                  setMutationError(null);
                }}
              >
                Record manual accepted-name correction
              </button>
            ) : (
              <form
                className="notice"
                aria-label="Manual accepted-name correction"
                onSubmit={(event) => void submitManualCorrection(event)}
              >
                <h4>Manual accepted-name correction</h4>
                <div className="field">
                  <FieldLabel
                    required
                    htmlFor="manual-reconcile-scientific-name"
                  >
                    Accepted scientific name
                  </FieldLabel>
                  <input
                    id="manual-reconcile-scientific-name"
                    required
                    maxLength={255}
                    disabled={busy}
                    value={manualName}
                    onChange={(event) => {
                      setManualName(event.currentTarget.value);
                    }}
                  />
                </div>
                <div className="field">
                  <label htmlFor="manual-reconcile-cultivar-name">
                    Cultivar
                  </label>
                  <input
                    id="manual-reconcile-cultivar-name"
                    maxLength={120}
                    disabled={busy}
                    value={manualCultivar}
                    onChange={(event) => {
                      setManualCultivar(event.currentTarget.value);
                    }}
                  />
                </div>
                <div className="field">
                  <label htmlFor="manual-reconcile-common-name">
                    Common name
                  </label>
                  <input
                    id="manual-reconcile-common-name"
                    maxLength={160}
                    disabled={busy}
                    value={manualCommonName}
                    onChange={(event) => {
                      setManualCommonName(event.currentTarget.value);
                    }}
                  />
                </div>
                {state.data.has_source_conflict && (
                  <label className="checkbox-field">
                    <input
                      type="checkbox"
                      checked={acknowledgeConflict}
                      onChange={(event) => {
                        setAcknowledgeConflict(event.currentTarget.checked);
                      }}
                    />{" "}
                    I have reviewed the conflicting source assessments and want
                    to apply this accepted name
                  </label>
                )}
                <div className="field">
                  <label htmlFor="manual-reconcile-notes">
                    Reconciliation notes (optional)
                  </label>
                  <textarea
                    id="manual-reconcile-notes"
                    rows={2}
                    maxLength={2000}
                    value={correctionNotes}
                    onChange={(event) => {
                      setCorrectionNotes(event.currentTarget.value);
                    }}
                  />
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={busy}
                    onClick={() => {
                      setManualOpen(false);
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={
                      busy ||
                      (state.data.has_source_conflict && !acknowledgeConflict)
                    }
                  >
                    {busy ? "Applying…" : "Confirm manual correction"}
                  </button>
                </div>
              </form>
            )}
          </div>

          {state.data.reconciliations.length > 0 && (
            <div>
              <h4>Reconciliation audit history</h4>
              <ul>
                {state.data.reconciliations.map((item) => (
                  <li key={item.id}>
                    <strong>
                      {item.kind === "duplicate_identity_merge"
                        ? "Duplicate merge"
                        : "Accepted-name correction"}
                    </strong>
                    : {item.previous_scientific_name} →{" "}
                    {item.applied_scientific_name} ({item.source_provider}) ·{" "}
                    {new Date(item.created_at).toLocaleDateString()}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
