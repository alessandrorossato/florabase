import {
  useEffect,
  useRef,
  useState,
  type RefObject,
  type SyntheticEvent,
} from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { FieldLabel } from "../components/FieldLabel";
import { BotanicalName } from "../components/ReferenceUI";
import {
  conflictExistingId,
  correctBotanicalIdentityAcceptedName,
  createBotanicalIdentitySynonym,
  deleteBotanicalIdentitySynonym,
  getBotanicalIdentityReconciliation,
  mergeDuplicateBotanicalIdentity,
  updateBotanicalIdentitySynonym,
  validationMessages,
  type AcceptedNameSuggestionResponse,
  type BotanicalIdentityResponse,
  type CollidingIdentitySummary,
  type IdentityHistoricalNameResponse,
  type IdentityReconciliationResponse,
} from "./api";

const STATUS_KIND_LABELS: Record<string, string> = {
  initial_recorded: "Original acquisition / recorded name",
  former_accepted: "Former accepted name",
  merged_duplicate: "Merged duplicate identity name",
  source_synonym: "Source synonym",
  operator_synonym: "Operator synonym",
};

const BADGE_LABELS: Record<string, { label: string; className: string }> = {
  initial_recorded: {
    label: "Original recorded",
    className: "ui-badge name-badge name-badge--original",
  },
  former_accepted: {
    label: "Former accepted",
    className: "ui-badge name-badge name-badge--historical",
  },
  merged_duplicate: {
    label: "Merged duplicate",
    className: "ui-badge name-badge name-badge--historical",
  },
  source_synonym: {
    label: "Source synonym",
    className: "ui-badge name-badge name-badge--source",
  },
  operator_synonym: {
    label: "Operator synonym",
    className: "ui-badge name-badge name-badge--operator",
  },
};

type SourceAssessment =
  IdentityReconciliationResponse["source_assessments"][number];

interface SynonymFormValues {
  scientific_name: string;
  cultivar_name: string;
  common_name: string;
  authorship: string;
  source_citation: string;
}

const EMPTY_SYNONYM_FORM: SynonymFormValues = {
  scientific_name: "",
  cultivar_name: "",
  common_name: "",
  authorship: "",
  source_citation: "",
};

interface SynonymErrorState {
  message: string;
  existingId: string | null;
}

