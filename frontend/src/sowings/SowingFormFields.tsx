import type { ReactNode } from "react";
import type { FormPanel } from "../components/FormSections";
import { FieldHelp } from "../components/ContextualHelp";
import { locationsForScope, type LocationResponse } from "../locations/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import type { PartialDate } from "./api";

type QuantityKind = "unknown" | "seed_count" | "weight";
export interface SowingFieldsState {
  label: string;
  sowingDate: PartialDate | null;
  quantityKind: QuantityKind;
  quantityValue: string;
  quantityUnit: "g" | "mg";
  quantityApproximate: boolean;
  locationId: string;
  substrate: string;
  methodContainer: string;
  pretreatment: string;
  temperatureMinC: string;
  temperatureMaxC: string;
  environment: string;
  notes: string;
}
export const sowingErrorFields = [
  { match: /quantity|seed count/i, selector: "#sowing-quantity-value" },
  { match: /maximum|temperature max/i, selector: "#temperature-max" },
  { match: /minimum|temperature/i, selector: "#temperature-min" },
  { match: /notes/i, selector: "#sowing-notes" },
  { match: /substrate/i, selector: "#sowing-substrate" },
  { match: /environment/i, selector: "#sowing-environment" },
  { match: /location/i, selector: "#sowing-location" },
  { match: /label/i, selector: "#sowing-label" },
  { match: /method/i, selector: "#sowing-method" },
  { match: /pretreatment/i, selector: "#sowing-pretreatment" },
  { match: /sowing date/i, selector: "#sowing-date-precision" },
];
export function sowingFormPanels({
  form,
  updateForm,
  locations,
  pending,
  source,
  outcome,
}: {
  form: SowingFieldsState;
  updateForm: <K extends keyof SowingFieldsState>(
    key: K,
    value: SowingFieldsState[K],
  ) => void;
  locations: LocationResponse[];
  pending: boolean;
  source: ReactNode;
  outcome?: ReactNode;
}): FormPanel[] {
  return [
    {
      id: "essentials",
      label: "Essentials",
      content: (
        <>
          {source}
          <div className="field">
            <label htmlFor="sowing-label">
              Sowing label <span className="optional">(optional)</span>
            </label>
            <input
              id="sowing-label"
              value={form.label}
              disabled={pending}
              onChange={(event) => {
                updateForm("label", event.currentTarget.value);
              }}
            />
          </div>
          <PartialDateField
            id="sowing-date"
            label="Sowing date (optional)"
            value={form.sowingDate}
            disabled={pending}
            onChange={(value) => {
              updateForm("sowingDate", value);
            }}
          />
        </>
      ),
    },
    {
      id: "material",
      label: "Material & location",
      content: (
        <>
          <fieldset
            aria-describedby="sowing-quantity-help"
            className="quantity-field"
          >
            <legend>
              Quantity sown <span className="optional">(optional)</span>
            </legend>
            <div className="field">
              <label htmlFor="sowing-quantity-kind">Kind</label>
              <select
                id="sowing-quantity-kind"
                value={form.quantityKind}
                disabled={pending}
                onChange={(event) => {
                  const quantityKind = event.currentTarget
                    .value as QuantityKind;
                  updateForm("quantityKind", quantityKind);
                  if (quantityKind === "unknown")
                    updateForm("quantityValue", "");
                }}
              >
                <option value="unknown">Unknown</option>
                <option value="seed_count">Seed count</option>
                <option value="weight">Weight</option>
              </select>
            </div>
            {form.quantityKind !== "unknown" && (
              <div className="quantity-controls sowing-quantity-controls">
                <div className="field">
                  <label htmlFor="sowing-quantity-value">Amount</label>
                  <input
                    id="sowing-quantity-value"
                    inputMode="decimal"
                    value={form.quantityValue}
                    disabled={pending}
                    onChange={(event) => {
                      updateForm("quantityValue", event.currentTarget.value);
                    }}
                  />
                </div>
                {form.quantityKind === "weight" && (
                  <div className="field">
                    <label htmlFor="sowing-quantity-unit">Unit</label>
                    <select
                      id="sowing-quantity-unit"
                      value={form.quantityUnit}
                      disabled={pending}
                      onChange={(event) => {
                        updateForm(
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
                    disabled={pending}
                    onChange={(event) => {
                      updateForm(
                        "quantityApproximate",
                        event.currentTarget.checked,
                      );
                    }}
                  />
                  Approximate
                </label>
              </div>
            )}
            <FieldHelp id="sowing-quantity-help">
              Keep count and weight as distinct measurements. Mark an estimate
              as approximate, or leave the quantity unknown rather than
              guessing.
            </FieldHelp>
          </fieldset>

          <div className="field">
            <label htmlFor="sowing-location">
              Current location <span className="optional">(optional)</span>
            </label>
            <select
              aria-describedby="sowing-location-help"
              id="sowing-location"
              value={form.locationId}
              disabled={pending}
              onChange={(event) => {
                updateForm("locationId", event.currentTarget.value);
              }}
            >
              <option value="">Not recorded</option>
              {locationsForScope(locations, "sowings").map((location) => (
                <option
                  key={location.id}
                  value={location.id}
                  disabled={
                    Boolean(location.retired_at) &&
                    location.id !== form.locationId
                  }
                >
                  {location.display_path}
                  {location.retired_at ? " (retired)" : ""}
                </option>
              ))}
            </select>
            <FieldHelp id="sowing-location-help">
              Where this Sowing is currently kept in your collection, not where
              its biological material originated.
            </FieldHelp>
          </div>
        </>
      ),
    },
    ...(outcome
      ? [{ id: "outcome", label: "Outcome & status", content: outcome }]
      : []),
    {
      id: "cultivation",
      label: "Cultivation",
      content: (
        <>
          <div className="field">
            <label htmlFor="sowing-substrate">
              Substrate <span className="optional">(optional)</span>
            </label>
            <input
              id="sowing-substrate"
              value={form.substrate}
              disabled={pending}
              onChange={(event) => {
                updateForm("substrate", event.currentTarget.value);
              }}
            />
          </div>
          <div className="field">
            <label htmlFor="sowing-method">
              Method / container <span className="optional">(optional)</span>
            </label>
            <input
              id="sowing-method"
              value={form.methodContainer}
              disabled={pending}
              onChange={(event) => {
                updateForm("methodContainer", event.currentTarget.value);
              }}
            />
          </div>
          <div className="field">
            <label htmlFor="sowing-pretreatment">
              Pretreatment <span className="optional">(optional)</span>
            </label>
            <input
              id="sowing-pretreatment"
              value={form.pretreatment}
              disabled={pending}
              onChange={(event) => {
                updateForm("pretreatment", event.currentTarget.value);
              }}
            />
          </div>
          <fieldset className="temperature-field">
            <legend>
              Temperature <span className="optional">(optional, °C)</span>
            </legend>
            <div className="temperature-controls">
              <div className="field">
                <label htmlFor="temperature-min">Minimum °C</label>
                <input
                  id="temperature-min"
                  inputMode="decimal"
                  value={form.temperatureMinC}
                  disabled={pending}
                  onChange={(event) => {
                    updateForm("temperatureMinC", event.currentTarget.value);
                  }}
                />
              </div>
              <div className="field">
                <label htmlFor="temperature-max">Maximum °C</label>
                <input
                  id="temperature-max"
                  inputMode="decimal"
                  value={form.temperatureMaxC}
                  disabled={pending}
                  onChange={(event) => {
                    updateForm("temperatureMaxC", event.currentTarget.value);
                  }}
                />
              </div>
            </div>
          </fieldset>
          <div className="field field--full">
            <label htmlFor="sowing-environment">
              Environment / conditions{" "}
              <span className="optional">(optional)</span>
            </label>
            <textarea
              id="sowing-environment"
              value={form.environment}
              disabled={pending}
              onChange={(event) => {
                updateForm("environment", event.currentTarget.value);
              }}
            />
          </div>
        </>
      ),
    },
    {
      id: "notes",
      label: "Notes",
      content: (
        <>
          <div className="field field--full">
            <label htmlFor="sowing-notes">
              Notes <span className="optional">(optional)</span>
            </label>
            <textarea
              id="sowing-notes"
              value={form.notes}
              disabled={pending}
              onChange={(event) => {
                updateForm("notes", event.currentTarget.value);
              }}
            />
          </div>
        </>
      ),
    },
  ];
}
