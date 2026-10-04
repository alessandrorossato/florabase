import { useEffect, useId, useRef, useState, type SyntheticEvent } from "react";
import { inventoryError } from "./inventoryApi";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { FormActions } from "../components/ReferenceUI";
import { TaskDialog } from "../components/TaskDialog";
import { listPlants, listPlantGroups } from "../plants/api";
import { useRecordName } from "../components/recordPresentation";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import {
  saveHarvest,
  materials,
  type Harvest,
  type HarvestWrite,
  type HarvestItem,
} from "./api";

type Line = HarvestItem & { key: number };
export function HarvestForm({
  harvest,
  sourceType = "plant",
  sourceId = "",
  onClose,
  onSaved,
}: {
  harvest?: Harvest;
  sourceType?: "plant" | "plant_group";
  sourceId?: string;
  onClose: () => void;
  onSaved: (harvest: Harvest) => void;
}) {
  const auth = useAuth();
  const name = useRecordName();
  const id = useId();
  const nextKey = useRef(harvest?.items.length ?? 1);
  const [type, setType] = useState(harvest?.source.type ?? sourceType);
  const [source, setSource] = useState(harvest?.source.id ?? sourceId);
  const [choices, setChoices] = useState<
    { id: string; label: string }[] | null
  >(null);
  const [date, setDate] = useState(harvest?.occurred_on ?? null);
  const [label, setLabel] = useState(harvest?.label ?? "");
  const [notes, setNotes] = useState(harvest?.notes ?? "");
  const [lines, setLines] = useState<Line[]>(
    harvest?.items.map((item, key) => ({ ...item, key })) ?? [
      { key: 0, material_kind: "fruit", quantity: null },
    ],
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const formRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    void (
      type === "plant"
        ? listPlants(controller.signal)
        : listPlantGroups(controller.signal)
    )
      .then((records) => {
        if (controller.signal.aborted) return;
        setChoices(
          records.map((record) => ({
            id: record.id,
            label: `${name(record, type === "plant" ? "Plant" : "Plant group")} · ${record.lifecycle}${record.label ? ` · ${record.botanical_identity.display_label}` : ""} · ${record.id.slice(-8)}`,
          })),
        );
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else
          setError("Could not load Harvest sources. Retry to choose a source.");
      });
    return () => {
      controller.abort();
    };
    // Source naming uses the shell's already-published identity context.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, attempt]);
  function update(key: number, part: Partial<Line>) {
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, ...part } : line)),
    );
  }
  function updateQuantity(
    key: number,
    part: Partial<NonNullable<HarvestItem["quantity"]>>,
  ) {
    setLines((current) =>
      current.map((line) =>
        line.key === key && line.quantity
          ? { ...line, quantity: { ...line.quantity, ...part } }
          : line,
      ),
    );
  }
  function focusLine(key: number) {
    requestAnimationFrame(() => {
      document.getElementById(`${id}-material-${String(key)}`)?.focus();
    });
  }
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!source) {
      setError("Choose a source Plant or Plant group.");
      return;
    }
    setPending(true);
    setError(null);
    const payload: HarvestWrite = {
      plant_id: type === "plant" ? source : null,
      plant_group_id: type === "plant_group" ? source : null,
      label: label.trim() || null,
      notes: notes.trim() || null,
      occurred_on: date,
      items: lines.map((item) => ({
        id: item.id,
        material_kind: item.material_kind,
        description: (item.description ?? "").trim() || null,
        quantity: item.quantity,
      })),
    };
    try {
      const token =
        auth.state.status === "authenticated" ? auth.state.csrfToken : "";
      onSaved(await saveHarvest(harvest?.id ?? null, payload, token));
    } catch (failure: unknown) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else {
        const detail =
          failure instanceof ApiError
            ? (failure.body as { detail?: unknown } | undefined)?.detail
            : undefined;
        const problems = Array.isArray(detail)
          ? (detail as { loc?: (string | number)[]; msg?: string }[])
          : [];
        const problem = problems.find((p) => p.loc?.includes("items"));
        const index = problem?.loc?.find((part) => typeof part === "number");
        setError(
          typeof index === "number"
            ? `Material line ${String(index + 1)}: ${problem?.msg ?? "check quantity and description"}`
            : failure instanceof ApiError && failure.status === 409
              ? inventoryError(failure)
              : "Could not save the Harvest. Check the source, date and material quantities, then try again.",
        );
        if (typeof index === "number" && lines[index])
          focusLine(lines[index].key);
        else formRef.current?.querySelector<HTMLInputElement>("input")?.focus();
      }
    } finally {
      setPending(false);
    }
  }
  return (
    <TaskDialog
      title={harvest ? "Edit harvest" : "Record harvest"}
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <form
        className="harvest-form"
        onSubmit={(event) => {
          void submit(event);
        }}
        ref={formRef}
      >
        <h3>{harvest ? "Edit harvest" : "Record harvest"}</h3>
        <p>
          Record what was collected. Source lifecycle, quantity and seed
          inventory stay unchanged.
        </p>
        {error && (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        )}
        <div className="form-grid">
          <div className="field">
            <label htmlFor={`${id}-source-type`}>Source type</label>
            <select
              id={`${id}-source-type`}
              value={type}
              disabled={pending}
              onChange={(event) => {
                setChoices(null);
                setError(null);
                setType(event.currentTarget.value as typeof type);
                setSource("");
              }}
            >
              <option value="plant">Plant</option>
              <option value="plant_group">Plant group</option>
            </select>
          </div>
          {choices ? (
            <ReferencePicker
              key={type}
              label="Harvest source"
              choices={choices}
              required
              value={source}
              disabled={pending}
              onChange={setSource}
            />
          ) : (
            <div role="status">
              Loading sources…{" "}
              {error && (
                <button
                  type="button"
                  className="button--secondary"
                  onClick={() => {
                    setError(null);
                    setAttempt((value) => value + 1);
                  }}
                >
                  Retry
                </button>
              )}
            </div>
          )}
        </div>
        <PartialDateField
          id={`${id}-date`}
          label="Harvest date"
          showHelp={false}
          value={date}
          disabled={pending}
          onChange={setDate}
        />
        <section aria-label="Harvest materials">
          <h4>Harvested materials</h4>
          {lines.map((line, index) => (
            <fieldset
              className="harvest-line"
              key={line.key}
              disabled={pending}
            >
              <legend>Material line {index + 1}</legend>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor={`${id}-material-${String(line.key)}`}>
                    Material {index + 1}
                  </label>
                  <select
                    id={`${id}-material-${String(line.key)}`}
                    value={line.material_kind}
                    onChange={(event) => {
                      update(line.key, {
                        material_kind: event.currentTarget
                          .value as Line["material_kind"],
                      });
                    }}
                  >
                    {materials.map((material) => (
                      <option key={material.id} value={material.id}>
                        {material.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor={`${id}-quantity-kind-${String(line.key)}`}>
                    Quantity type {index + 1}
                  </label>
                  <select
                    id={`${id}-quantity-kind-${String(line.key)}`}
                    value={line.quantity?.kind ?? ""}
                    onChange={(event) => {
                      const kind = event.currentTarget.value;
                      update(line.key, {
                        quantity: kind
                          ? {
                              kind: kind as "weight" | "item_count",
                              value: "1",
                              is_approximate: false,
                              unit: kind === "weight" ? "g" : null,
                            }
                          : null,
                      });
                    }}
                  >
                    <option value="">Not recorded</option>
                    <option value="item_count">Item count</option>
                    <option value="weight">Weight</option>
                  </select>
                </div>
                {line.quantity && (
                  <>
                    <div className="field">
                      <label htmlFor={`${id}-quantity-${String(line.key)}`}>
                        Quantity {index + 1}
                      </label>
                      <input
                        id={`${id}-quantity-${String(line.key)}`}
                        type="number"
                        inputMode="decimal"
                        required
                        min={line.quantity.kind === "item_count" ? "1" : "0"}
                        step={line.quantity.kind === "item_count" ? "1" : "any"}
                        value={line.quantity.value}
                        onChange={(event) => {
                          updateQuantity(line.key, {
                            value: event.currentTarget.value,
                          });
                        }}
                      />
                    </div>
                    {line.quantity.kind === "weight" && (
                      <div className="field">
                        <label htmlFor={`${id}-unit-${String(line.key)}`}>
                          Weight unit {index + 1}
                        </label>
                        <select
                          id={`${id}-unit-${String(line.key)}`}
                          value={line.quantity.unit ?? "g"}
                          onChange={(event) => {
                            updateQuantity(line.key, {
                              unit: event.currentTarget.value as
                                "mg" | "g" | "kg",
                            });
                          }}
                        >
                          <option value="mg">mg</option>
                          <option value="g">g</option>
                          <option value="kg">kg</option>
                        </select>
                      </div>
                    )}
                    <div className="field">
                      <label htmlFor={`${id}-approx-${String(line.key)}`}>
                        Quantity precision {index + 1}
                      </label>
                      <select
                        id={`${id}-approx-${String(line.key)}`}
                        value={
                          line.quantity.is_approximate ? "approximate" : "exact"
                        }
                        onChange={(event) => {
                          updateQuantity(line.key, {
                            is_approximate:
                              event.currentTarget.value === "approximate",
                          });
                        }}
                      >
                        <option value="exact">Exact</option>
                        <option value="approximate">Approximate</option>
                      </select>
                    </div>
                  </>
                )}
                <div className="field">
                  <label htmlFor={`${id}-description-${String(line.key)}`}>
                    Description {index + 1} (optional)
                  </label>
                  <textarea
                    rows={2}
                    id={`${id}-description-${String(line.key)}`}
                    maxLength={2000}
                    value={line.description ?? ""}
                    onChange={(event) => {
                      update(line.key, {
                        description: event.currentTarget.value,
                      });
                    }}
                  />
                </div>
              </div>
              <button
                className="button--secondary"
                type="button"
                disabled={lines.length === 1}
                aria-label={`Remove material line ${String(index + 1)}`}
                onClick={() => {
                  setLines((current) =>
                    current.filter((item) => item.key !== line.key),
                  );
                  focusLine(lines[index + 1]?.key ?? lines[index - 1].key);
                }}
              >
                Remove line
              </button>
            </fieldset>
          ))}
          <button
            type="button"
            className="button--secondary"
            disabled={pending || lines.length >= 100}
            onClick={() => {
              const key = nextKey.current++;
              setLines((current) => [
                ...current,
                { key, material_kind: "fruit", quantity: null },
              ]);
              focusLine(key);
            }}
          >
            Add material line
          </button>
        </section>
        <div className="field">
          <label htmlFor={`${id}-label`}>Label (optional)</label>
          <input
            id={`${id}-label`}
            value={label}
            maxLength={255}
            disabled={pending}
            onChange={(event) => {
              setLabel(event.currentTarget.value);
            }}
          />
          <small>
            Without a label, the title uses the source and harvested materials.
          </small>
        </div>
        <div className="field">
          <label htmlFor={`${id}-notes`}>Notes</label>
          <textarea
            id={`${id}-notes`}
            value={notes}
            maxLength={20000}
            disabled={pending}
            onChange={(event) => {
              setNotes(event.currentTarget.value);
            }}
          />
        </div>
        <FormActions>
          <button type="submit" disabled={pending || !choices}>
            {pending ? "Saving…" : "Save harvest"}
          </button>
          <button
            type="button"
            className="button--secondary"
            disabled={pending}
            onClick={onClose}
          >
            Cancel
          </button>
        </FormActions>
      </form>
    </TaskDialog>
  );
}
