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
import { PartialDateField } from "../seed-lots/PartialDateField";
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
  return `${lot.quantity.is_approximate ? "~" : ""}${lot.quantity.value} ${unit ?? ""}`;
}

export function SeedLotSowingWizard({ seedLotId }: { seedLotId: string }) {
  const auth = useAuth();
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
      suggested: Math.max(0, source - used),
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
    const errors = validateDetails();
    if (errors.length) {
      setMessages(errors);
      return;
    }
    const naturalPartial =
      lot.lifecycle === "active" && canPartial && !preview?.oversubscribed;
    setUsage(naturalPartial ? "partial" : "none");
    setRemainder(
      sourceApproximate && preview?.suggested != null
        ? String(preview.suggested)
        : (lot.quantity?.value ?? ""),
    );
    setMessages([]);
    setStage(2);
  }

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
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
          { label: lot.label ?? "SeedLot", href: `#/seeds/${lot.id}` },
          { label: "Start sowing" },
        ]}
      />
      <div className="workspace-intro">
        <div>
          <p className="eyebrow">Guided propagation · Step {stage} of 2</p>
          <h2 id="guided-sowing-title">Start sowing</h2>
          <p>
            From <strong>{lot.label ?? "Unlabelled SeedLot"}</strong> ·{" "}
            {lot.botanical_identity.display_label} · {quantityText(lot)} ·{" "}
            {lot.lifecycle}
          </p>
        </div>
      </div>
      <form
        className="propagation-form"
        onSubmit={(event) => void submit(event)}
        noValidate
      >
        {stage === 1 ? (
          <>
            <h3>Sowing details</h3>
            <div className="guided-form-grid">
              <div className="field">
                <label htmlFor="guided-sowing-label">
                  Label <span className="optional">(optional)</span>
                </label>
                <input
                  id="guided-sowing-label"
                  value={form.label}
                  onChange={(event) => {
                    update("label", event.currentTarget.value);
                  }}
                />
              </div>
              <PartialDateField
                id="guided-sowing-date"
                label="Sowing date (optional)"
                value={form.sowingDate}
                disabled={pending}
                onChange={(value) => {
                  update("sowingDate", value);
                }}
              />
              <fieldset className="quantity-field">
                <legend>Quantity sown</legend>
                <div className="field">
                  <label htmlFor="guided-quantity-kind">Kind</label>
                  <select
                    id="guided-quantity-kind"
                    value={form.quantityKind}
                    onChange={(event) => {
                      update(
                        "quantityKind",
                        event.currentTarget.value as QuantityKind,
                      );
                    }}
                  >
                    <option value="unknown">Unknown</option>
                    <option value="seed_count">Seed count</option>
                    <option value="weight">Weight</option>
                  </select>
                </div>
                {form.quantityKind !== "unknown" && (
                  <>
                    <div className="field">
                      <label htmlFor="guided-quantity-value">Amount</label>
                      <input
                        id="guided-quantity-value"
                        inputMode="decimal"
                        value={form.quantityValue}
                        onChange={(event) => {
                          update("quantityValue", event.currentTarget.value);
                        }}
                      />
                    </div>
                    {form.quantityKind === "weight" && (
                      <div className="field">
                        <label htmlFor="guided-quantity-unit">Unit</label>
                        <select
                          id="guided-quantity-unit"
                          value={form.quantityUnit}
                          onChange={(event) => {
                            update(
                              "quantityUnit",
                              event.currentTarget.value as "g" | "mg",
                            );
                          }}
                        >
                          <option value="g">g</option>
                          <option value="mg">mg</option>
                        </select>
                      </div>
                    )}
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={form.quantityApproximate}
                        onChange={(event) => {
                          update(
                            "quantityApproximate",
                            event.currentTarget.checked,
                          );
                        }}
                      />
                      Approximate
                    </label>
                  </>
                )}
              </fieldset>
              <div className="field">
                <label htmlFor="guided-location">
                  Current location <span className="optional">(optional)</span>
                </label>
                <select
                  id="guided-location"
                  value={form.locationId}
                  onChange={(event) => {
                    update("locationId", event.currentTarget.value);
                  }}
                >
                  <option value="">Not recorded</option>
                  {locations.map((location) => (
                    <option
                      key={location.id}
                      value={location.id}
                      disabled={Boolean(location.retired_at)}
                    >
                      {location.display_path}
                    </option>
                  ))}
                </select>
              </div>
              {(
                [
                  ["methodContainer", "Method / container"],
                  ["substrate", "Substrate"],
                  ["pretreatment", "Pretreatment"],
                  ["environment", "Environment / conditions"],
                ] as const
              ).map(([key, label]) => (
                <div className="field" key={key}>
                  <label htmlFor={`guided-${key}`}>
                    {label} <span className="optional">(optional)</span>
                  </label>
                  <input
                    id={`guided-${key}`}
                    value={form[key]}
                    onChange={(event) => {
                      update(key, event.currentTarget.value);
                    }}
                  />
                </div>
              ))}
              <div className="field">
                <label htmlFor="guided-temperature-min">
                  Minimum °C <span className="optional">(optional)</span>
                </label>
                <input
                  id="guided-temperature-min"
                  inputMode="decimal"
                  value={form.temperatureMinC}
                  onChange={(event) => {
                    update("temperatureMinC", event.currentTarget.value);
                  }}
                />
              </div>
              <div className="field">
                <label htmlFor="guided-temperature-max">
                  Maximum °C <span className="optional">(optional)</span>
                </label>
                <input
                  id="guided-temperature-max"
                  inputMode="decimal"
                  value={form.temperatureMaxC}
                  onChange={(event) => {
                    update("temperatureMaxC", event.currentTarget.value);
                  }}
                />
              </div>
              <div className="field field--full">
                <label htmlFor="guided-notes">
                  Notes <span className="optional">(optional)</span>
                </label>
                <textarea
                  id="guided-notes"
                  value={form.notes}
                  onChange={(event) => {
                    update("notes", event.currentTarget.value);
                  }}
                />
              </div>
            </div>
            {messages.length > 0 && (
              <div className="notice notice--error" role="alert">
                <ul>
                  {messages.map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="actions">
              <button type="button" onClick={continueToUsage}>
                Continue to SeedLot usage
              </button>
              <a
                className="button-link button--secondary"
                href={`#/seeds/${lot.id}`}
              >
                Cancel
              </a>
            </div>
          </>
        ) : (
          <>
            <h3>Confirm SeedLot usage</h3>
            <p>
              Review the effect on the source before creating the Sowing.
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
                  : `${form.quantityApproximate ? "~" : ""}${form.quantityValue} ${form.quantityKind === "seed_count" ? "seeds" : form.quantityUnit}`}
              </p>
            </div>
            <fieldset className="choice-cards">
              <legend>How should the SeedLot change?</legend>
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
                        ? "Keep quantity unknown"
                        : sourceApproximate
                          ? "Set a resulting estimate"
                          : preview?.oversubscribed
                            ? "Subtract (not available)"
                            : `Subtract → ${String(preview?.suggested ?? "")} remaining`}
                    </strong>
                    <small>
                      {sourceApproximate
                        ? "The remainder remains an estimate and is editable."
                        : sourceUnknown
                          ? "No numeric amount will be invented."
                          : "Florabase calculates the exact remainder."}
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
                  <strong>Use all → SeedLot exhausted</strong>
                  <small>
                    {canUseAll
                      ? "The source becomes exhausted; approximate or unknown material is not rewritten as exact zero."
                      : "For exact compatible quantities, the Sowing amount must equal the source amount."}
                  </small>
                </span>
              </label>
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
                  <strong>Do not change SeedLot quantity</strong>
                  <small>
                    Creates the Sowing without adjusting the source.
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
                <p>
                  Suggested remainder: ~
                  {String(preview?.suggested ?? lot.quantity?.value)}
                </p>
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
                {pending ? "Creating Sowing…" : "Create Sowing"}
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
            </div>
          </>
        )}
      </form>
    </section>
  );
}
