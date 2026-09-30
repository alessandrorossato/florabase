import { firstValidationField } from "../components/formValidation";
import { FormSections } from "../components/FormSections";
import {
  sowingFormPanels,
  sowingErrorFields,
} from "../sowings/SowingFormFields";
import { useRecordName } from "../components/recordPresentation";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { Breadcrumbs } from "../components/CollectionUI";
import { listLocations, type LocationResponse } from "../locations/api";
import {
  createSowingFromSeedLot,
  listSeedLots,
  type PartialDate,
  type SeedLotResponse,
  type SeedLotSowingTransitionCreate,
} from "../seed-lots/api";

type QuantityKind = "unknown" | "seed_count" | "weight";
type UsageMode = "partial" | "use_all" | "none";

interface FormState {
  label: string;
  sowingDate: PartialDate | null;
  quantityKind: QuantityKind;
  quantityValue: string;
  quantityUnit: "g" | "mg";
  quantityApproximate: boolean;
  locationId: string;
  methodContainer: string;
  substrate: string;
  pretreatment: string;
  temperatureMinC: string;
  temperatureMaxC: string;
  environment: string;
  notes: string;
}

function initialForm(lot: SeedLotResponse): FormState {
  return {
    label: "",
    sowingDate: null,
    quantityKind: lot.quantity?.kind ?? "unknown",
    quantityValue: "",
    quantityUnit:
      lot.quantity?.kind === "weight" ? (lot.quantity.unit ?? "g") : "g",
    quantityApproximate: lot.quantity?.is_approximate ?? false,
    locationId: lot.location_id ?? "",
    methodContainer: "",
    substrate: "",
    pretreatment: "",
    temperatureMinC: "",
    temperatureMaxC: "",
    environment: "",
    notes: "",
  };
}

const blankForm: FormState = {
  label: "",
  sowingDate: null,
  quantityKind: "unknown",
  quantityValue: "",
  quantityUnit: "g",
  quantityApproximate: false,
  locationId: "",
  methodContainer: "",
  substrate: "",
  pretreatment: "",
  temperatureMinC: "",
  temperatureMaxC: "",
  environment: "",
  notes: "",
};

function quantityText(lot: SeedLotResponse): string {
  if (!lot.quantity) return "Quantity unknown";
  const unit = lot.quantity.kind === "seed_count" ? "seeds" : lot.quantity.unit;
  return `${lot.quantity.is_approximate ? "About " : ""}${lot.quantity.value} ${unit ?? ""}`;
}

