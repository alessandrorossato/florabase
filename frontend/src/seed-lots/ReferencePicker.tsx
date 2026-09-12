import { useId, useMemo, useRef, useState, type KeyboardEvent } from "react";

export interface ReferenceChoice {
  id: string;
  label: string;
  retired?: boolean;
}

export function ReferencePicker({
  label,
  choices,
  value,
  onChange,
  onCreate,
  required = false,
  disabled = false,
  createLabel = "Create new",
}: {
  label: string;
  choices: ReferenceChoice[];
  value: string;
  onChange: (id: string) => void;
  onCreate?: (query: string) => void;
  required?: boolean;
  disabled?: boolean;
  createLabel?: string;
}) {
  const inputId = useId();
  const listId = useId();
  const input = useRef<HTMLInputElement>(null);
  const selected = choices.find((choice) => choice.id === value);
  const [query, setQuery] = useState(selected?.label ?? "");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const matches = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return choices.filter(
      (choice) =>
        (!choice.retired || choice.id === value) &&
        (!normalized || choice.label.toLocaleLowerCase().includes(normalized)),
    );
  }, [choices, query, value]);

  function choose(choice: ReferenceChoice) {
    onChange(choice.id);
    setQuery(choice.label);
    setOpen(false);
  }

  function keyboard(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => Math.min(index + 1, matches.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter" && open && matches[activeIndex]) {
      event.preventDefault();
      choose(matches[activeIndex]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div
      className="field reference-picker"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
      onKeyDown={(event) => {
        if (event.key !== "Escape" || event.target === input.current) return;
        event.preventDefault();
        input.current?.focus();
        setOpen(false);
      }}
    >
      <label htmlFor={inputId}>{label}</label>
      <input
        id={inputId}
        ref={input}
        role="combobox"
        aria-autocomplete="list"
        aria-controls={listId}
        aria-expanded={open}
        aria-activedescendant={
          open && matches[activeIndex]
            ? `${listId}-${matches[activeIndex].id}`
            : undefined
        }
        autoComplete="off"
        disabled={disabled}
        required={required && !value}
        value={value && selected ? selected.label : query}
        onFocus={() => {
          setOpen(true);
        }}
        onChange={(event) => {
          setQuery(event.currentTarget.value);
          onChange("");
          setActiveIndex(0);
          setOpen(true);
        }}
        onKeyDown={keyboard}
      />
      {open && (
        <div className="reference-menu">
          <ul id={listId} role="listbox">
            {matches.map((choice, index) => (
              <li
                id={`${listId}-${choice.id}`}
                role="option"
                aria-selected={choice.id === value}
                key={choice.id}
              >
                <button
                  type="button"
                  className={index === activeIndex ? "is-active" : undefined}
                  onMouseDown={(event) => {
                    event.preventDefault();
                  }}
                  onClick={() => {
                    choose(choice);
                  }}
                >
                  {choice.label}
                  {choice.retired ? " (retired)" : ""}
                </button>
              </li>
            ))}
          </ul>
          {matches.length === 0 && <p>No matching references.</p>}
          {onCreate && (
            <button
              type="button"
              className="reference-create"
              onMouseDown={(event) => {
                event.preventDefault();
              }}
              onClick={() => {
                setOpen(false);
                onCreate(query.trim());
              }}
            >
              {query.trim() ? `${createLabel} “${query.trim()}”` : createLabel}
            </button>
          )}
        </div>
      )}
      {selected?.retired && <small>Current selection is retired.</small>}
    </div>
  );
}
