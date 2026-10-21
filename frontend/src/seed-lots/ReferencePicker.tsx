import {
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { FieldLabel } from "../components/FieldLabel";
import { FieldHelp } from "../components/ContextualHelp";
import { describedBy } from "../components/aria";
import { BotanicalName } from "../components/ReferenceUI";

export interface ReferenceChoice {
  id: string;
  label: string;
  scientificName?: string;
  description?: string;
  retired?: boolean;
  inactiveLabel?: string;
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
  help,
  placeholder,
  openOnFocus = true,
}: {
  label: string;
  choices: ReferenceChoice[];
  value: string;
  onChange: (id: string) => void;
  onCreate?: (query: string) => void;
  required?: boolean;
  disabled?: boolean;
  createLabel?: string;
  help?: ReactNode;
  placeholder?: string;
  /** Keep dialogs from opening a menu merely because they focused this field. */
  openOnFocus?: boolean;
}) {
  const inputId = useId();
  const listId = useId();
  const helpId = useId();
  const retiredId = useId();
  const input = useRef<HTMLInputElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const [menuSpace, setMenuSpace] = useState({ above: false, height: 256 });
  const selected = choices.find((choice) => choice.id === value);
  const [query, setQuery] = useState(selected?.label ?? "");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const typing = useRef(false);
  const previousValue = useRef(value);
  // Keep the visible query aligned with controlled value changes. Typing emits an
  // empty value first, so only a real external clear should also clear the query;
  // a parent re-render that just rebuilds `choices` must preserve typed text.
  useEffect(() => {
    const timeout = window.setTimeout(() => {
      if (value) {
        const label = choices.find((choice) => choice.id === value)?.label;
        if (label !== undefined) setQuery(label);
      } else if (previousValue.current && !typing.current) {
        setQuery("");
      }
      previousValue.current = value;
      typing.current = false;
    }, 0);
    return () => {
      window.clearTimeout(timeout);
    };
  }, [choices, value]);
  const matches = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return choices.filter(
      (choice) =>
        (!choice.retired || choice.id === value) &&
        (!normalized ||
          `${choice.label} ${choice.description ?? ""}`
            .toLocaleLowerCase()
            .includes(normalized)),
    );
  }, [choices, query, value]);

  // Anchor to the control, not its label/help or stretched field grid. Respect clipping panels.
  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const control = input.current;
      if (!control) return;
      const bounds = control.getBoundingClientRect();
      let top = 8;
      let bottom = window.innerHeight - 8;
      for (
        let ancestor = control.parentElement;
        ancestor;
        ancestor = ancestor.parentElement
      ) {
        if (
          /(auto|scroll|hidden|clip)/.test(getComputedStyle(ancestor).overflowY)
        ) {
          const clip = ancestor.getBoundingClientRect();
          top = Math.max(top, clip.top + ancestor.clientTop);
          bottom = Math.min(
            bottom,
            clip.top + ancestor.clientTop + ancestor.clientHeight,
          );
        }
      }
      const below = bottom - bounds.bottom - 4;
      const above = bounds.top - top - 4;
      const desiredHeight = Math.min(
        256,
        (menu.current?.scrollHeight ?? 254) + 2,
      );
      const useAbove = below < desiredHeight && above > below;
      const height = Math.max(0, useAbove ? above : below);
      setMenuSpace((current) =>
        current.above === useAbove && current.height === height
          ? current
          : { above: useAbove, height },
      );
    };
    place();
    const observer =
      typeof ResizeObserver === "undefined"
        ? undefined
        : new ResizeObserver(place);
    if (input.current) observer?.observe(input.current);
    if (menu.current) observer?.observe(menu.current);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);

  useLayoutEffect(() => {
    if (!open) return;
    const panel = menu.current;
    const option = panel?.querySelector<HTMLElement>("button.is-active");
    if (!panel || !option) return;
    const bounds = option.getBoundingClientRect();
    const viewport = panel.getBoundingClientRect();
    if (bounds.top < viewport.top) panel.scrollTop -= viewport.top - bounds.top;
    else if (bounds.bottom > viewport.bottom)
      panel.scrollTop += bounds.bottom - viewport.bottom;
  }, [open, activeIndex]);

  function choose(choice: ReferenceChoice) {
    onChange(choice.id);
    setQuery(choice.label);
    input.current?.focus();
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
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      event.stopPropagation();
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
        event.stopPropagation();
        input.current?.focus();
        setOpen(false);
      }}
    >
      <FieldLabel htmlFor={inputId} required={required}>
        {label}
      </FieldLabel>
      <div className="reference-control">
        <input
          id={inputId}
          ref={input}
          role="combobox"
          aria-autocomplete="list"
          aria-controls={listId}
          aria-describedby={describedBy(
            help !== undefined && help !== null && help !== false
              ? helpId
              : undefined,
            selected?.retired && retiredId,
          )}
          aria-expanded={open}
          aria-activedescendant={
            open && matches[activeIndex]
              ? `${listId}-${matches[activeIndex].id}`
              : undefined
          }
          placeholder={placeholder}
          autoComplete="off"
          disabled={disabled}
          required={required && !value}
          aria-required={required || undefined}
          value={value && selected ? selected.label : query}
          onFocus={() => {
            if (openOnFocus) setOpen(true);
          }}
          onClick={() => {
            setOpen(true);
          }}
          onChange={(event) => {
            typing.current = true;
            setQuery(event.currentTarget.value);
            onChange("");
            setActiveIndex(0);
            setOpen(true);
          }}
          onKeyDown={keyboard}
        />
        {open && (
          <div
            className="reference-menu"
            ref={menu}
            data-placement={menuSpace.above ? "above" : "below"}
            style={{ maxHeight: `min(16rem, ${String(menuSpace.height)}px)` }}
          >
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
                    <span>
                      <BotanicalName
                        label={choice.label}
                        scientificName={choice.scientificName}
                      />
                    </span>
                    {choice.description && (
                      <small className="reference-choice-context">
                        {choice.description}
                      </small>
                    )}
                    {choice.retired
                      ? ` (${choice.inactiveLabel ?? "retired"})`
                      : ""}
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
                {query.trim()
                  ? `${createLabel} “${query.trim()}”`
                  : createLabel}
              </button>
            )}
          </div>
        )}
      </div>
      {help && <FieldHelp id={helpId}>{help}</FieldHelp>}
      {selected?.retired && (
        <small id={retiredId}>
          Current selection is {selected.inactiveLabel ?? "retired"}.
        </small>
      )}
    </div>
  );
}
