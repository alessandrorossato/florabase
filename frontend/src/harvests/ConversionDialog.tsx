import { useEffect, useId, useRef, useState, type SyntheticEvent } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { TaskDialog } from "../components/TaskDialog";
import {
  listBotanicalIdentities,
  type BotanicalIdentityResponse,
} from "../botanical-identities/api";
import {
  listLocations,
  locationsForScope,
  type LocationResponse,
} from "../locations/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { formatPartialDate } from "../events/eventData";
import { getHarvest, type Harvest } from "./api";
import { QuantityFields } from "./InventoryDialog";
import {
  inventoryError,
  remainingLabel,
  type Inventory,
  type Quantity,
} from "./inventoryApi";
import {
  convertSeeds,
  type Conversion,
  type ConversionCreate,
} from "./conversionApi";

export function ConversionDialog({
  inventory,
  harvest: initialHarvest,
  onClose,
  onSaved,
}: {
  inventory: Inventory;
  harvest?: Harvest;
  onClose: () => void;
  onSaved: (conversion: Conversion) => void;
}) {
  const auth = useAuth();
  const id = useId();
  const alert = useRef<HTMLParagraphElement>(null);
  const [harvest, setHarvest] = useState(initialHarvest);
  const [choices, setChoices] = useState<{
    identities: BotanicalIdentityResponse[];
    locations: LocationResponse[];
  } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loadingError, setLoadingError] = useState(false);
  const [identity, setIdentity] = useState(
    inventory.source.botanical_identity.id,
  );
  const [location, setLocation] = useState(inventory.location?.id ?? "");
  const [label, setLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [mode, setMode] = useState<ConversionCreate["mode"]>("partial");
  const [quantity, setQuantity] = useState<Quantity | null>(
    inventory.quantity ? { ...inventory.quantity, value: "" } : null,
  );
  const [remainder, setRemainder] = useState<Quantity | null>(
    inventory.quantity?.is_approximate
      ? { ...inventory.quantity, value: "" }
      : null,
  );
  const [viability, setViability] =
    useState<ConversionCreate["expected_viability_until"]>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      listBotanicalIdentities(controller.signal),
      listLocations(controller.signal),
      initialHarvest
        ? Promise.resolve(initialHarvest)
        : getHarvest(inventory.harvest_id, controller.signal),
    ])
      .then(([identities, locations, currentHarvest]) => {
        if (controller.signal.aborted) return;
        setChoices({
          identities,
          locations: locationsForScope(locations, "seed_lots"),
        });
        setHarvest(currentHarvest);
        setLoadingError(false);
      })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) {
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setLoadingError(true);
        }
      });
    return () => {
      controller.abort();
    };
  }, [inventory.harvest_id, initialHarvest, attempt, auth]);
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      if (quantity?.unit === "kg")
        throw new Error(
          "Record a current measurement in g or mg first; units are not converted.",
        );
      const target: ConversionCreate["quantity"] = quantity
        ? {
            ...quantity,
            kind: quantity.kind === "item_count" ? "seed_count" : "weight",
            unit: quantity.unit as "mg" | "g" | null,
          }
        : null;
      const result = await convertSeeds(
        inventory.id,
        {
          mode,
          botanical_identity_id: identity,
          location_id: location || null,
          label: label.trim() || null,
          notes: notes.trim() || null,
          quantity: target,
          resulting_quantity: mode === "partial" ? remainder : null,
          expected_viability_until: viability,
        },
        auth.state.status === "authenticated" ? auth.state.csrfToken : "",
      );
      onSaved(result);
    } catch (failure: unknown) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else {
        setError(
          failure instanceof Error && !(failure instanceof ApiError)
            ? failure.message
            : inventoryError(failure),
        );
        requestAnimationFrame(() => alert.current?.focus());
      }
    } finally {
      setPending(false);
    }
  }
  const exact = Boolean(
    inventory.quantity && !inventory.quantity.is_approximate,
  );
  return (
    <TaskDialog
      title="Create Seed lot from stored seeds"
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <form
        className="record-form inventory-form"
        onSubmit={(e) => {
          void submit(e);
        }}
      >
        <h3>Create Seed lot from stored seeds</h3>
        <section aria-label="Source seed material">
          <h4>Source</h4>
          <p>{inventory.harvest_title}</p>
          <p>
            Producer:{" "}
            {inventory.source.type === "plant_group" ? "Plant group" : "Plant"}{" "}
            · {inventory.source.display_name}
          </p>
          <p>{inventory.source.botanical_identity.display_label}</p>
          <p>Remaining now: {remainingLabel(inventory)}</p>
          <p>Storage: {inventory.location?.display_path ?? "Not recorded"}</p>
          <p>
            Harvest date:{" "}
            {harvest ? formatPartialDate(harvest.occurred_on) : "Loading…"}
          </p>
        </section>
        <div className="field">
          <label htmlFor={`${id}-mode`}>Material leaving stock</label>
          <select
            id={`${id}-mode`}
            value={mode}
            disabled={pending}
            onChange={(e) => {
              const next = e.currentTarget.value as ConversionCreate["mode"];
              setMode(next);
              if (next === "use_all" && exact) setQuantity(inventory.quantity);
              else if (mode === "use_all" && exact)
                setQuantity(
                  inventory.quantity
                    ? { ...inventory.quantity, value: "" }
                    : null,
                );
            }}
          >
            <option value="partial">Partial amount</option>
            <option value="use_all">Use all remaining</option>
          </select>
        </div>
        <h4>Resulting Seed lot</h4>
        {choices ? (
          <>
            <ReferencePicker
              label="Botanical identity"
              choices={choices.identities.map((i) => ({
                id: i.id,
                label: i.display_label,
              }))}
              value={identity}
              onChange={setIdentity}
              disabled={pending}
              required
            />
            <ReferencePicker
              label="Seed lot Location"
              choices={choices.locations.map((l) => ({
                id: l.id,
                label: l.display_path,
                retired: Boolean(l.retired_at),
              }))}
              value={location}
              onChange={setLocation}
              disabled={pending}
              help="Confirm where the resulting Seed lot will be stored. Remaining source material stays in its current Location."
            />
            {location && (
              <button
                type="button"
                className="button--secondary"
                disabled={pending}
                onClick={() => {
                  setLocation("");
                }}
              >
                Clear Seed lot Location
              </button>
            )}
          </>
        ) : loadingError ? (
          <p role="alert">
            Could not load creation choices.{" "}
            <button
              type="button"
              onClick={() => {
                setAttempt((v) => v + 1);
              }}
            >
              Retry choices
            </button>
          </p>
        ) : (
          <p role="status">Loading creation choices…</p>
        )}
        <div className="field">
          <label htmlFor={`${id}-label`}>Seed lot label</label>
          <input
            id={`${id}-label`}
            value={label}
            maxLength={255}
            disabled={pending}
            onChange={(e) => {
              setLabel(e.currentTarget.value);
            }}
          />
        </div>
        <QuantityFields
          label="Seed lot quantity"
          value={quantity}
          onChange={setQuantity}
          disabled={pending || (mode === "use_all" && exact)}
          weightUnits={["mg", "g"]}
        />
        {mode === "partial" && inventory.quantity?.is_approximate && (
          <QuantityFields
            label="Confirmed remaining now"
            value={remainder}
            onChange={setRemainder}
            disabled={pending}
            approximateOnly
          />
        )}
        <PartialDateField
          id={`${id}-viability`}
          label="Expected viability until"
          value={viability ?? null}
          onChange={setViability}
          disabled={pending}
        />
        <div className="field">
          <label htmlFor={`${id}-notes`}>Seed lot notes</label>
          <textarea
            id={`${id}-notes`}
            value={notes}
            maxLength={20000}
            disabled={pending}
            onChange={(e) => {
              setNotes(e.currentTarget.value);
            }}
          />
        </div>
        <p role="status" className="field-help">
          {inventory.quantity?.unit === "kg" &&
            "Correct the current stock measurement to g or mg before creating a Seed lot. Units are not converted. "}
          {mode === "use_all"
            ? "All remaining source material will be depleted."
            : !inventory.quantity
              ? "The source remainder stays unknown."
              : inventory.quantity.is_approximate
                ? "Confirm the approximate source remainder; it is not calculated."
                : "The exact target amount will be subtracted from source stock."}{" "}
          One new collection-produced Seed lot will retain this exact producer.
          No Sowing or Event is created.
        </p>
        {error && (
          <p role="alert" ref={alert} tabIndex={-1}>
            {error}
          </p>
        )}
        <div className="actions">
          <button disabled={pending || !choices || !harvest || !identity}>
            {pending ? "Creating…" : "Create Seed lot"}
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
