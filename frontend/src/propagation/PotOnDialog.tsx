import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type RefObject,
  type SyntheticEvent,
} from "react";

import {
  activeCsrfToken,
  ApiError,
  isExpectedAuthCancellation,
} from "../auth/api";
import { useAuth } from "../auth/context";
import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import { IdentityCreateDialog } from "../botanical-identities/IdentityCreateDialog";
import { FieldHelp } from "../components/ContextualHelp";
import { FieldLabel } from "../components/FieldLabel";
import { useRecordName } from "../components/recordPresentation";
import { TaskDialog } from "../components/TaskDialog";
import {
  listLocations,
  locationsForScope,
  type LocationResponse,
} from "../locations/api";
import {
  getPlantGroup,
  type PlantGroupResponse,
  type PlantResponse,
} from "../plants/api";
import { invalidDateControls } from "../seed-lots/dateControls";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import {
  createPlantGroupFromSowing,
  getSowing,
  type PartialDate,
  type SowingLifecycle,
  type SowingResponse,
} from "../sowings/api";
import {
  defaultCounterPadding,
  expandLabelPattern,
  extractPlantsFromGroup,
  MAX_BATCH_COUNT,
  MAX_LABEL_LENGTH,
  normalizeSingleLineLabel,
  potOnSowing,
  previewLabelSample,
  propagationErrorDetail,
} from "./api";

export type PotOnSource =
  | { kind: "sowing"; sowing: SowingResponse }
  | { kind: "group"; group: PlantGroupResponse };

type PotOnMode = "plants" | "group";
type Step = "form" | "preview" | "success";
type WritableSowingLifecycle = Exclude<SowingLifecycle, "reversed">;

const sowingLifecycleOptions: {
  value: WritableSowingLifecycle;
  label: string;
  display: string;
}[] = [
  { value: "active", label: "Keep active", display: "Active" },
  { value: "completed", label: "Complete Sowing", display: "Completed" },
  { value: "failed", label: "Mark failed", display: "Failed" },
  { value: "abandoned", label: "Abandon Sowing", display: "Abandoned" },
];

function todayPartialDate(): PartialDate {
  const now = new Date();
  return {
    precision: "day",
    year: now.getFullYear(),
    month: now.getMonth() + 1,
    day: now.getDate(),
  };
}

function defaultSowingLifecycle(
  sowing: SowingResponse,
  count: number,
): WritableSowingLifecycle {
  if (sowing.germinated_count !== null && count >= sowing.germinated_count) {
    return "completed";
  }
  return "active";
}

function initialCountFor(source: PotOnSource): number {
  if (source.kind === "sowing") {
    const germinated = source.sowing.germinated_count;
    if (germinated !== null && germinated >= 1) {
      return Math.min(germinated, MAX_BATCH_COUNT);
    }
    return 1;
  }
  const qty = source.group.quantity;
  if (qty && !qty.is_approximate && qty.value >= 1) {
    return Math.min(qty.value, 1);
  }
  return 1;
}

function defaultPatternFor(source: PotOnSource): string {
  const label =
    source.kind === "sowing" ? source.sowing.label : source.group.label;
  return label ? `${label}-{n}` : "";
}

function formatPartialDate(value: PartialDate | null): string {
  if (!value) return "Not recorded";
  if (value.precision === "year") return String(value.year);
  if (value.precision === "month") {
    return `${String(value.year)}-${String(value.month ?? 1).padStart(2, "0")}`;
  }
  return `${String(value.year)}-${String(value.month ?? 1).padStart(2, "0")}-${String(value.day ?? 1).padStart(2, "0")}`;
}

function conflictMessage(
  sourceKind: PotOnSource["kind"],
  code: string | undefined,
  fallback: string | undefined,
): { message: string; stale: boolean } {
  if (code === "stale_preview") {
    return {
      stale: true,
      message:
        sourceKind === "sowing"
          ? "This Sowing changed before confirmation. Refresh the Sowing to review current details."
          : "This Plant group changed before confirmation. Refresh the Plant group to review current details.",
    };
  }
  if (code === "sowing_not_active") {
    return {
      stale: true,
      message:
        "This Sowing is no longer active and cannot be potted on in a batch.",
    };
  }
  if (code === "reversed_sowing_is_historical") {
    return {
      stale: true,
      message: "This Sowing has been reversed and cannot create descendants.",
    };
  }
  if (code === "plant_group_not_active") {
    return {
      stale: true,
      message:
        "This Plant group is no longer active and cannot be split into plants.",
    };
  }
  if (code === "plant_group_quantity_exceeded") {
    return {
      stale: true,
      message:
        "The requested count exceeds the exact quantity available in this Plant group.",
    };
  }
  if (code === "location_scope_not_supported") {
    return {
      stale: false,
      message:
        "The selected Location does not support Plants. Choose a plant-compatible Location.",
    };
  }
  if (code === "propagation_concurrency_conflict") {
    return {
      stale: true,
      message: "Concurrent changes conflicted. Refresh and try again.",
    };
  }
  return {
    stale: false,
    message:
      fallback ??
      (sourceKind === "sowing"
        ? "This Sowing changed before confirmation. Review its current state and try again."
        : "This Plant group changed before confirmation. Review its current state and try again."),
  };
}