function errorMessage(error: unknown, fallback: string): string {
  if (
    error instanceof ApiError &&
    typeof error.body === "object" &&
    error.body !== null &&
    "detail" in error.body
  ) {
    const detail = (error.body as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim() !== "") {
      return detail;
    }
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

function parseSynonymApiError(
  error: unknown,
  fallback: string,
): SynonymErrorState {
  if (error instanceof ApiError && error.status === 422) {
    return {
      message: validationMessages(error).join(" "),
      existingId: null,
    };
  }
  return {
    message: errorMessage(error, fallback),
    existingId: error instanceof ApiError ? conflictExistingId(error) : null,
  };
}

function deriveIdentitySynonyms(
  names: IdentityHistoricalNameResponse[],
  activeScientificName: string,
  activeCultivarName: string | null | undefined,
): string[] {
  const activeScientific = activeScientificName.trim().toLowerCase();
  const activeCultivar = (activeCultivarName ?? "").trim().toLowerCase();
  const seen = new Set<string>();
  const result: string[] = [];
  for (const row of names) {
    const rowScientific = row.scientific_name.trim().toLowerCase();
    const rowCultivar = (row.cultivar_name ?? "").trim().toLowerCase();
    if (rowScientific === activeScientific && rowCultivar === activeCultivar) {
      continue;
    }
    if (!seen.has(row.scientific_name)) {
      seen.add(row.scientific_name);
      result.push(row.scientific_name);
    }
  }
  return result;
}

function sourceCitationLabel(assessment: SourceAssessment): string {
  const provider = assessment.source_provider.toUpperCase();
  const text = assessment.source_version
    ? `${provider} ${assessment.source_version}`
    : provider;
  return text.slice(0, 64);
}

function prefillFromAssessment(
  assessment: SourceAssessment,
  currentScientificName: string,
): SynonymFormValues | null {
  const currentLower = currentScientificName.trim().toLowerCase();
  const matched = assessment.scientific_name?.trim() ?? "";
  if (matched && matched.toLowerCase() !== currentLower) {
    return {
      scientific_name: matched,
      cultivar_name: "",
      common_name: "",
      authorship: assessment.authorship?.trim() ?? "",
      source_citation: sourceCitationLabel(assessment),
    };
  }
  const accepted = assessment.accepted_scientific_name?.trim() ?? "";
  if (accepted && accepted.toLowerCase() !== currentLower) {
    return {
      scientific_name: accepted,
      cultivar_name: "",
      common_name: "",
      authorship: assessment.accepted_authorship?.trim() ?? "",
      source_citation: sourceCitationLabel(assessment),
    };
  }
  return null;
}

function formatDateLabel(value: string | null | undefined): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

function OperatorSynonymForm({
  mode,
  idPrefix,
  values,
  error,
  busy,
  scientificInputRef,
  onChange,
  onSubmit,
  onCancel,
}: {
  mode: "add" | "edit";
  idPrefix: string;
  values: SynonymFormValues;
  error: SynonymErrorState | null;
  busy: boolean;
  scientificInputRef: RefObject<HTMLInputElement | null>;
  onChange: (next: SynonymFormValues) => void;
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void;
  onCancel: () => void;
}) {
  const title =
    mode === "add" ? "Add operator synonym" : "Edit operator synonym";
  const submitLabel =
    mode === "add"
      ? busy
        ? "Saving synonym…"
        : "Save operator synonym"
      : busy
        ? "Updating synonym…"
        : "Save synonym changes";

  return (
    <form
      className="notice synonym-editor-form"
      aria-label={title}
      noValidate
      onKeyDown={(event) => {
        if (event.key === "Escape" && !busy) {
          event.stopPropagation();
          onCancel();
        }
      }}
      onSubmit={onSubmit}
    >
      <h5>{title}</h5>
      {error && (
        <div
          id={`${idPrefix}-error`}
          className="notice notice--error"
          role="alert"
        >
          <p>{error.message}</p>
          {error.existingId && (
            <p>
              <a href={`#/identities/${error.existingId}?tab=taxonomy`}>
                Inspect colliding botanical identity
              </a>
            </p>
          )}
        </div>
      )}
      <div className="field">
        <FieldLabel required htmlFor={`${idPrefix}-scientific-name`}>
          Synonym scientific name
        </FieldLabel>
        <input
          ref={scientificInputRef}
          id={`${idPrefix}-scientific-name`}
          required
          maxLength={255}
          disabled={busy}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${idPrefix}-error` : undefined}
          value={values.scientific_name}
          onChange={(event) => {
            onChange({ ...values, scientific_name: event.currentTarget.value });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor={`${idPrefix}-cultivar-name`}>Cultivar (optional)</label>
        <input
          id={`${idPrefix}-cultivar-name`}
          maxLength={120}
          disabled={busy}
          value={values.cultivar_name}
          onChange={(event) => {
            onChange({ ...values, cultivar_name: event.currentTarget.value });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor={`${idPrefix}-common-name`}>
          Common name (optional)
        </label>
        <input
          id={`${idPrefix}-common-name`}
          maxLength={160}
          disabled={busy}
          value={values.common_name}
          onChange={(event) => {
            onChange({ ...values, common_name: event.currentTarget.value });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor={`${idPrefix}-authorship`}>
          Taxonomic authorship (optional)
        </label>
        <input
          id={`${idPrefix}-authorship`}
          maxLength={255}
          placeholder="e.g. (F.Rchb.) Friedrich & G.D.Rowley"
          disabled={busy}
          value={values.authorship}
          onChange={(event) => {
            onChange({ ...values, authorship: event.currentTarget.value });
          }}
        />
      </div>
      <div className="field">
        <label htmlFor={`${idPrefix}-source-citation`}>
          Source citation or reference (optional)
        </label>
        <input
          id={`${idPrefix}-source-citation`}
          maxLength={64}
          placeholder="e.g. Hortus Third or Kew WCVP"
          disabled={busy}
          value={values.source_citation}
          onChange={(event) => {
            onChange({ ...values, source_citation: event.currentTarget.value });
          }}
        />
      </div>
      <div className="actions">
        <button
          type="button"
          className="button--secondary"
          disabled={busy}
          onClick={onCancel}
        >
          Cancel
        </button>
        <button type="submit" disabled={busy}>
          {submitLabel}
        </button>
      </div>
    </form>
  );
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

  const [addSynonymOpen, setAddSynonymOpen] = useState(false);
  const [editingSynonymId, setEditingSynonymId] = useState<string | null>(null);
  const [confirmRemoveSynonymId, setConfirmRemoveSynonymId] = useState<
    string | null
  >(null);
  const [synonymForm, setSynonymForm] =
    useState<SynonymFormValues>(EMPTY_SYNONYM_FORM);
  const [synonymError, setSynonymError] = useState<SynonymErrorState | null>(
    null,
  );
  const synonymInputRef = useRef<HTMLInputElement>(null);
  const addSynonymTriggerRef = useRef<HTMLButtonElement>(null);
  const editButtonRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const removeButtonRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const cancelRemoveBtnRef = useRef<HTMLButtonElement>(null);

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
        setState((previous) => {
          if (
            previous.status === "ready" &&
            previous.data.identity.id === identity.id
          ) {
            return previous;
          }
          return {
            status: "error",
            message:
              "Could not load accepted-name reconciliation evidence. Retry to inspect suggestions.",
          };
        });
      });
    return () => {
      controller.abort();
    };
  }, [identity.id, identity.updated_at, attempt, auth]);

  useEffect(() => {
    if (addSynonymOpen || editingSynonymId) {
      synonymInputRef.current?.focus();
    }
  }, [addSynonymOpen, editingSynonymId]);

  useEffect(() => {
    if (confirmRemoveSynonymId) {
      cancelRemoveBtnRef.current?.focus();
    }
  }, [confirmRemoveSynonymId]);

  function restoreFocus(target: "add" | { edit: string } | { remove: string }) {
    requestAnimationFrame(() => {
      if (target === "add") {
        addSynonymTriggerRef.current?.focus();
      } else if ("edit" in target) {
        editButtonRefs.current.get(target.edit)?.focus();
      } else {
        removeButtonRefs.current.get(target.remove)?.focus();
      }
    });
  }

  function resetSynonymWorkflow(
    focusTarget?: "add" | { edit: string } | { remove: string },
  ) {
    setAddSynonymOpen(false);
    setEditingSynonymId(null);
    setConfirmRemoveSynonymId(null);
    setSynonymForm(EMPTY_SYNONYM_FORM);
    setSynonymError(null);
    if (focusTarget) {
      restoreFocus(focusTarget);
    }
  }

  function openAddSynonym(prefill: SynonymFormValues = EMPTY_SYNONYM_FORM) {
    setSelectedSuggestion(null);
    setManualOpen(false);
    setMergeTarget(null);
    setEditingSynonymId(null);
    setConfirmRemoveSynonymId(null);
    setMutationError(null);
    setSynonymError(null);
    setSynonymForm(prefill);
    setAddSynonymOpen(true);
  }

  function openEditSynonym(item: IdentityHistoricalNameResponse) {
    setSelectedSuggestion(null);
    setManualOpen(false);
    setMergeTarget(null);
    setAddSynonymOpen(false);
    setConfirmRemoveSynonymId(null);
    setMutationError(null);
    setSynonymError(null);
    setSynonymForm({
      scientific_name: item.scientific_name,
      cultivar_name: item.cultivar_name ?? "",
      common_name: item.common_name ?? "",
      authorship: item.authorship ?? "",
      source_citation: item.source_version ?? "",
    });
    setEditingSynonymId(item.id);
  }

  async function syncParentDirectory(
    currentIdentity: BotanicalIdentityResponse,
    nextFormerNames: IdentityHistoricalNameResponse[],
  ) {
    try {
      await onIdentityUpdated({
        ...currentIdentity,
        synonyms: deriveIdentitySynonyms(
          nextFormerNames,
          currentIdentity.scientific_name,
          currentIdentity.cultivar_name,
        ),
      });
    } catch {
      setMutationError(
        "Operator synonym change saved, but the botanical identity directory could not be refreshed.",
      );
    }
  }

  async function submitAddSynonym(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || state.status !== "ready") return;
    if (synonymForm.scientific_name.trim() === "") {
      setSynonymError({
        message: "Synonym scientific name cannot be blank.",
        existingId: null,
      });
      synonymInputRef.current?.focus();
      return;
    }
    setBusy(true);
    setSynonymError(null);
    setMutationError(null);
    setNotice(null);
    let created: IdentityHistoricalNameResponse;
    try {
      created = await createBotanicalIdentitySynonym(
        identity.id,
        {
          scientific_name: synonymForm.scientific_name.trim(),
          cultivar_name: synonymForm.cultivar_name.trim() || null,
          common_name: synonymForm.common_name.trim() || null,
          authorship: synonymForm.authorship.trim() || null,
          source_citation: synonymForm.source_citation.trim() || null,
        },
        csrfToken,
      );
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
        return;
      }
      setSynonymError(
        parseSynonymApiError(
          error,
          "Florabase could not save this operator synonym.",
        ),
      );
      synonymInputRef.current?.focus();
      setBusy(false);
      return;
    }

    const nextFormerNames = [...state.data.former_names, created];
    setState({
      status: "ready",
      data: { ...state.data, former_names: nextFormerNames },
    });
    resetSynonymWorkflow("add");
    setNotice(`Operator synonym ${created.display_label} added.`);
    await syncParentDirectory(state.data.identity, nextFormerNames);
    setBusy(false);
  }

  async function submitEditSynonym(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !editingSynonymId || state.status !== "ready") return;
    if (synonymForm.scientific_name.trim() === "") {
      setSynonymError({
        message: "Synonym scientific name cannot be blank.",
        existingId: null,
      });
      synonymInputRef.current?.focus();
      return;
    }
    setBusy(true);
    setSynonymError(null);
    setMutationError(null);
    setNotice(null);
    const targetId = editingSynonymId;
    let updated: IdentityHistoricalNameResponse;
    try {
      updated = await updateBotanicalIdentitySynonym(
        identity.id,
        targetId,
        {
          scientific_name: synonymForm.scientific_name.trim(),
          cultivar_name: synonymForm.cultivar_name.trim() || null,
          common_name: synonymForm.common_name.trim() || null,
          authorship: synonymForm.authorship.trim() || null,
          source_citation: synonymForm.source_citation.trim() || null,
        },
        csrfToken,
      );
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
        return;
      }
      setSynonymError(
        parseSynonymApiError(
          error,
          "Florabase could not update this operator synonym.",
        ),
      );
      synonymInputRef.current?.focus();
      setBusy(false);
      return;
    }

    const nextFormerNames = state.data.former_names.map((item) =>
      item.id === targetId ? updated : item,
    );
    setState({
      status: "ready",
      data: { ...state.data, former_names: nextFormerNames },
    });
    resetSynonymWorkflow({ edit: targetId });
    setNotice(`Operator synonym ${updated.display_label} updated.`);
    await syncParentDirectory(state.data.identity, nextFormerNames);
    setBusy(false);
  }

  async function confirmRemoveSynonym(item: IdentityHistoricalNameResponse) {
    if (busy || state.status !== "ready") return;
    setBusy(true);
    setMutationError(null);
    setSynonymError(null);
    setNotice(null);
    try {
      await deleteBotanicalIdentitySynonym(identity.id, item.id, csrfToken);
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
        return;
      }
      setMutationError(
        errorMessage(
          error,
          "Florabase could not remove this operator synonym.",
        ),
      );
      setBusy(false);
      return;
    }

    const nextFormerNames = state.data.former_names.filter(
      (entry) => entry.id !== item.id,
    );
    setState({
      status: "ready",
      data: { ...state.data, former_names: nextFormerNames },
    });
    setConfirmRemoveSynonymId(null);
    setNotice(`Operator synonym ${item.display_label} removed.`);
    restoreFocus("add");
    await syncParentDirectory(state.data.identity, nextFormerNames);
    setBusy(false);
  }

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
      resetSynonymWorkflow();
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
      resetSynonymWorkflow();
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
      resetSynonymWorkflow();
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

  const isMerged = Boolean(
    state.status === "ready"
      ? state.data.identity.merged_into_id
      : identity.merged_into_id,
  );
  const mergedSurvivorId =
    state.status === "ready"
      ? state.data.identity.merged_into_id
      : identity.merged_into_id;

  const operatorSynonyms =
    state.status === "ready"
      ? state.data.former_names.filter(
          (item) => item.status_kind === "operator_synonym",
        )
      : [];
  const sourceSynonyms =
    state.status === "ready"
      ? state.data.former_names.filter(
          (item) => item.status_kind === "source_synonym",
        )
      : [];
  const historicalNames =
    state.status === "ready"
      ? state.data.former_names.filter(
          (item) =>
            item.status_kind === "initial_recorded" ||
            item.status_kind === "former_accepted" ||
            item.status_kind === "merged_duplicate",
        )
      : [];

  return (
    <section
      className="taxonomy-panel identity-reconciliation-panel"
      aria-label="Accepted-name reconciliation"
    >
      <h3>Accepted-name reconciliation</h3>
      <p>
        Manage operator synonyms, inspect source-provided names, review version
        or cross-source conflicts, and explicitly confirm accepted-name
        corrections without losing original acquisition provenance.
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
          {isMerged && mergedSurvivorId && (
            <div className="notice" role="status">
              <p>
                This botanical identity is retired after duplicate
                reconciliation. Operator synonym and accepted-name edits are
                locked; manage names on the{" "}
                <a href={`#/identities/${mergedSurvivorId}?tab=taxonomy`}>
                  survivor botanical identity
                </a>
                .
              </p>
            </div>
          )}

          <div className="reconciliation-provenance">
            <h4>Name provenance</h4>
            <div className="name-classification-grid">
              <div className="name-classification-row">
                <span className="ui-badge name-badge name-badge--accepted">
                  Accepted name
                </span>
                <div>
                  <p>
                    <strong>Current active name:</strong>{" "}
                    <BotanicalName
                      label={state.data.identity.display_label}
                      scientificName={state.data.identity.scientific_name}
                    />
                  </p>
                  {state.data.identity.common_name && (
                    <p className="field-help">
                      Common name: {state.data.identity.common_name}
                    </p>
                  )}
                </div>
              </div>

              <div className="name-classification-row">
                <span className={BADGE_LABELS.initial_recorded.className}>
                  {BADGE_LABELS.initial_recorded.label}
                </span>
                <div>
                  <p>
                    <strong>Original recorded name:</strong>{" "}
                    <BotanicalName
                      label={state.data.original_display_label}
                      scientificName={state.data.original_scientific_name}
                    />
                  </p>
                  <p className="field-help">
                    Immutable acquisition provenance; cannot be overwritten or
                    removed.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <section
            className="operator-synonyms-section"
            aria-label="Operator-managed synonyms"
          >
            <div className="synonym-section-header">
              <h4>Operator-managed synonyms ({operatorSynonyms.length})</h4>
              {!isMerged && !addSynonymOpen && !editingSynonymId && (
                <button
                  ref={addSynonymTriggerRef}
                  type="button"
                  className="button--secondary"
                  disabled={busy}
                  onClick={() => {
                    openAddSynonym();
                  }}
                >
                  Add operator synonym
                </button>
              )}
            </div>
            <p className="field-help">
              Operator-managed synonyms improve lookup and document legacy or
              alternative names without replacing the current accepted name or
              creating duplicate identities.
            </p>

            {addSynonymOpen && !isMerged && (
              <OperatorSynonymForm
                mode="add"
                idPrefix="add-synonym"
                values={synonymForm}
                error={synonymError}
                busy={busy}
                scientificInputRef={synonymInputRef}
                onChange={setSynonymForm}
                onSubmit={(event) => void submitAddSynonym(event)}
                onCancel={() => {
                  resetSynonymWorkflow("add");
                }}
              />
            )}

            {operatorSynonyms.length === 0 ? (
              <p className="field-help" role="status">
                No operator-managed synonyms recorded.
              </p>
            ) : (
              <ul className="synonym-ledger-list">
                {operatorSynonyms.map((item) => {
                  const effectiveDate = formatDateLabel(item.effective_from);
                  return (
                    <li key={item.id} className="synonym-ledger-item">
                      {editingSynonymId === item.id ? (
                        <OperatorSynonymForm
                          mode="edit"
                          idPrefix={`edit-synonym-${item.id}`}
                          values={synonymForm}
                          error={synonymError}
                          busy={busy}
                          scientificInputRef={synonymInputRef}
                          onChange={setSynonymForm}
                          onSubmit={(event) => void submitEditSynonym(event)}
                          onCancel={() => {
                            resetSynonymWorkflow({ edit: item.id });
                          }}
                        />
                      ) : (
                        <>
                          <div className="synonym-item-main">
                            <span
                              className={
                                BADGE_LABELS.operator_synonym.className
                              }
                            >
                              {BADGE_LABELS.operator_synonym.label}
                            </span>{" "}
                            <BotanicalName
                              label={item.display_label}
                              scientificName={item.scientific_name}
                            />
                            {item.authorship ? ` ${item.authorship}` : ""}
                            {item.common_name ? ` · ${item.common_name}` : ""}
                            <span className="synonym-item-meta field-help">
                              {item.source_version
                                ? ` · Source: ${item.source_version}`
                                : " · Operator-entered"}
                              {effectiveDate ? ` · Added ${effectiveDate}` : ""}
                            </span>
                          </div>
                          {!isMerged && confirmRemoveSynonymId !== item.id && (
                            <div className="synonym-item-actions actions">
                              <button
                                ref={(node) => {
                                  if (node) {
                                    editButtonRefs.current.set(item.id, node);
                                  } else {
                                    editButtonRefs.current.delete(item.id);
                                  }
                                }}
                                type="button"
                                className="button--secondary"
                                disabled={busy}
                                aria-label={`Edit synonym ${item.display_label}`}
                                onClick={() => {
                                  openEditSynonym(item);
                                }}
                              >
                                Edit
                              </button>
                              <button
                                ref={(node) => {
                                  if (node) {
                                    removeButtonRefs.current.set(item.id, node);
                                  } else {
                                    removeButtonRefs.current.delete(item.id);
                                  }
                                }}
                                type="button"
                                className="button--secondary"
                                disabled={busy}
                                aria-label={`Remove synonym ${item.display_label}`}
                                onClick={() => {
                                  setAddSynonymOpen(false);
                                  setEditingSynonymId(null);
                                  setSynonymError(null);
                                  setMutationError(null);
                                  setConfirmRemoveSynonymId(item.id);
                                }}
                              >
                                Remove
                              </button>
                            </div>
                          )}
                          {!isMerged && confirmRemoveSynonymId === item.id && (
                            <div
                              className="notice notice--warning"
                              role="alertdialog"
                              aria-label={`Confirm removal of ${item.display_label}`}
                              aria-describedby={`remove-synonym-desc-${item.id}`}
                              onKeyDown={(event) => {
                                if (event.key === "Escape" && !busy) {
                                  event.stopPropagation();
                                  setConfirmRemoveSynonymId(null);
                                  restoreFocus({ remove: item.id });
                                }
                              }}
                            >
                              <p id={`remove-synonym-desc-${item.id}`}>
                                Remove operator synonym{" "}
                                <strong>{item.display_label}</strong>? The
                                current accepted name and immutable historical
                                provenance remain intact.
                              </p>
                              <div className="actions">
                                <button
                                  ref={cancelRemoveBtnRef}
                                  type="button"
                                  className="button--secondary"
                                  disabled={busy}
                                  onClick={() => {
                                    setConfirmRemoveSynonymId(null);
                                    restoreFocus({ remove: item.id });
                                  }}
                                >
                                  Cancel
                                </button>
                                <button
                                  type="button"
                                  className="button--danger"
                                  disabled={busy}
                                  onClick={() =>
                                    void confirmRemoveSynonym(item)
                                  }
                                >
                                  {busy ? "Removing…" : "Confirm removal"}
                                </button>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section
            className="historical-ledger-section"
            aria-label="Historical name ledger"
          >
            <h4>Historical name ledger ({historicalNames.length})</h4>
            {historicalNames.length > 0 ? (
              <>
                <ul className="synonym-ledger-list">
                  {historicalNames.map((item) => {
                    const badge = BADGE_LABELS[item.status_kind] ?? {
                      label: item.status_kind,
                      className: "ui-badge name-badge name-badge--historical",
                    };
                    const effectiveDate = formatDateLabel(item.effective_from);
                    const supersededDate = formatDateLabel(item.superseded_at);
                    return (
                      <li key={item.id} className="synonym-ledger-item">
                        <div className="synonym-item-main">
                          <span className={badge.className}>{badge.label}</span>{" "}
                          <BotanicalName
                            label={item.display_label}
                            scientificName={item.scientific_name}
                          />
                          {item.authorship ? ` ${item.authorship}` : ""} ·{" "}
                          {STATUS_KIND_LABELS[item.status_kind] ??
                            item.status_kind}{" "}
                          · Source: {item.source_provider}
                          {item.source_version
                            ? ` (${item.source_version})`
                            : ""}
                          {effectiveDate ? ` · Recorded ${effectiveDate}` : ""}
                          {supersededDate
                            ? ` · Superseded ${supersededDate}`
                            : ""}
                          {item.origin_identity_id && (
                            <>
                              {" · "}
                              <a
                                href={`#/identities/${item.origin_identity_id}`}
                              >
                                Merged record
                              </a>
                            </>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
                <p className="field-help">
                  Historical and original recorded names are immutable
                  provenance evidence and cannot be edited or deleted.
                </p>
              </>
            ) : (
              <p className="field-help">
                No superseded names recorded yet; this identity retains its
                initial recorded name.
              </p>
            )}
          </section>

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

          {(state.data.source_assessments.length > 0 ||
            sourceSynonyms.length > 0) && (
            <section aria-label="Source-provided names and assessments">
              <h4>Source-provided names &amp; assessments</h4>
              <p className="field-help">
                Provider classifications are read-only reference evidence.
                Prefill an operator synonym if you want to curate one locally
                for search.
              </p>
              <ul className="synonym-ledger-list">
                {state.data.source_assessments.map((assessment, idx) => {
                  const candidate = prefillFromAssessment(
                    assessment,
                    state.data.identity.scientific_name,
                  );
                  return (
                    <li
                      key={`${assessment.source_provider}-${assessment.source_version ?? "default"}-${String(idx)}`}
                      className="synonym-ledger-item"
                    >
                      <div className="synonym-item-main">
                        <span className="ui-badge name-badge name-badge--source">
                          Source reference
                        </span>{" "}
                        <strong>{assessment.source_label}</strong>
                        {assessment.source_version
                          ? ` (${assessment.source_version})`
                          : ""}
                        : {assessment.status ?? "Unresolved"}
                        {assessment.scientific_name
                          ? ` · ${assessment.scientific_name}`
                          : ""}
                        {assessment.authorship
                          ? ` ${assessment.authorship}`
                          : ""}
                        {assessment.accepted_scientific_name &&
                        assessment.accepted_scientific_name.toLowerCase() !==
                          (assessment.scientific_name ?? "").toLowerCase()
                          ? ` → Accepted: ${assessment.accepted_scientific_name}`
                          : ""}
                        {assessment.stale ? " · (Stale link)" : ""}
                      </div>
                      {!isMerged && candidate && (
                        <div className="synonym-item-actions actions">
                          <button
                            type="button"
                            className="button--secondary"
                            disabled={busy}
                            onClick={() => {
                              openAddSynonym(candidate);
                            }}
                          >
                            Add as operator synonym
                          </button>
                        </div>
                      )}
                    </li>
                  );
                })}
                {sourceSynonyms.map((item) => (
                  <li key={item.id} className="synonym-ledger-item">
                    <div className="synonym-item-main">
                      <span className={BADGE_LABELS.source_synonym.className}>
                        {BADGE_LABELS.source_synonym.label}
                      </span>{" "}
                      <BotanicalName
                        label={item.display_label}
                        scientificName={item.scientific_name}
                      />
                      {item.authorship ? ` ${item.authorship}` : ""} · Source:{" "}
                      {item.source_provider}
                      {item.source_version ? ` (${item.source_version})` : ""}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
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
                          , Vegetative lots:{" "}
                          {
                            suggestion.colliding_identity.collection_counts
                              .vegetative_lots
                          }
                          , Rooting attempts:{" "}
                          {
                            suggestion.colliding_identity.collection_counts
                              .propagation_attempts
                          }
                          ). In-place renaming is refused so identities are
                          never merged silently.
                        </p>
                        {!isMerged && (
                          <button
                            type="button"
                            className="button--secondary"
                            disabled={busy}
                            onClick={() => {
                              setSelectedSuggestion(null);
                              setManualOpen(false);
                              resetSynonymWorkflow();
                              setMergeTarget(
                                suggestion.colliding_identity ?? null,
                              );
                              setKeepSurvivorProfile(false);
                              setMutationError(null);
                            }}
                          >
                            Review duplicate-identity reconciliation
                          </button>
                        )}
                      </div>
                    ) : (
                      !isMerged && (
                        <button
                          type="button"
                          className="button--secondary"
                          disabled={busy || suggestion.stale}
                          onClick={() => {
                            setMergeTarget(null);
                            setManualOpen(false);
                            resetSynonymWorkflow();
                            setSelectedSuggestion(suggestion);
                            setAcknowledgeConflict(false);
                            setMutationError(null);
                          }}
                        >
                          Review accepted-name correction
                        </button>
                      )
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selectedSuggestion && !isMerged && (
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

          {mergeTarget && !isMerged && (
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
                {state.data.identity.collection_counts?.plant_groups ?? 0}),
                vegetative lots (
                {state.data.identity.collection_counts?.vegetative_lots ?? 0}),
                and planned activities on {state.data.identity.display_label}{" "}
                will be transactionally repointed to {mergeTarget.display_label}
                , and {state.data.identity.display_label} will be retained as a
                merged historical name on the survivor.
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

          {!isMerged && (
            <div>
              {!manualOpen ? (
                <button
                  type="button"
                  className="button--secondary"
                  disabled={busy}
                  onClick={() => {
                    setSelectedSuggestion(null);
                    setMergeTarget(null);
                    resetSynonymWorkflow();
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
                      I have reviewed the conflicting source assessments and
                      want to apply this accepted name
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
          )}

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