export function SeedLotSowingWizard({ seedLotId }: { seedLotId: string }) {
  const auth = useAuth();
  const recordName = useRecordName();

  const [data, setData] = useState<
    | { status: "loading" }
    | { status: "error" }
    | { status: "ready"; lot: SeedLotResponse; locations: LocationResponse[] }
  >({ status: "loading" });
  const [form, setForm] = useState<FormState>(blankForm);
  const [stage, setStage] = useState<1 | 2>(1);
  const [usage, setUsage] = useState<UsageMode>("none");
  const [remainder, setRemainder] = useState("");
  const [messages, setMessages] = useState<string[]>([]);
  const [validationField, setValidationField] = useState<string | undefined>();
  const sectionError = useMemo(
    () => (messages.length ? { messages, field: validationField } : undefined),
    [messages, validationField],
  );
  const [pending, setPending] = useState(false);
  const feedback = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      listSeedLots(controller.signal),
      listLocations(controller.signal),
    ])
      .then(([lots, locations]) => {
        const lot = lots.find(({ id }) => id === seedLotId);
        if (!lot) throw new Error("missing");
        setData({ status: "ready", lot, locations });
        setForm(initialForm(lot));
      })
      .catch(() => {
        if (!controller.signal.aborted) setData({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [seedLotId]);

  const preview = useMemo(() => {
    if (data.status !== "ready" || !data.lot.quantity) return null;
    const source = Number(data.lot.quantity.value);
    const used = Number(form.quantityValue);
    const compatible =
      form.quantityKind === data.lot.quantity.kind &&
      (form.quantityKind !== "weight" ||
        form.quantityUnit === data.lot.quantity.unit);
    if (!compatible || !form.quantityValue || !Number.isFinite(used))
      return {
        compatible,
        suggested: null,
        oversubscribed: false,
        matchesSource: false,
      };
    return {
      compatible,
      suggested: data.lot.quantity.is_approximate
        ? null
        : Math.max(0, source - used),
      oversubscribed: !data.lot.quantity.is_approximate && used > source,
      matchesSource: used === source,
    };
  }, [data, form]);

  if (data.status === "loading")
    return (
      <section className="workspace">
        <p role="status">Loading guided sowing…</p>
      </section>
    );
  if (data.status === "error")
    return (
      <section className="workspace">
        <div className="notice notice--error" role="alert">
          Florabase could not load the source SeedLot.
        </div>
      </section>
    );
  const { lot, locations } = data;
  const sourceApproximate = Boolean(lot.quantity?.is_approximate);
  const sourceUnknown = lot.quantity === null;
  const canPartial =
    sourceUnknown ||
    (Boolean(preview?.compatible) &&
      !preview?.oversubscribed &&
      (sourceApproximate || !form.quantityApproximate));
  const canUseAll =
    sourceUnknown ||
    form.quantityKind === "unknown" ||
    (Boolean(preview?.compatible) &&
      (sourceApproximate ||
        form.quantityApproximate ||
        preview?.matchesSource));

  function validateDetails(): string[] {
    const errors: string[] = [];
    const amount = Number(form.quantityValue);
    if (form.quantityKind !== "unknown") {
      if (!form.quantityValue || !Number.isFinite(amount) || amount <= 0)
        errors.push("Quantity sown must be greater than zero.");
      if (form.quantityKind === "seed_count" && !Number.isInteger(amount))
        errors.push("Seed count must be a whole number.");
    }
    const minimum = Number(form.temperatureMinC);
    const maximum = Number(form.temperatureMaxC);
    if (form.temperatureMinC && !Number.isFinite(minimum))
      errors.push("Enter a valid minimum temperature.");
    if (form.temperatureMaxC && !Number.isFinite(maximum))
      errors.push("Enter a valid maximum temperature.");
    if (form.temperatureMinC && form.temperatureMaxC && minimum > maximum)
      errors.push("Minimum temperature cannot exceed maximum temperature.");
    return errors;
  }

  function continueToUsage() {
    setValidationField(undefined);
    const errors = validateDetails();
    if (errors.length) {
      setMessages(errors);
      return;
    }
    setUsage("none");
    setRemainder(lot.quantity?.value ?? "");
    setMessages([]);
    setStage(2);
  }

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    if (stage === 1) {
      continueToUsage();
      return;
    }
    const errors: string[] = [];
    if (usage === "partial" && preview?.oversubscribed)
      errors.push("The Sowing quantity exceeds the exact quantity available.");
    if (usage === "partial" && !canPartial)
      errors.push(
        "Partial adjustment is unavailable because the quantities use incompatible dimensions or units.",
      );
    if (usage === "partial" && sourceApproximate) {
      const value = Number(remainder);
      if (!remainder || !Number.isFinite(value) || value < 0)
        errors.push("Enter a non-negative resulting estimate.");
    }
    if (errors.length) {
      setMessages(errors);
      feedback.current?.focus();
      return;
    }
    const quantity =
      form.quantityKind === "unknown"
        ? null
        : {
            kind: form.quantityKind,
            value: form.quantityValue,
            unit: form.quantityKind === "weight" ? form.quantityUnit : null,
            is_approximate: form.quantityApproximate,
          };
    const source_adjustment: SeedLotSowingTransitionCreate["source_adjustment"] =
      usage === "none"
        ? { mode: "none" }
        : usage === "use_all"
          ? { mode: "use_all" }
          : {
              mode: "partial",
              resulting_quantity:
                sourceApproximate && lot.quantity
                  ? {
                      kind: lot.quantity.kind,
                      value: remainder,
                      unit: lot.quantity.unit,
                      is_approximate: true,
                    }
                  : null,
            };
    setPending(true);
    setMessages([]);
    setValidationField(undefined);
    try {
      const result = await createSowingFromSeedLot(
        lot.id,
        {
          sowing: {
            label: form.label || null,
            sowing_date: form.sowingDate,
            quantity,
            germinated_count: null,
            location_id: form.locationId || null,
            method_container: form.methodContainer || null,
            substrate: form.substrate || null,
            pretreatment: form.pretreatment || null,
            temperature_min_c: form.temperatureMinC || null,
            temperature_max_c: form.temperatureMaxC || null,
            environment: form.environment || null,
            lifecycle: "active",
            notes: form.notes || null,
          },
          source_adjustment,
        },
        auth.state.status === "authenticated" ||
          auth.state.status === "logging-out" ||
          auth.state.status === "logout-failed"
          ? auth.state.csrfToken
          : "",
      );
      window.location.hash = `/sowings/${result.sowing.id}`;
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 422) {
        setValidationField(firstValidationField(error));
        const field = firstValidationField(error);
        if (field?.startsWith("sowing_")) setStage(1);
      }

      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else if (error instanceof ApiError && error.status === 409)
        setMessages([
          "The source SeedLot changed or cannot accept this adjustment. Review its current state and try again.",
        ]);
      else
        setMessages([
          "Florabase could not create the Sowing. Your details are still here; review them and try again.",
        ]);
      setPending(false);
      window.setTimeout(() => feedback.current?.focus(), 0);
    }
  }

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  return (
    <section
      className="workspace propagation-workspace"
      aria-labelledby="guided-sowing-title"
    >
      <Breadcrumbs
        items={[
          {
            label: lot.botanical_identity.display_label,
            href: `#/identities/${lot.botanical_identity.id}?tab=seeds`,
          },
          { label: recordName(lot, "SeedLot"), href: `#/seeds/${lot.id}` },
          { label: "Start sowing" },
        ]}
      />
      <div className="workspace-intro">
        <div>
          <p className="eyebrow">Guided propagation · Step {stage} of 2</p>
          <h2 id="guided-sowing-title">Start sowing</h2>
          <p>
            Record the Sowing, then choose what happens to the source seed lot.
          </p>
        </div>
      </div>
      <section
        className="seed-sowing-source"
        aria-labelledby="source-seed-lot-title"
      >
        <h3 id="source-seed-lot-title">Source seed lot</h3>
        <dl>
          <div>
            <dt>Lot</dt>
            <dd>
              <a href={`#/seeds/${lot.id}`}>
                {recordName(lot, "Unlabelled seed lot")}
              </a>
            </dd>
          </div>
          <div>
            <dt>Botanical identity</dt>
            <dd>{lot.botanical_identity.display_label}</dd>
          </div>
          <div>
            <dt>Current quantity</dt>
            <dd>{quantityText(lot)}</dd>
          </div>
          <div>
            <dt>Storage</dt>
            <dd>{lot.location?.display_path ?? "Not recorded"}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              {lot.lifecycle.charAt(0).toUpperCase() + lot.lifecycle.slice(1)}
            </dd>
          </div>
        </dl>
      </section>
      <form
        className="propagation-form"
        onSubmit={(event) => void submit(event)}
        noValidate
      >
        {stage === 1 ? (
          <>
            <h3>Sowing details</h3>
            <FormSections
              disabled={pending}
              error={sectionError}
              errorFields={sowingErrorFields}
              panels={sowingFormPanels({
                form,
                updateForm: update,
                locations,
                pending,
                source: (
                  <div className="field">
                    <span className="field-label">Source SeedLot</span>
                    <strong>{recordName(lot, "SeedLot")}</strong>
                    <small>Locked to the source above.</small>
                  </div>
                ),
              })}
              submit={
                <button type="button" onClick={continueToUsage}>
                  Review seed usage
                </button>
              }
              cancel={
                <a
                  className="button-link button--secondary"
                  href={`#/seeds/${lot.id}`}
                >
                  Cancel
                </a>
              }
            />
            {messages.length > 0 && (
              <div className="notice notice--error" role="alert">
                <ul>
                  {messages.map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <>
            <h3>Seed usage</h3>
            <p>
              Choose the effect on the source before starting the Sowing.
              Nothing changes until you submit.
            </p>
            <div className="quantity-effect" aria-live="polite">
              <p>
                <strong>Current source:</strong> {quantityText(lot)}
              </p>
              <p>
                <strong>Sowing:</strong>{" "}
                {form.quantityKind === "unknown"
                  ? "Quantity unknown"
                  : `${form.quantityApproximate ? "About " : ""}${form.quantityValue} ${form.quantityKind === "seed_count" ? "seeds" : form.quantityUnit}`}
              </p>
            </div>
            <fieldset className="choice-cards">
              <legend>What happens to the source seed lot?</legend>
              <label>
                <input
                  type="radio"
                  name="usage"
                  checked={usage === "none"}
                  onChange={() => {
                    setUsage("none");
                  }}
                />{" "}
                <span>
                  <strong>Keep inventory unchanged</strong>
                  <small>
                    Creates the Sowing without adjusting the source quantity.
                  </small>
                </span>
              </label>
              {canPartial && (
                <label>
                  <input
                    type="radio"
                    name="usage"
                    checked={usage === "partial"}
                    onChange={() => {
                      setUsage("partial");
                    }}
                  />{" "}
                  <span>
                    <strong>
                      {sourceUnknown
                        ? "Record partial use; quantity stays unknown"
                        : "Use part of the lot"}
                    </strong>
                    <small>
                      {sourceApproximate
                        ? "Confirm an editable resulting estimate; no exact remainder is inferred."
                        : sourceUnknown
                          ? "No numeric amount will be invented."
                          : `${String(preview?.suggested ?? "")} ${lot.quantity?.kind === "seed_count" ? "seeds" : (lot.quantity?.unit ?? "")} will remain after exact subtraction.`}
                    </small>
                  </span>
                </label>
              )}
              <label aria-disabled={!canUseAll}>
                <input
                  type="radio"
                  name="usage"
                  disabled={!canUseAll}
                  checked={usage === "use_all"}
                  onChange={() => {
                    setUsage("use_all");
                  }}
                />{" "}
                <span>
                  <strong>Use the whole lot</strong>
                  <small>
                    {canUseAll
                      ? "The source becomes exhausted. Approximate or unknown quantities are not rewritten as exact zero."
                      : "For exact compatible quantities, the Sowing amount must equal the source amount."}
                  </small>
                </span>
              </label>
            </fieldset>
            {!canPartial && !preview?.oversubscribed && (
              <div className="notice" role="status">
                These source and Sowing quantities use incompatible dimensions
                or units, so subtraction is not offered. Choose no adjustment,
                or correct the Sowing details.
              </div>
            )}
            {usage === "partial" && sourceApproximate && (
              <div className="estimate-editor">
                <p>Current estimate: {quantityText(lot)}</p>
                <div className="field">
                  <label htmlFor="resulting-estimate">Resulting estimate</label>
                  <div className="quantity-controls">
                    <input
                      id="resulting-estimate"
                      inputMode="decimal"
                      value={remainder}
                      onChange={(event) => {
                        setRemainder(event.currentTarget.value);
                      }}
                    />
                    <span>
                      {lot.quantity?.kind === "seed_count"
                        ? "seeds"
                        : lot.quantity?.unit}
                    </span>
                  </div>
                  <small>
                    This remains approximate. You may keep the current estimate
                    or enter another estimate.
                  </small>
                </div>
              </div>
            )}
            <div className="seed-sowing-confirmation" role="status">
              <strong>Before you start</strong>
              <p>
                A new Sowing will be recorded for{" "}
                {recordName(lot, "this seed lot")}.
              </p>
              <p>
                {usage === "none"
                  ? "The source quantity and lifecycle will stay unchanged."
                  : usage === "use_all"
                    ? "The source will become exhausted; its quantity representation will follow the recorded exact, approximate, or unknown state."
                    : sourceUnknown
                      ? "Partial use will be recorded; the source quantity will remain unknown."
                      : sourceApproximate
                        ? remainder
                          ? `The resulting source estimate must be confirmed as about ${remainder} ${lot.quantity?.kind === "seed_count" ? "seeds" : (lot.quantity?.unit ?? "")}.`
                          : "Enter the resulting source estimate before starting."
                        : `${String(preview?.suggested ?? "")} ${lot.quantity?.kind === "seed_count" ? "seeds" : (lot.quantity?.unit ?? "")} will remain in the source lot.`}
              </p>
            </div>
            {preview?.oversubscribed && (
              <div className="notice notice--error" role="alert">
                The Sowing quantity exceeds the exact source quantity.
                Subtraction cannot be submitted.
              </div>
            )}
            {messages.length > 0 && (
              <div
                className="notice notice--error"
                role="alert"
                tabIndex={-1}
                ref={feedback}
              >
                <ul>
                  {messages.map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="actions">
              <button type="submit" disabled={pending}>
                {pending ? "Starting sowing…" : "Start sowing"}
              </button>
              <button
                type="button"
                className="button--secondary"
                disabled={pending}
                onClick={() => {
                  setStage(1);
                  setMessages([]);
                }}
              >
                Back to details
              </button>
              <a
                className="button-link button--secondary"
                href={`#/seeds/${lot.id}`}
              >
                Cancel
              </a>
            </div>
          </>
        )}
      </form>
    </section>
  );
}
