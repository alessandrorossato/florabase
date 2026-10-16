import "./partial-date.css";
import { FieldLabel } from "../components/FieldLabel";
import type { PartialDate } from "./api";
import { FieldHelp } from "../components/ContextualHelp";

export function PartialDateField({
  id,
  label,
  value,
  onChange,
  disabled,
  showHelp = true,
  helpText,
}: {
  id: string;
  label: string;
  value: PartialDate | null;
  onChange: (value: PartialDate | null) => void;
  disabled: boolean;
  showHelp?: boolean;
  helpText?: string;
}) {
  const precision = value?.precision ?? "";
  const helpId = `${id}-precision-help`;
  function update(part: Partial<PartialDate>) {
    const nextPrecision = (part.precision ?? precision) as
      "year" | "month" | "day";
    onChange({
      precision: nextPrecision,
      year: part.year ?? value?.year ?? new Date().getFullYear(),
      ...(nextPrecision !== "year"
        ? { month: part.month ?? value?.month ?? 1 }
        : {}),
      ...(nextPrecision === "day" ? { day: part.day ?? value?.day ?? 1 } : {}),
    });
  }
  return (
    <fieldset className="partial-date partial-date--stacked">
      <legend>{label}</legend>
      <div className="field">
        <label htmlFor={`${id}-precision`}>Precision</label>
        <select
          aria-describedby={showHelp ? helpId : undefined}
          id={`${id}-precision`}
          disabled={disabled}
          value={precision}
          onChange={(event) => {
            const next = event.currentTarget.value;
            if (!next) onChange(null);
            else update({ precision: next as PartialDate["precision"] });
          }}
        >
          <option value="">Unknown</option>
          <option value="year">Year</option>
          <option value="month">Year and month</option>
          <option value="day">Complete date</option>
        </select>
        {showHelp && (
          <FieldHelp id={helpId}>
            {helpText ??
              "Choose only the precision you know; do not invent a missing month or day."}
          </FieldHelp>
        )}
      </div>
      {value && (
        <div className="partial-date-parts">
          <div className="field">
            <FieldLabel htmlFor={`${id}-year`} required>
              Year
            </FieldLabel>
            <input
              id={`${id}-year`}
              aria-required="true"
              type="number"
              min="1"
              max="9999"
              disabled={disabled}
              value={value.year}
              onChange={(event) => {
                update({ year: Number(event.currentTarget.value) });
              }}
            />
          </div>
          {value.precision !== "year" && (
            <div className="field">
              <FieldLabel htmlFor={`${id}-month`} required>
                Month
              </FieldLabel>
              <input
                id={`${id}-month`}
                aria-required="true"
                type="number"
                min="1"
                max="12"
                disabled={disabled}
                value={value.month ?? 1}
                onChange={(event) => {
                  update({ month: Number(event.currentTarget.value) });
                }}
              />
            </div>
          )}
          {value.precision === "day" && (
            <div className="field">
              <FieldLabel htmlFor={`${id}-day`} required>
                Day
              </FieldLabel>
              <input
                id={`${id}-day`}
                aria-required="true"
                type="number"
                min="1"
                max="31"
                disabled={disabled}
                value={value.day ?? 1}
                onChange={(event) => {
                  update({ day: Number(event.currentTarget.value) });
                }}
              />
            </div>
          )}
        </div>
      )}
    </fieldset>
  );
}