export function PotOnDialog({
  source: initialSource,
  identities: providedIdentities,
  locations: providedLocations,
  returnFocusTo,
  fallbackFocusTo,
  onClose,
  onSowingUpdated,
  onGroupUpdated,
}: {
  source: PotOnSource;
  identities?: BotanicalIdentityResponse[];
  locations?: LocationResponse[];
  returnFocusTo?: RefObject<HTMLElement | null>;
  fallbackFocusTo?: RefObject<HTMLElement | null>;
  onClose: () => void;
  onSowingUpdated?: (sowing: SowingResponse) => void;
  onGroupUpdated?: (group: PlantGroupResponse, plants: PlantResponse[]) => void;
}) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const recordName = useRecordName();
  const titleId = useId();
  const countId = useId();
  const patternId = useId();
  const startId = useId();
  const paddingId = useId();
  const groupLabelId = useId();
  const notesId = useId();
  const countHelpId = useId();
  const patternHelpId = useId();
  const lifecycleHelpId = useId();

  const [source, setSource] = useState<PotOnSource>(initialSource);
  const [fetchedReferences, setFetchedReferences] = useState<
    | { status: "loading" }
    | { status: "error" }
    | {
        status: "ready";
        identities: BotanicalIdentityResponse[];
        locations: LocationResponse[];
      }
  >({ status: "loading" });
  // Identities created from the picker here (UX-ENTRY-002) join whichever list is in use.
  const [createdIdentities, setCreatedIdentities] = useState<
    BotanicalIdentityResponse[]
  >([]);
  const [identityDraft, setIdentityDraft] = useState<string | null>(null);
  const references = useMemo(() => {
    const base =
      providedIdentities && providedLocations
        ? {
            status: "ready" as const,
            identities: providedIdentities,
            locations: providedLocations,
          }
        : fetchedReferences;
    if (base.status !== "ready" || createdIdentities.length === 0) return base;
    const created = new Set(createdIdentities.map((item) => item.id));
    return {
      ...base,
      identities: [
        ...base.identities.filter((item) => !created.has(item.id)),
        ...createdIdentities,
      ],
    };
  }, [
    fetchedReferences,
    providedIdentities,
    providedLocations,
    createdIdentities,
  ]);
  const [refAttempt, setRefAttempt] = useState(0);

  const [mode, setMode] = useState<PotOnMode>("plants");
  const [countInput, setCountInput] = useState(() =>
    String(initialCountFor(initialSource)),
  );
  const [labelPattern, setLabelPattern] = useState(() =>
    defaultPatternFor(initialSource),
  );
  const [groupLabel, setGroupLabel] = useState(() =>
    initialSource.kind === "sowing" ? (initialSource.sowing.label ?? "") : "",
  );
  const [counterStartInput, setCounterStartInput] = useState("1");
  const [counterPaddingInput, setCounterPaddingInput] = useState("");
  const [identityId, setIdentityId] = useState(() =>
    initialSource.kind === "sowing"
      ? initialSource.sowing.seed_lot.botanical_identity_id
      : initialSource.group.botanical_identity_id,
  );
  const [locationId, setLocationId] = useState(() => {
    const rawLocation =
      initialSource.kind === "sowing"
        ? (initialSource.sowing.location_id ?? "")
        : (initialSource.group.location_id ?? "");
    if (!rawLocation || !providedLocations) return rawLocation;
    const valid = locationsForScope(providedLocations, "plants").some(
      (item) => item.id === rawLocation,
    );
    return valid ? rawLocation : "";
  });
  const [entryDate, setEntryDate] = useState<PartialDate | null>(() =>
    todayPartialDate(),
  );
  const [notes, setNotes] = useState("");
  const [resultingLifecycle, setResultingLifecycle] =
    useState<WritableSowingLifecycle>(() =>
      initialSource.kind === "sowing"
        ? defaultSowingLifecycle(
            initialSource.sowing,
            initialCountFor(initialSource),
          )
        : "active",
    );
  const [lifecycleManuallyChosen, setLifecycleManuallyChosen] = useState(false);

  const [step, setStep] = useState<Step>("form");
  const [pending, setPending] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [staleConflict, setStaleConflict] = useState(false);
  const [result, setResult] = useState<
    | { kind: "plants"; plants: PlantResponse[]; summary: string }
    | { kind: "group"; group: PlantGroupResponse; summary: string }
    | null
  >(null);
  const alertRef = useRef<HTMLDivElement>(null);
  const successRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (providedIdentities && providedLocations) {
      return;
    }
    if (!authorized) return;
    const controller = new AbortController();
    void Promise.all([
      providedIdentities
        ? Promise.resolve(providedIdentities)
        : listBotanicalIdentities(capability, controller.signal),
      providedLocations
        ? Promise.resolve(providedLocations)
        : listLocations(capability, controller.signal),
    ])
      .then(([identities, locations]) => {
        if (controller.signal.aborted) return;
        setFetchedReferences({ status: "ready", identities, locations });
        setLocationId((current) => {
          if (!current) return "";
          const supported = locationsForScope(locations, "plants").some(
            (item) => item.id === current,
          );
          return supported ? current : "";
        });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error)) {
          return;
        }
        if (error instanceof ApiError && error.status === 401) {
          sessionExpired();
        } else {
          setFetchedReferences({ status: "error" });
        }
      });
    return () => {
      controller.abort();
    };
  }, [
    authorized,
    capability,
    providedIdentities,
    providedLocations,
    refAttempt,
    sessionExpired,
  ]);

  const exactGroupQuantity =
    source.kind === "group" &&
    source.group.quantity &&
    !source.group.quantity.is_approximate
      ? source.group.quantity.value
      : null;

  const approximateGroupQuantity =
    source.kind === "group" && source.group.quantity?.is_approximate
      ? source.group.quantity.value
      : null;

  const maxCount =
    exactGroupQuantity !== null
      ? Math.min(exactGroupQuantity, MAX_BATCH_COUNT)
      : MAX_BATCH_COUNT;

  const parsedCount = /^\d+$/.test(countInput.trim())
    ? Number(countInput.trim())
    : NaN;
  const parsedStart = /^\d+$/.test(counterStartInput.trim())
    ? Number(counterStartInput.trim())
    : NaN;
  const parsedPadding =
    counterPaddingInput.trim() === ""
      ? null
      : /^\d+$/.test(counterPaddingInput.trim())
        ? Number(counterPaddingInput.trim())
        : NaN;

  const autoPadding =
    Number.isInteger(parsedCount) &&
    parsedCount >= 1 &&
    Number.isInteger(parsedStart) &&
    parsedStart >= 0
      ? defaultCounterPadding(parsedCount, parsedStart)
      : 1;

  const labelExpansion = useMemo(() => {
    if (source.kind === "sowing" && mode === "group") {
      return { labels: [], duplicateWarning: false };
    }
    if (
      !Number.isInteger(parsedCount) ||
      parsedCount < 1 ||
      parsedCount > MAX_BATCH_COUNT ||
      !Number.isInteger(parsedStart) ||
      parsedStart < 0 ||
      (parsedPadding !== null &&
        (!Number.isInteger(parsedPadding) || parsedPadding < 0))
    ) {
      return { labels: [], duplicateWarning: false };
    }
    return expandLabelPattern(
      labelPattern,
      parsedCount,
      parsedStart,
      parsedPadding,
    );
  }, [
    labelPattern,
    mode,
    parsedCount,
    parsedPadding,
    parsedStart,
    source.kind,
  ]);

  const labelSample = useMemo(
    () => previewLabelSample(labelExpansion.labels),
    [labelExpansion.labels],
  );

  const plantLocations = useMemo(
    () =>
      references.status === "ready"
        ? locationsForScope(references.locations, "plants")
        : [],
    [references],
  );

  const selectedLocation = useMemo(
    () => plantLocations.find((item) => item.id === locationId) ?? null,
    [locationId, plantLocations],
  );

  const selectedIdentity = useMemo(
    () =>
      references.status === "ready"
        ? (references.identities.find((item) => item.id === identityId) ?? null)
        : null,
    [identityId, references],
  );

  function handleCountChange(nextValue: string) {
    setCountInput(nextValue);
    if (source.kind === "sowing" && !lifecycleManuallyChosen) {
      const numeric = /^\d+$/.test(nextValue.trim())
        ? Number(nextValue.trim())
        : NaN;
      if (Number.isInteger(numeric) && numeric >= 1) {
        setResultingLifecycle(defaultSowingLifecycle(source.sowing, numeric));
      }
    }
  }

  function validateForm(formElement: HTMLFormElement): string[] {
    const nextErrors: string[] = [];
    if (
      !Number.isInteger(parsedCount) ||
      parsedCount < 1 ||
      parsedCount > maxCount
    ) {
      if (exactGroupQuantity !== null && parsedCount > exactGroupQuantity) {
        nextErrors.push(
          `Count cannot exceed the exact group quantity of ${String(exactGroupQuantity)}.`,
        );
      } else {
        nextErrors.push(
          `Count must be a whole number between 1 and ${String(maxCount)}.`,
        );
      }
    }
    if (!identityId) {
      nextErrors.push("Choose a Botanical identity.");
    }
    if (source.kind === "sowing" && mode === "group") {
      const normalized = normalizeSingleLineLabel(groupLabel);
      if (normalized.error) {
        nextErrors.push(normalized.error);
      } else if (
        normalized.normalized &&
        normalized.normalized.length > MAX_LABEL_LENGTH
      ) {
        nextErrors.push(
          `Label must not exceed ${String(MAX_LABEL_LENGTH)} characters.`,
        );
      }
    } else {
      if (!Number.isInteger(parsedStart) || parsedStart < 0) {
        nextErrors.push(
          "Counter start must be zero or a positive whole number.",
        );
      }
      if (
        parsedPadding !== null &&
        (!Number.isInteger(parsedPadding) ||
          parsedPadding < 0 ||
          parsedPadding > MAX_LABEL_LENGTH)
      ) {
        nextErrors.push(
          "Counter padding must be a whole number between 0 and 255.",
        );
      }
      if (
        nextErrors.length === 0 &&
        Number.isInteger(parsedCount) &&
        parsedCount >= 1 &&
        parsedCount <= MAX_BATCH_COUNT
      ) {
        const checked = expandLabelPattern(
          labelPattern,
          parsedCount,
          parsedStart,
          parsedPadding,
        );
        if (checked.error) nextErrors.push(checked.error);
      }
    }
    for (const control of invalidDateControls(formElement)) {
      nextErrors.push(control.validationMessage);
    }
    return nextErrors;
  }

  function handlePreview(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const nextErrors = validateForm(event.currentTarget);
    if (nextErrors.length > 0) {
      setErrors(nextErrors);
      setStaleConflict(false);
      window.setTimeout(() => alertRef.current?.focus(), 0);
      return;
    }
    setErrors([]);
    setStaleConflict(false);
    setStep("preview");
  }

  async function handleRefreshSource() {
    if (refreshing || pending) return;
    setRefreshing(true);
    try {
      if (source.kind === "sowing") {
        const fresh = await getSowing(source.sowing.id, capability);
        setSource({ kind: "sowing", sowing: fresh });
        onSowingUpdated?.(fresh);
        setStaleConflict(false);
        setErrors(
          fresh.lifecycle !== "active"
            ? [
                `Sowing is now ${fresh.lifecycle} and cannot be potted on in a batch.`,
              ]
            : [],
        );
        setStep("form");
      } else {
        const fresh = await getPlantGroup(source.group.id, capability);
        setSource({ kind: "group", group: fresh });
        onGroupUpdated?.(fresh, []);
        setStaleConflict(false);
        setErrors(
          fresh.lifecycle !== "active"
            ? [
                `Plant group is now ${fresh.lifecycle} and cannot be split into plants.`,
              ]
            : [],
        );
        setStep("form");
      }
    } catch (error: unknown) {
      if (isExpectedAuthCancellation(error)) return;
      if (error instanceof ApiError && error.status === 401) {
        sessionExpired();
      } else {
        setErrors(["Florabase could not refresh the record. Try again."]);
      }
    } finally {
      setRefreshing(false);
    }
  }

  async function handleConfirm() {
    if (pending) return;
    const csrfToken = activeCsrfToken(auth.state);
    if (!csrfToken) return;
    setPending(true);
    setErrors([]);
    setStaleConflict(false);
    try {
      if (source.kind === "sowing" && mode === "plants") {
        const response = await potOnSowing(
          source.sowing.id,
          {
            count: parsedCount,
            label_pattern: labelPattern.trim() ? labelPattern : null,
            counter_start: parsedStart,
            counter_padding: parsedPadding,
            botanical_identity_id: identityId,
            location_id: locationId || null,
            collection_entry_date: entryDate,
            notes: notes.trim() ? notes : null,
            plant_lifecycle: "active",
            resulting_sowing_lifecycle: resultingLifecycle,
            expected_sowing_updated_at: source.sowing.updated_at,
          },
          csrfToken,
          capability,
        );
        setSource({ kind: "sowing", sowing: response.sowing });
        onSowingUpdated?.(response.sowing);
        const lifecycleDisplay =
          sowingLifecycleOptions.find(
            (item) => item.value === response.sowing.lifecycle,
          )?.display ?? response.sowing.lifecycle;
        setResult({
          kind: "plants",
          plants: response.plants,
          summary: `Created ${String(response.plants.length)} ${response.plants.length === 1 ? "Plant" : "Plants"}; Sowing is now ${lifecycleDisplay}.`,
        });
        setStep("success");
        window.setTimeout(() => successRef.current?.focus(), 0);
      } else if (source.kind === "sowing" && mode === "group") {
        const response = await createPlantGroupFromSowing(
          source.sowing.id,
          {
            plant_group: {
              botanical_identity_id: identityId,
              label: groupLabel.trim() ? groupLabel : null,
              collection_entry_date: entryDate,
              location_id: locationId || null,
              lifecycle: "active",
              notes: notes.trim() ? notes : null,
              quantity: { value: parsedCount, is_approximate: false },
            },
            resulting_sowing_lifecycle: resultingLifecycle,
          },
          csrfToken,
          capability,
        );
        setSource({ kind: "sowing", sowing: response.sowing });
        onSowingUpdated?.(response.sowing);
        const lifecycleDisplay =
          sowingLifecycleOptions.find(
            (item) => item.value === response.sowing.lifecycle,
          )?.display ?? response.sowing.lifecycle;
        setResult({
          kind: "group",
          group: response.plant_group,
          summary: `Created 1 Plant group of ${String(parsedCount)}; Sowing is now ${lifecycleDisplay}.`,
        });
        setStep("success");
        window.setTimeout(() => successRef.current?.focus(), 0);
      } else if (source.kind === "group") {
        const response = await extractPlantsFromGroup(
          source.group.id,
          {
            count: parsedCount,
            label_pattern: labelPattern.trim() ? labelPattern : null,
            counter_start: parsedStart,
            counter_padding: parsedPadding,
            botanical_identity_id: identityId,
            location_id: locationId || null,
            collection_entry_date: entryDate,
            notes: notes.trim() ? notes : null,
            expected_plant_group_updated_at: source.group.updated_at,
          },
          csrfToken,
          capability,
        );
        setSource({ kind: "group", group: response.plant_group });
        onGroupUpdated?.(response.plant_group, response.plants);
        const qtySummary = response.plant_group.quantity
          ? response.plant_group.quantity.is_approximate
            ? `Group remains ~${String(response.plant_group.quantity.value)}.`
            : response.plant_group.lifecycle === "completed"
              ? "Group is now Completed (0 remaining)."
              : `Group quantity is now ${String(response.plant_group.quantity.value)}.`
          : "Group quantity remains unknown.";
        setResult({
          kind: "plants",
          plants: response.plants,
          summary: `Split ${String(response.plants.length)} ${response.plants.length === 1 ? "Plant" : "Plants"} from group. ${qtySummary}`,
        });
        setStep("success");
        window.setTimeout(() => successRef.current?.focus(), 0);
      }
    } catch (error: unknown) {
      if (isExpectedAuthCancellation(error)) {
        setPending(false);
        return;
      }
      if (error instanceof ApiError && error.status === 401) {
        sessionExpired();
      } else if (error instanceof ApiError && error.status === 409) {
        const detail = propagationErrorDetail(error);
        const mapped = conflictMessage(
          source.kind,
          detail.code,
          detail.message,
        );
        setErrors([mapped.message]);
        setStaleConflict(mapped.stale);
      } else if (error instanceof ApiError && error.status === 422) {
        setErrors([
          "Check the batch details (count, labels, or date) and try again.",
        ]);
        setStaleConflict(false);
      } else {
        setErrors([
          source.kind === "sowing"
            ? "Florabase could not pot on these seedlings. No records were created."
            : "Florabase could not split plants from this group. No records were created.",
        ]);
        setStaleConflict(false);
      }
      window.setTimeout(() => alertRef.current?.focus(), 0);
    } finally {
      setPending(false);
    }
  }

  const previewSentence = useMemo(() => {
    const noun = parsedCount === 1 ? "Plant" : "Plants";
    const locationPart = selectedLocation
      ? ` in ${selectedLocation.display_path}`
      : "";
    if (source.kind === "sowing") {
      const lifecycleDisplay =
        sowingLifecycleOptions.find((item) => item.value === resultingLifecycle)
          ?.display ?? resultingLifecycle;
      const sowingClause = `sowing becomes ${lifecycleDisplay}`;
      if (mode === "group") {
        const normalized = normalizeSingleLineLabel(groupLabel).normalized;
        const labelPart = normalized ? ` ${normalized}` : "";
        return `Will create 1 Plant group of ${String(parsedCount)}${labelPart}${locationPart}; ${sowingClause}.`;
      }
      const labelPart =
        labelSample.first && labelSample.last
          ? parsedCount === 1
            ? ` ${labelSample.first}`
            : ` ${labelSample.first} … ${labelSample.last}`
          : " (unlabelled)";
      return `Will create ${String(parsedCount)} ${noun}${labelPart}${locationPart}; ${sowingClause}.`;
    }
    const labelPart =
      labelSample.first && labelSample.last
        ? parsedCount === 1
          ? ` ${labelSample.first}`
          : ` ${labelSample.first} … ${labelSample.last}`
        : " (unlabelled)";
    const groupClause =
      exactGroupQuantity !== null
        ? exactGroupQuantity - parsedCount === 0
          ? "group becomes Completed"
          : `group quantity becomes ${String(exactGroupQuantity - parsedCount)}`
        : approximateGroupQuantity !== null
          ? `approximate group quantity (~${String(approximateGroupQuantity)}) remains unchanged`
          : "unknown group quantity remains unchanged";
    return `Will create ${String(parsedCount)} ${noun}${labelPart}${locationPart}; ${groupClause}.`;
  }, [
    approximateGroupQuantity,
    exactGroupQuantity,
    groupLabel,
    labelSample.first,
    labelSample.last,
    mode,
    parsedCount,
    resultingLifecycle,
    selectedLocation,
    source.kind,
  ]);

  const dialogTitle =
    source.kind === "sowing" ? "Pot on seedlings" : "Split into plants";
  const sourceDisplayName =
    source.kind === "sowing"
      ? recordName(source.sowing, "Unlabelled sowing")
      : recordName(source.group, "Unlabelled plant group");

  return (
    <TaskDialog
      title={dialogTitle}
      className="pot-on-dialog"
      returnFocusTo={returnFocusTo}
      fallbackFocusTo={fallbackFocusTo}
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <h3 id={titleId}>{dialogTitle}</h3>
      <p className="field-help">
        From <strong>{sourceDisplayName}</strong>
      </p>

      {references.status === "loading" ? (
        <div role="status">
          <p>Loading botanical identities and locations…</p>
          <div className="actions">
            <button
              type="button"
              className="button--secondary"
              onClick={onClose}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : references.status === "error" ? (
        <div>
          <div className="notice notice--error" role="alert">
            Florabase could not load botanical identities and locations.
          </div>
          <div className="actions">
            <button
              type="button"
              className="button--secondary"
              onClick={onClose}
            >
              Close
            </button>
            <button
              type="button"
              onClick={() => {
                setFetchedReferences({ status: "loading" });
                setRefAttempt((value) => value + 1);
              }}
            >
              Retry
            </button>
          </div>
        </div>
      ) : step === "success" && result ? (
        <div>
          <div
            className="notice notice--success"
            role="status"
            tabIndex={-1}
            ref={successRef}
          >
            <p>{result.summary}</p>
          </div>
          {result.kind === "plants" ? (
            <div style={{ marginBlock: "0.75rem" }}>
              <p className="field-help">Created Plants:</p>
              <ul
                style={{
                  maxHeight: "14rem",
                  overflowY: "auto",
                  paddingInlineStart: "1.25rem",
                  marginBlock: "0.5rem",
                }}
              >
                {result.plants.map((plant) => (
                  <li key={plant.id}>
                    <a href={`#/plants/${plant.id}`} onClick={onClose}>
                      {plant.label ?? plant.botanical_identity.display_label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p style={{ marginBlock: "0.75rem" }}>
              <a href={`#/plant-groups/${result.group.id}`} onClick={onClose}>
                Open{" "}
                {result.group.label ??
                  result.group.botanical_identity.display_label}
              </a>
            </p>
          )}
          <div className="actions">
            <button type="button" onClick={onClose}>
              Done
            </button>
          </div>
        </div>
      ) : step === "preview" ? (
        <div>
          {errors.length > 0 && (
            <div
              className="notice notice--error"
              role="alert"
              tabIndex={-1}
              ref={alertRef}
            >
              <ul>
                {errors.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="notice" aria-live="polite">
            <p>
              <strong>{previewSentence}</strong>
            </p>
          </div>
          <dl
            style={{ display: "grid", gap: "0.5rem", marginBlock: "0.75rem" }}
          >
            <div>
              <dt>Botanical identity</dt>
              <dd>{selectedIdentity?.display_label ?? "Selected identity"}</dd>
            </div>
            <div>
              <dt>Location</dt>
              <dd>{selectedLocation?.display_path ?? "Not recorded"}</dd>
            </div>
            <div>
              <dt>Collection-entry date</dt>
              <dd>{formatPartialDate(entryDate)}</dd>
            </div>
            {(source.kind === "group" || mode === "plants") &&
              labelSample.head.length > 0 && (
                <div>
                  <dt>Labels ({String(parsedCount)})</dt>
                  <dd>
                    {labelSample.head.join(", ")}
                    {labelSample.omitted > 0 && labelSample.tail
                      ? `, … (${String(labelSample.omitted)} more), ${labelSample.tail}`
                      : labelSample.tail
                        ? `, ${labelSample.tail}`
                        : ""}
                  </dd>
                </div>
              )}
          </dl>
          <div className="actions">
            <button
              type="button"
              className="button--secondary"
              disabled={pending || refreshing}
              onClick={() => {
                setErrors([]);
                setStaleConflict(false);
                setStep("form");
              }}
            >
              Back to edit
            </button>
            {staleConflict ? (
              <button
                type="button"
                disabled={refreshing}
                onClick={() => {
                  void handleRefreshSource();
                }}
              >
                {refreshing
                  ? "Refreshing…"
                  : source.kind === "sowing"
                    ? "Refresh Sowing"
                    : "Refresh Plant group"}
              </button>
            ) : (
              <button
                type="button"
                disabled={pending}
                onClick={() => {
                  void handleConfirm();
                }}
              >
                {pending
                  ? "Creating…"
                  : source.kind === "sowing"
                    ? "Confirm pot-on"
                    : "Confirm split"}
              </button>
            )}
          </div>
        </div>
      ) : (
        <form onSubmit={handlePreview} noValidate>
          {errors.length > 0 && (
            <div
              className="notice notice--error"
              role="alert"
              tabIndex={-1}
              ref={alertRef}
            >
              <ul>
                {errors.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
          )}

          {source.kind === "sowing" && (
            <fieldset className="sowing-state-options">
              <legend>Create as</legend>
              <label>
                <input
                  type="radio"
                  name="pot-on-mode"
                  checked={mode === "plants"}
                  disabled={pending}
                  onChange={() => {
                    setMode("plants");
                  }}
                />
                N individual Plants
              </label>
              <label>
                <input
                  type="radio"
                  name="pot-on-mode"
                  checked={mode === "group"}
                  disabled={pending}
                  onChange={() => {
                    setMode("group");
                  }}
                />
                One Plant group of N
              </label>
            </fieldset>
          )}

          <div className="field">
            <FieldLabel htmlFor={countId} required>
              {source.kind === "sowing"
                ? "Number of seedlings"
                : "Number of plants to split"}
            </FieldLabel>
            <input
              id={countId}
              type="number"
              inputMode="numeric"
              min={1}
              max={maxCount}
              required
              aria-describedby={countHelpId}
              value={countInput}
              disabled={pending}
              onChange={(event) => {
                handleCountChange(event.currentTarget.value);
              }}
            />
            <FieldHelp id={countHelpId}>
              {source.kind === "sowing"
                ? source.sowing.germinated_count !== null
                  ? `Germinated count: ${String(source.sowing.germinated_count)} (hint only, not enforced; 1–${String(MAX_BATCH_COUNT)}).`
                  : `No germinated count recorded (1–${String(MAX_BATCH_COUNT)}).`
                : exactGroupQuantity !== null
                  ? `Exact group quantity: ${String(exactGroupQuantity)} (split up to ${String(maxCount)}).`
                  : approximateGroupQuantity !== null
                    ? `Approximate group quantity: ~${String(approximateGroupQuantity)} (up to ${String(MAX_BATCH_COUNT)}).`
                    : `Group quantity is unknown and will remain unknown (1–${String(MAX_BATCH_COUNT)}).`}
            </FieldHelp>
          </div>

          {approximateGroupQuantity !== null && (
            <div className="notice notice--duplicate" role="status">
              This group has an approximate quantity (~
              {String(approximateGroupQuantity)}). Splitting plants will leave
              the approximate group quantity unchanged.
            </div>
          )}

          {source.kind === "sowing" && mode === "group" ? (
            <div className="field">
              <label htmlFor={groupLabelId}>Plant group label</label>
              <input
                id={groupLabelId}
                value={groupLabel}
                maxLength={MAX_LABEL_LENGTH}
                disabled={pending}
                onChange={(event) => {
                  setGroupLabel(event.currentTarget.value);
                }}
              />
            </div>
          ) : (
            <>
              <div className="field">
                <label htmlFor={patternId}>Label pattern</label>
                <input
                  id={patternId}
                  placeholder="HOY-24-07-{n}"
                  aria-describedby={patternHelpId}
                  value={labelPattern}
                  maxLength={MAX_LABEL_LENGTH}
                  disabled={pending}
                  onChange={(event) => {
                    setLabelPattern(event.currentTarget.value);
                  }}
                />
                <FieldHelp id={patternHelpId}>
                  Use <code>{"{n}"}</code> for the counter, or leave blank for
                  unlabelled plants.
                </FieldHelp>
              </div>

              <div className="form-grid">
                <div className="field">
                  <label htmlFor={startId}>Counter start</label>
                  <input
                    id={startId}
                    type="number"
                    inputMode="numeric"
                    min={0}
                    value={counterStartInput}
                    disabled={pending}
                    onChange={(event) => {
                      setCounterStartInput(event.currentTarget.value);
                    }}
                  />
                </div>
                <div className="field">
                  <label htmlFor={paddingId}>Counter padding</label>
                  <input
                    id={paddingId}
                    type="number"
                    inputMode="numeric"
                    min={0}
                    max={MAX_LABEL_LENGTH}
                    placeholder={`Auto (${String(autoPadding)})`}
                    value={counterPaddingInput}
                    disabled={pending}
                    onChange={(event) => {
                      setCounterPaddingInput(event.currentTarget.value);
                    }}
                  />
                </div>
              </div>

              {labelExpansion.error && (
                <div className="notice notice--error" role="alert">
                  {labelExpansion.error}
                </div>
              )}

              {labelExpansion.duplicateWarning && (
                <div className="notice notice--duplicate" role="status">
                  Pattern does not include <code>{"{n}"}</code> — all{" "}
                  {String(parsedCount)} plants will receive the same label.
                </div>
              )}

              {!labelExpansion.error && labelSample.head.length > 0 && (
                <div className="field" aria-live="polite">
                  <span className="field-help">
                    Label preview:{" "}
                    <strong>
                      {labelSample.head.join(", ")}
                      {labelSample.omitted > 0 && labelSample.tail
                        ? `, …, ${labelSample.tail}`
                        : labelSample.tail
                          ? `, ${labelSample.tail}`
                          : ""}
                    </strong>
                  </span>
                </div>
              )}
            </>
          )}

          <ReferencePicker
            label="Botanical identity"
            required
            openOnFocus={false}
            disabled={pending}
            choices={references.identities.map((identity) => ({
              id: identity.id,
              label: identity.display_label,
              scientificName: identity.scientific_name,
            }))}
            value={identityId}
            onChange={setIdentityId}
            onCreate={(query) => {
              setIdentityDraft(query);
            }}
            createLabel="Create identity"
          />
          {identityDraft !== null && (
            <IdentityCreateDialog
              initialName={identityDraft}
              onClose={() => {
                setIdentityDraft(null);
              }}
              onCreated={(identity) => {
                setCreatedIdentities((current) => [
                  ...current.filter((item) => item.id !== identity.id),
                  identity,
                ]);
                setIdentityId(identity.id);
                setIdentityDraft(null);
              }}
            />
          )}

          <ReferencePicker
            label="Current location"
            placeholder="Not recorded"
            openOnFocus={false}
            disabled={pending}
            choices={plantLocations.map((location) => ({
              id: location.id,
              label: location.display_path,
              retired: Boolean(location.retired_at),
            }))}
            value={locationId}
            onChange={setLocationId}
          />

          <PartialDateField
            id="pot-on-entry-date"
            label="Collection-entry date"
            hidePrecisionLabel
            value={entryDate}
            disabled={pending}
            onChange={setEntryDate}
          />

          <div className="field">
            <label htmlFor={notesId}>Notes</label>
            <textarea
              id={notesId}
              rows={2}
              value={notes}
              disabled={pending}
              onChange={(event) => {
                setNotes(event.currentTarget.value);
              }}
            />
          </div>

          {source.kind === "sowing" && (
            <fieldset
              className="sowing-state-options"
              aria-describedby={lifecycleHelpId}
            >
              <legend>Sowing afterwards</legend>
              {sowingLifecycleOptions.map((option) => (
                <label key={option.value}>
                  <input
                    type="radio"
                    name="pot-on-sowing-lifecycle"
                    checked={resultingLifecycle === option.value}
                    disabled={pending}
                    onChange={() => {
                      setLifecycleManuallyChosen(true);
                      setResultingLifecycle(option.value);
                    }}
                  />
                  {option.label}
                </label>
              ))}
              <FieldHelp id={lifecycleHelpId}>
                Defaults to Completed when the count meets or exceeds the
                germinated count.
              </FieldHelp>
            </fieldset>
          )}

          <div className="actions">
            <button
              type="button"
              className="button--secondary"
              disabled={pending}
              onClick={onClose}
            >
              Cancel
            </button>
            <button type="submit" disabled={pending}>
              Review &amp; confirm
            </button>
          </div>
        </form>
      )}
    </TaskDialog>
  );
}

export function PotOnLauncher({
  source,
  identities,
  locations,
  fallbackFocusTo,
  onSowingUpdated,
  onGroupUpdated,
}: {
  source: PotOnSource;
  identities?: BotanicalIdentityResponse[];
  locations?: LocationResponse[];
  fallbackFocusTo?: RefObject<HTMLElement | null>;
  onSowingUpdated?: (sowing: SowingResponse) => void;
  onGroupUpdated?: (group: PlantGroupResponse, plants: PlantResponse[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const isActive =
    source.kind === "sowing"
      ? source.sowing.lifecycle === "active"
      : source.group.lifecycle === "active";
  if (!isActive && !open) return null;
  const label =
    source.kind === "sowing" ? "Pot on seedlings…" : "Split into plants…";
  return (
    <>
      {isActive && (
        <button
          type="button"
          className="button--secondary"
          ref={triggerRef}
          onClick={() => {
            setOpen(true);
          }}
        >
          {label}
        </button>
      )}
      {open && (
        <PotOnDialog
          source={source}
          identities={identities}
          locations={locations}
          returnFocusTo={triggerRef}
          fallbackFocusTo={fallbackFocusTo}
          onClose={() => {
            setOpen(false);
          }}
          onSowingUpdated={onSowingUpdated}
          onGroupUpdated={onGroupUpdated}
        />
      )}
    </>
  );
}
