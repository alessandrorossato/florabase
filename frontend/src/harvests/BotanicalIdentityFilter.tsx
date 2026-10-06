import { useEffect, useRef, useState } from "react";
import {
  ReferencePicker,
  type ReferenceChoice,
} from "../seed-lots/ReferencePicker";

export function BotanicalIdentityFilter({
  choices,
  value,
  onChange,
}: {
  choices: ReferenceChoice[];
  value: string;
  onChange: (id: string) => void;
}) {
  const [reset, setReset] = useState(0);
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (reset) container.current?.querySelector("input")?.focus();
  }, [reset]);
  return (
    <div className="botanical-identity-filter" ref={container}>
      <ReferencePicker
        key={reset}
        label="Botanical identity"
        placeholder="All botanical identities"
        choices={
          value && !choices.some((choice) => choice.id === value)
            ? [
                ...choices,
                {
                  id: value,
                  label: `Unavailable botanical identity · ${value}`,
                },
              ]
            : choices
        }
        value={value}
        onChange={onChange}
      />
      {value && (
        <button
          type="button"
          className="botanical-identity-filter-clear secondary"
          aria-label="Clear botanical identity filter"
          onClick={() => {
            onChange("");
            setReset((count) => count + 1);
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}
