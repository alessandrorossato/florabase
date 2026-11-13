import "./partial-date.css";
import { useEffect, useRef, useState } from "react";
import { FieldLabel } from "../components/FieldLabel";
import type { PartialDate } from "./api";
import { FieldHelp } from "../components/ContextualHelp";

type Precision = PartialDate["precision"];
type Part = "year" | "month" | "day";
/** What the user has typed so far. Never a payload: a missing part stays "". */
interface Draft {
  precision: Precision | "";
  year: string;
  month: string;
  day: string;
}
const neededParts: Record<Precision, Part[]> = {
  year: ["year"],
  month: ["year", "month"],
  day: ["year", "month", "day"],
};

function draftOf(value: PartialDate | null, fallback: Precision | ""): Draft {
  const text = (part: number | null | undefined) =>
    part == null ? "" : String(part);
  const precision = value?.precision ?? fallback;
  return {
    precision,
    year: text(value?.year),
    month: precision === "year" ? "" : text(value?.month),
    day: precision === "day" ? text(value?.day) : "",
  };
}

/** The first part that is missing or not a real calendar value, with its upper bound. */
function problemOf(draft: Draft): { part: Part; max: number } | null {
  if (!draft.precision) return null;
  for (const part of neededParts[draft.precision]) {
    const max =
      part === "year"
        ? 9999
        : part === "month"
          ? 12
          : // The Gregorian calendar repeats every 400 years; 2000 keeps Date away from 2-digit years.
            new Date(
              Date.UTC(
                2000 + (Number(draft.year) % 400),
                Number(draft.month),
                0,
              ),
            ).getUTCDate();
    const number = Number(draft[part]);
    if (!draft[part] || !Number.isInteger(number) || number < 1 || number > max)
      return { part, max };
  }
  return null;
}

/** Only call for a complete draft. */
function valueOf(draft: Draft): PartialDate | null {
  if (!draft.precision) return null;
  return {
    precision: draft.precision,
    year: Number(draft.year),
    ...(draft.precision !== "year" ? { month: Number(draft.month) } : {}),
    ...(draft.precision === "day" ? { day: Number(draft.day) } : {}),
  };
}

const sameDate = (a: PartialDate | null, b: PartialDate | null) =>
  a?.precision === b?.precision &&
  a?.year === b?.year &&
  (a?.month ?? null) === (b?.month ?? null) &&
  (a?.day ?? null) === (b?.day ?? null);

/**
 * Edits a PartialDate without ever inventing a part. `onChange` receives a complete
 * PartialDate, or null both for "unknown" and while the draft is incomplete. An
 * incomplete draft marks its empty input invalid (custom validity), which blocks native
 * submission; forms with `noValidate` ask `invalidDateControls` before saving.
 */
export function PartialDateField({
  id,
  label,
  value,
  onChange,
  disabled,
  showHelp = true,
  helpText,
  hidePrecisionLabel = false,
  unknownOption = true,
}: {
  id: string;
  label: string;
  value: PartialDate | null;
  onChange: (value: PartialDate | null) => void;
  disabled: boolean;
  showHelp?: boolean;
  helpText?: string;
  hidePrecisionLabel?: boolean;
  /** False where "unknown" is chosen elsewhere: precision then starts at Complete date. */
  unknownOption?: boolean;
}) {
  const fallback = unknownOption ? "" : "day";
  const [draft, setDraft] = useState(() => draftOf(value, fallback));
  // The value this draft stands for; a different `value` means the form replaced it.
  const [seen, setSeen] = useState(value);
  if (!sameDate(seen, value)) {
    setSeen(value);
    setDraft(draftOf(value, fallback));
  }
  const problem = problemOf(draft);
  const message = problem
    ? `${label} is incomplete: enter a valid ${problem.part} (1–${String(problem.max)}), or change its precision.`
    : "";
  const parts = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const input = parts.current?.querySelector<HTMLInputElement>(
      `[data-date-control="${problem?.part ?? ""}"]`,
    );
    input?.setCustomValidity(message);
    return () => input?.setCustomValidity("");
  }, [message, problem?.part]);

  function change(next: Draft) {
    const emitted = problemOf(next) ? null : valueOf(next);
    setDraft(next);
    setSeen(emitted);
    if (!sameDate(emitted, value)) onChange(emitted);
  }
  const helpId = `${id}-precision-help`;
  const problemId = `${id}-problem`;
  const bounds = { year: 9999, month: 12, day: 31 };
  return (
    <fieldset className="partial-date partial-date--stacked">
      <legend>{label}</legend>
      <div className="field">
        <label
          htmlFor={`${id}-precision`}
          className={hidePrecisionLabel ? "sr-only" : undefined}
        >
          {hidePrecisionLabel ? `${label} precision` : "Precision"}
        </label>
        <select
          aria-describedby={showHelp ? helpId : undefined}
          id={`${id}-precision`}
          disabled={disabled}
          value={draft.precision}
          onChange={(event) => {
            const precision = event.currentTarget.value as Precision | "";
            // Keep what was typed, drop what the new precision does not need, add nothing.
            const keep = precision ? neededParts[precision] : [];
            change({
              precision,
              year: keep.includes("year") ? draft.year : "",
              month: keep.includes("month") ? draft.month : "",
              day: keep.includes("day") ? draft.day : "",
            });
          }}
        >
          {unknownOption && <option value="">Unknown</option>}
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
      {draft.precision && (
        <div className="partial-date-parts" ref={parts}>
          {neededParts[draft.precision].map((part) => (
            <div className="field" key={part}>
              <FieldLabel htmlFor={`${id}-${part}`} required>
                {part[0].toUpperCase() + part.slice(1)}
              </FieldLabel>
              <input
                id={`${id}-${part}`}
                data-date-control={part}
                aria-required="true"
                aria-describedby={
                  problem?.part === part ? problemId : undefined
                }
                type="number"
                min="1"
                max={bounds[part]}
                disabled={disabled}
                value={draft[part]}
                onChange={(event) => {
                  change({ ...draft, [part]: event.currentTarget.value });
                }}
              />
            </div>
          ))}
        </div>
      )}
      {problem && (
        <p className="field-help" id={problemId}>
          Enter a valid {problem.part} (1–{problem.max}), or change the
          precision. Nothing is filled in for you.
        </p>
      )}
    </fieldset>
  );
}
