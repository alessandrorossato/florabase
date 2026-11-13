import { useEffect, useRef, useState } from "react";
import { FieldLabel } from "../components/FieldLabel";
import { localDay } from "../schedule/calendar";
import { PartialDateField } from "../seed-lots/PartialDateField";
import type { PartialDate } from "../seed-lots/api";

export type DateChoice = "unset" | "today" | "other" | "unknown";

function dayValue(day: string): PartialDate {
  const [year, month, date] = day.split("-").map(Number);
  return { precision: "day", year, month, day: date };
}

/**
 * Explicit occurrence date: Today, Another date or Date unknown. `onChange` receives a
 * complete PartialDate or null; while nothing is chosen (or Another date is incomplete)
 * the first invalid control carries the reason, see `invalidDateControls`.
 */
export function OccurrenceDateChoice({
  id,
  value,
  onChange,
  disabled,
  initialChoice = "unset",
  unknownUnavailable,
}: {
  id: string;
  value: PartialDate | null;
  onChange: (value: PartialDate | null) => void;
  disabled: boolean;
  /** Choice for a new entry (design decision D1). A stored date always opens as Another date. */
  initialChoice?: DateChoice;
  /** Why this entry needs a date; when set, Date unknown cannot be chosen. */
  unknownUnavailable?: string;
}) {
  // Read once: the day shown is the day recorded, even if the dialog stays open past midnight.
  const [today] = useState(() => localDay());
  const [chosen, setChosen] = useState<DateChoice>(() =>
    value ? "other" : initialChoice,
  );
  const choice = chosen === "unknown" && unknownUnavailable ? "unset" : chosen;
  const first = useRef<HTMLInputElement>(null);
  useEffect(() => {
    first.current?.setCustomValidity(
      choice === "unset"
        ? `Choose when this happened: Today${unknownUnavailable ? " or Another date" : ", Another date or Date unknown"}.`
        : "",
    );
  }, [choice, unknownUnavailable]);
  useEffect(() => {
    // Only reached when Today is the initial choice; a click records it directly.
    if (choice === "today" && !value) onChange(dayValue(today));
  }, [choice, value, onChange, today]);

  function choose(next: DateChoice) {
    setChosen(next);
    onChange(next === "today" ? dayValue(today) : null);
  }
  const reasonId = `${id}-unknown-reason`;
  const option = (
    name: DateChoice,
    label: string,
    extra?: { ref?: typeof first; reason?: boolean },
  ) => (
    <label className="checkbox-label">
      <input
        ref={extra?.ref}
        type="radio"
        name={`${id}-choice`}
        data-date-control="choice"
        aria-describedby={extra?.reason ? reasonId : undefined}
        checked={choice === name}
        disabled={disabled || extra?.reason}
        onChange={() => {
          choose(name);
        }}
      />
      {label}
    </label>
  );
  return (
    <fieldset className="partial-date partial-date--stacked">
      <FieldLabel as="legend" required>
        When did it happen?
      </FieldLabel>
      <div className="occurrence-date-choices">
        {option("today", `Today, ${today}`, { ref: first })}
        {option("other", "Another date")}
        {option("unknown", "Date unknown", {
          reason: Boolean(unknownUnavailable),
        })}
      </div>
      {unknownUnavailable && (
        <p className="field-help" id={reasonId}>
          {unknownUnavailable}
        </p>
      )}
      {choice === "unset" && (
        <p className="field-help">
          Choose one. Florabase never fills in a date you did not give.
        </p>
      )}
      {choice === "today" && (
        <p className="field-help">
          Today is your device’s calendar day, recorded as a complete date.
        </p>
      )}
      {choice === "other" && (
        <PartialDateField
          id={id}
          label="Occurrence date"
          value={value}
          disabled={disabled}
          onChange={onChange}
          unknownOption={false}
        />
      )}
      {choice === "unknown" && (
        <p className="field-help">
          Saved without an occurrence date. Recording time is kept separately
          and is never shown as when it happened.
        </p>
      )}
    </fieldset>
  );
}
