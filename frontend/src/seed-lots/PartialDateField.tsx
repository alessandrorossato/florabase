import type { PartialDate } from "./api";

export function PartialDateField({
  id,
  label,
  value,
  onChange,
  disabled,
}: {
  id: string;
  label: string;
  value: PartialDate | null;
  onChange: (value: PartialDate | null) => void;
  disabled: boolean;
}) {
  const precision = value?.precision ?? "";
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
    <fieldset className="partial-date">
      <legend>{label}</legend>
      <div className="field">
        <label htmlFor={`${id}-precision`}>Precision</label>
        <select
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
      </div>
      {value && (
        <div className="partial-date-parts">
          <div className="field">
            <label htmlFor={`${id}-year`}>Year</label>
            <input
              id={`${id}-year`}
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
              <label htmlFor={`${id}-month`}>Month</label>
              <input
                id={`${id}-month`}
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
              <label htmlFor={`${id}-day`}>Day</label>
              <input
                id={`${id}-day`}
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
