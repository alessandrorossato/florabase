import { FieldLabel } from "../components/FieldLabel";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import { FieldHelp } from "../components/ContextualHelp";
import { locationsForScope, type LocationResponse } from "../locations/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import type { PartialDate } from "./api";
export interface PlantFieldsState {
  label: string;
  locationId: string;
  quantityKind: "unknown" | "exact" | "approximate";
  quantityValue: string;
  collectionEntryDate: PartialDate | null;
  notes: string;
}
type QuantityKind = PlantFieldsState["quantityKind"];
interface FieldProps {
  form: PlantFieldsState;
  pending: boolean;
  updateForm: <K extends keyof PlantFieldsState>(
    key: K,
    value: PlantFieldsState[K],
  ) => void;
}
export function PlantEssentialsFields({
  form,
  pending,
  updateForm,
  locations,
  kind,
}: FieldProps & { locations: LocationResponse[]; kind: "plant" | "group" }) {
  return (
    <>
      <div className="field">
        <label htmlFor="plant-label">Label</label>
        <input
          id="plant-label"
          value={form.label}
          disabled={pending}
          onChange={(event) => {
            updateForm("label", event.currentTarget.value);
          }}
        />
      </div>
      {kind === "group" && (
        <fieldset
          aria-describedby="plant-group-quantity-help"
          className="quantity-field"
        >
          <legend>Quantity</legend>
          <div className="field">
            <label className="sr-only" htmlFor="plant-quantity-kind">
              Quantity kind
            </label>
            <select
              id="plant-quantity-kind"
              value={form.quantityKind}
              disabled={pending}
              onChange={(event) => {
                const quantityKind = event.currentTarget.value as QuantityKind;
                updateForm("quantityKind", quantityKind);
                if (quantityKind === "unknown") updateForm("quantityValue", "");
              }}
            >
              <option value="unknown">Unknown</option>
              <option value="exact">Exact count</option>
              <option value="approximate">Approximate count</option>
            </select>
          </div>
          {form.quantityKind !== "unknown" && (
            <div className="field">
              <FieldLabel htmlFor="plant-quantity-value" required>
                Count
              </FieldLabel>
              <input
                id="plant-quantity-value"
                aria-required="true"
                inputMode="numeric"
                value={form.quantityValue}
                disabled={pending}
                onChange={(event) => {
                  updateForm("quantityValue", event.currentTarget.value);
                }}
              />
            </div>
          )}
          <FieldHelp id="plant-group-quantity-help">
            Choose Exact only for a known count, Approximate for an estimate, or
            Unknown rather than guessing.
          </FieldHelp>
        </fieldset>
      )}
      <ReferencePicker
        id="plant-location"
        label="Current location"
        help="Current collection position; record movements in Journal to keep their history."
        placeholder="Not recorded"
        disabled={pending}
        choices={locationsForScope(locations, "plants").map((location) => ({
          id: location.id,
          label: location.display_path,
          retired: Boolean(location.retired_at),
        }))}
        value={form.locationId}
        onChange={(id) => {
          updateForm("locationId", id);
        }}
      />
    </>
  );
}
export function PlantEntryDateField({ form, pending, updateForm }: FieldProps) {
  return (
    <PartialDateField
      id="plant-entry-date"
      label="Collection-entry date"
      hidePrecisionLabel
      value={form.collectionEntryDate}
      disabled={pending}
      onChange={(value) => {
        updateForm("collectionEntryDate", value);
      }}
    />
  );
}
export function PlantNotesField({ form, pending, updateForm }: FieldProps) {
  return (
    <div className="field field--full">
      <label htmlFor="plant-notes">Notes</label>
      <textarea
        id="plant-notes"
        value={form.notes}
        disabled={pending}
        onChange={(event) => {
          updateForm("notes", event.currentTarget.value);
        }}
      />
    </div>
  );
}
