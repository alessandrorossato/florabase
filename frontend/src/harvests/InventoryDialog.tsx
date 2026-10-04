import { useEffect, useId, useRef, useState, type SyntheticEvent } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { TaskDialog } from "../components/TaskDialog";
import {
  listLocations,
  locationsForScope,
  type LocationResponse,
} from "../locations/api";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { materials, quantityLabel, type HarvestItem } from "./api";
import {
  dispositionKinds,
  inventoryError,
  recordDisposition,
  remainingLabel,
  saveInventory,
  type DispositionCreate,
  type Inventory,
  type Quantity,
} from "./inventoryApi";

export function QuantityFields({
  label,
  value,
  onChange,
  disabled,
  approximateOnly = false,
}: {
  label: string;
  value: Quantity | null;
  onChange: (value: Quantity | null) => void;
  disabled: boolean;
  approximateOnly?: boolean;
}) {
  const id = useId();
  const precision = value
    ? value.is_approximate
      ? "approximate"
      : "exact"
    : "unknown";
  return (
    <fieldset disabled={disabled} className="inventory-quantity">
      <legend>{label}</legend>
      <div className="field">
        <label htmlFor={`${id}-precision`}>{label} precision</label>
        <select
          id={`${id}-precision`}
          value={precision}
          onChange={(event) => {
            const p = event.currentTarget.value;
            onChange(
              p === "unknown"
                ? null
                : {
                    ...(value ?? { kind: "item_count", value: "", unit: null }),
                    is_approximate: p === "approximate",
                  },
            );
          }}
        >
          {!approximateOnly && <option value="unknown">Unknown</option>}
          {!approximateOnly && <option value="exact">Exact</option>}
          <option value="approximate">Approximate</option>
        </select>
      </div>
      {value && (
        <div className="harvest-quantity-fields">
          <div className="field">
            <label htmlFor={`${id}-kind`}>{label} dimension</label>
            <select
              id={`${id}-kind`}
              value={value.kind}
              onChange={(event) => {
                const kind = event.currentTarget.value as Quantity["kind"];
                onChange({
                  ...value,
                  kind,
                  unit: kind === "weight" ? "g" : null,
                });
              }}
            >
              <option value="item_count">Item count</option>
              <option value="weight">Weight</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor={`${id}-amount`}>{label} amount</label>
            <input
              id={`${id}-amount`}
              inputMode="decimal"
              required
              pattern={
                value.kind === "item_count" ? "[0-9]+" : "[0-9]+(\\.[0-9]+)?"
              }
              value={value.value}
              onChange={(event) => {
                onChange({ ...value, value: event.currentTarget.value });
              }}
            />
          </div>
          {value.kind === "weight" && (
            <div className="field">
              <label htmlFor={`${id}-unit`}>{label} unit</label>
              <select
                id={`${id}-unit`}
                value={value.unit ?? "g"}
                onChange={(event) => {
                  onChange({
                    ...value,
                    unit: event.currentTarget.value as Quantity["unit"],
                  });
                }}
              >
                {["mg", "g", "kg"].map((unit) => (
                  <option key={unit}>{unit}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}
    </fieldset>
  );
}

export function InventoryDialog({
  item,
  inventory,
  disposition = false,
  onClose,
  onSaved,
}: {
  item: HarvestItem;
  inventory?: Inventory;
  disposition?: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const auth = useAuth();
  const id = useId();
  const alert = useRef<HTMLParagraphElement>(null);
  const [quantity, setQuantity] = useState<Quantity | null>(
    inventory ? inventory.quantity : (item.quantity ?? null),
  );
  const [state, setState] = useState<Inventory["state"]>(
    inventory?.state ?? "active",
  );
  const [location, setLocation] = useState(inventory?.location?.id ?? "");
  const [locations, setLocations] = useState<LocationResponse[] | null>(null);
  const [locationsError, setLocationsError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [kind, setKind] = useState<DispositionCreate["kind"]>("consumed");
  const [mode, setMode] = useState<DispositionCreate["mode"]>("partial");
  const [used, setUsed] = useState<Quantity | null>(
    inventory?.quantity ? { ...inventory.quantity, value: "" } : null,
  );
  const [result, setResult] = useState<Quantity | null>(
    inventory?.quantity?.is_approximate
      ? { ...inventory.quantity, value: "" }
      : null,
  );
  const [date, setDate] = useState<DispositionCreate["occurred_on"]>(null);
  const [notes, setNotes] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const title = disposition
    ? "Record disposition"
    : inventory
      ? "Edit stored material"
      : "Track stored material";
  useEffect(() => {
    if (disposition) return;
    const controller = new AbortController();
    void listLocations(controller.signal)
      .then((rows) => {
        if (!controller.signal.aborted) {
          setLocations(locationsForScope(rows, "harvest_inventory"));
          setLocationsError(false);
        }
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) {
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setLocationsError(true);
        }
      });
    return () => {
      controller.abort();
    };
  }, [disposition, attempt, auth]);
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    const token =
      auth.state.status === "authenticated" ? auth.state.csrfToken : "";
    try {
      if (disposition && inventory)
        await recordDisposition(
          inventory.id,
          {
            kind,
            mode,
            quantity: mode === "partial" ? used : null,
            resulting_quantity: mode === "partial" ? result : null,
            occurred_on: date,
            notes: notes.trim() || null,
          },
          token,
        );
      else
        await saveInventory(
          item.id ?? "",
          inventory?.id,
          {
            state,
            quantity: state === "active" ? quantity : null,
            location_id: location || null,
          },
          token,
        );
      onSaved();
    } catch (failure: unknown) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else {
        setError(inventoryError(failure));
        requestAnimationFrame(() => alert.current?.focus());
      }
    } finally {
      setPending(false);
    }
  }
  return (
    <TaskDialog
      title={title}
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <form
        onSubmit={(event) => {
          void submit(event);
        }}
        className="record-form inventory-form"
      >
        <h3>{title}</h3>
        <p>
          {materials.find((m) => m.id === item.material_kind)?.label}
          {item.description ? ` · ${item.description}` : ""}
        </p>
        <p>
          <strong>Collected:</strong> {quantityLabel(item)}
        </p>
        {inventory && (
          <p>
            <strong>Remaining now:</strong> {remainingLabel(inventory)}
          </p>
        )}
        {disposition ? (
          <>
            <div className="field">
              <label htmlFor={`${id}-kind`}>Disposition</label>
              <select
                id={`${id}-kind`}
                disabled={pending}
                value={kind}
                onChange={(event) => {
                  setKind(
                    event.currentTarget.value as DispositionCreate["kind"],
                  );
                }}
              >
                {dispositionKinds.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor={`${id}-mode`}>Material leaving stock</label>
              <select
                id={`${id}-mode`}
                disabled={pending}
                value={mode}
                onChange={(event) => {
                  setMode(
                    event.currentTarget.value as DispositionCreate["mode"],
                  );
                }}
              >
                <option value="partial">Partial amount</option>
                <option value="use_all">Use all remaining</option>
              </select>
            </div>
            {mode === "partial" && (
              <>
                <QuantityFields
                  label="Amount used"
                  value={used}
                  onChange={setUsed}
                  disabled={pending}
                />
                {inventory?.quantity?.is_approximate && (
                  <QuantityFields
                    label="Confirmed remaining now"
                    value={result}
                    onChange={setResult}
                    disabled={pending}
                    approximateOnly
                  />
                )}
              </>
            )}
            <p className="field-help" role="status">
              {mode === "use_all"
                ? "This marks stored material depleted; no material will remain held."
                : !inventory?.quantity
                  ? "Remaining quantity stays unknown."
                  : inventory.quantity.is_approximate
                    ? "Confirm the approximate balance that remains now. It is not calculated from an estimate."
                    : "The exact amount used will be subtracted from the current exact balance. Use all remaining for the whole balance."}
            </p>
            <PartialDateField
              id={`${id}-date`}
              label="Disposition date"
              value={date ?? null}
              onChange={setDate}
              disabled={pending}
            />
            <div className="field">
              <label htmlFor={`${id}-notes`}>Notes</label>
              <textarea
                id={`${id}-notes`}
                maxLength={20000}
                disabled={pending}
                value={notes}
                onChange={(event) => {
                  setNotes(event.currentTarget.value);
                }}
              />
            </div>
            {kind === "used_for_propagation" && (
              <p className="field-help">
                Records material leaving this stock for propagation. No new
                collection record is created.
              </p>
            )}
          </>
        ) : (
          <>
            <p className="field-help">
              {inventory
                ? "Correct current stored material. Retained dispositions and collected quantities stay as recorded."
                : "Confirm what remains now. Some material may already have been used before tracking began."}
            </p>
            {inventory && (
              <div className="field">
                <label htmlFor={`${id}-state`}>Inventory state</label>
                <select
                  id={`${id}-state`}
                  value={state}
                  disabled={pending}
                  onChange={(event) => {
                    setState(event.currentTarget.value as Inventory["state"]);
                  }}
                >
                  <option value="active">Active — material held</option>
                  <option value="depleted">Depleted — no material held</option>
                </select>
              </div>
            )}
            {state === "active" && (
              <QuantityFields
                label="Remaining now"
                value={quantity}
                onChange={setQuantity}
                disabled={pending}
              />
            )}
            {locations ? (
              <ReferencePicker
                label="Storage Location"
                choices={locations.map((l) => ({
                  id: l.id,
                  label: l.display_path,
                  retired: Boolean(l.retired_at),
                }))}
                value={location}
                onChange={setLocation}
                disabled={pending}
                help="Where this material is stored now. Enable the Stored material scope on a Location to use it here."
              />
            ) : locationsError ? (
              <p role="alert">
                Could not load storage Locations.{" "}
                <button
                  type="button"
                  onClick={() => {
                    setAttempt((v) => v + 1);
                  }}
                >
                  Retry Locations
                </button>
              </p>
            ) : (
              <p role="status">Loading storage Locations…</p>
            )}
            {location && (
              <button
                type="button"
                className="button--secondary"
                disabled={pending}
                onClick={() => {
                  setLocation("");
                }}
              >
                Clear storage Location
              </button>
            )}
          </>
        )}
        {error && (
          <p role="alert" tabIndex={-1} ref={alert}>
            {error}
          </p>
        )}
        <div className="actions">
          <button disabled={pending || (!disposition && !locations)}>
            {pending ? "Saving…" : title}
          </button>
          <button
            type="button"
            className="button--secondary"
            disabled={pending}
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
      </form>
    </TaskDialog>
  );
}
