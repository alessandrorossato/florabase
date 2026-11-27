import { useEffect, useId, useState, type KeyboardEvent } from "react";
import type { ProtectedRequestCapability } from "../auth/api";
import type { BotanicalIdentityResponse } from "../botanical-identities/api";
import { FieldLabel } from "../components/FieldLabel";
import { searchNames, type Candidate } from "../taxonomy/api";

/** What the typed name resolves to when the plant is added. */
export type NameChoice =
  | { kind: "existing"; identity: BotanicalIdentityResponse }
  | { kind: "wfo"; candidate: Candidate }
  | { kind: "text" };

type Option =
  | { kind: "existing"; identity: BotanicalIdentityResponse }
  | { kind: "wfo"; candidate: Candidate };

const fold = (value: string) => value.trim().replace(/\s+/g, " ").toLowerCase();

function familyOf(candidate: Candidate): string | undefined {
  return candidate.classification.find((node) => node.rank === "family")
    ?.scientific_name;
}

function optionKey(option: Option) {
  return option.kind === "existing"
    ? `identity:${option.identity.id}`
    : `wfo:${option.candidate.taxon.source_taxon_id}`;
}

function useWfoNames(prefix: string, capability: ProtectedRequestCapability) {
  const [found, setFound] = useState<{
    prefix: string;
    names: Candidate[];
    unavailable: boolean;
  }>({ prefix: "", names: [], unavailable: false });
  useEffect(() => {
    if (prefix.length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      searchNames(prefix, capability, controller.signal)
        .then((names) => {
          setFound({ prefix, names, unavailable: false });
        })
        .catch(() => {
          // An unavailable index only removes suggestions; typing is unaffected.
          if (!controller.signal.aborted)
            setFound({ prefix, names: [], unavailable: true });
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [prefix, capability]);
  return found.prefix === prefix ? found : null;
}

/**
 * Scientific name with suggestions from the identities you already have and the local
 * WFO index. Picking an identity reuses it; picking a WFO name creates the identity linked
 * to WFO; anything else is saved as typed, without a link.
 */
export function QuickAddNameField({
  identities,
  capability,
  value,
  choice,
  disabled,
  onChange,
}: {
  identities: BotanicalIdentityResponse[];
  capability: ProtectedRequestCapability;
  value: string;
  choice: NameChoice;
  disabled: boolean;
  onChange: (value: string, choice: NameChoice) => void;
}) {
  const inputId = useId();
  const listId = useId();
  const statusId = useId();
  const [open, setOpen] = useState(false);
  // -1: nothing is highlighted until the user moves into the list.
  const [active, setActive] = useState(-1);
  const prefix = value.trim();
  const wfo = useWfoNames(prefix, capability);
  const query = fold(value);
  const existing: Option[] =
    query.length < 2
      ? []
      : identities
          .filter((identity) =>
            [
              identity.display_label,
              identity.scientific_name,
              identity.common_name ?? "",
            ]
              .map(fold)
              .some((text) => text.includes(query)),
          )
          .slice(0, 6)
          .map((identity) => ({ kind: "existing", identity }));
  const names: Option[] = (wfo?.names ?? [])
    // Unplaced names have no classification and cannot be linked (TAXONOMY-001).
    .filter((candidate) => candidate.classification.length > 0)
    .slice(0, 8)
    .map((candidate) => ({ kind: "wfo", candidate }));
  const options = [...existing, ...names];
  const shown = open && options.length > 0;

  function pick(option: Option) {
    setOpen(false);
    if (option.kind === "existing")
      onChange(option.identity.scientific_name, option);
    else onChange(option.candidate.taxon.scientific_name, option);
  }

  function keys(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && options.length) {
      event.preventDefault();
      setOpen(true);
      setActive((current) => (current + 1 >= options.length ? 0 : current + 1));
    } else if (event.key === "ArrowUp" && options.length) {
      event.preventDefault();
      setOpen(true);
      setActive((current) => (current <= 0 ? options.length - 1 : current - 1));
    } else if (event.key === "Enter" && shown && active >= 0) {
      event.preventDefault();
      pick(options[Math.min(active, options.length - 1)]);
    } else if (event.key === "Escape" && shown) {
      event.preventDefault();
      event.stopPropagation();
      setOpen(false);
    }
  }

  const status =
    choice.kind === "existing"
      ? `Uses your identity ${choice.identity.display_label}.`
      : choice.kind === "wfo"
        ? `Linked to WFO ${choice.candidate.taxon.scientific_name} ${choice.candidate.taxon.authorship} (${choice.candidate.taxon.taxonomic_status}). An identity you already have with this name is reused.`
        : prefix
          ? wfo?.unavailable
            ? "WFO suggestions are unavailable. The name is saved as typed, without a WFO link."
            : "New identity saved as typed, without a WFO link. Pick a suggestion to link it."
          : "Type at least two letters for suggestions.";

  return (
    <div className="field quick-add-name">
      <FieldLabel required htmlFor={inputId}>
        Scientific name
      </FieldLabel>
      <input
        id={inputId}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={shown}
        aria-controls={listId}
        aria-activedescendant={
          shown && active >= 0 && active < options.length
            ? `${listId}-${String(active)}`
            : undefined
        }
        aria-describedby={statusId}
        autoComplete="off"
        required
        disabled={disabled}
        value={value}
        onChange={(event) => {
          setOpen(true);
          setActive(-1);
          onChange(event.currentTarget.value, { kind: "text" });
        }}
        onFocus={() => {
          setOpen(true);
        }}
        onBlur={() => {
          setOpen(false);
        }}
        onKeyDown={keys}
      />
      <ul
        id={listId}
        role="listbox"
        aria-label="Name suggestions"
        className="quick-add-suggestions"
        hidden={!shown}
      >
        {shown &&
          options.map((option, index) => (
            <li
              key={optionKey(option)}
              id={`${listId}-${String(index)}`}
              role="option"
              aria-selected={index === active}
              onMouseDown={(event) => {
                event.preventDefault();
              }}
              onClick={() => {
                pick(option);
              }}
            >
              {option.kind === "existing" ? (
                <>
                  <span>{option.identity.display_label}</span>
                  <small>In your collection</small>
                </>
              ) : (
                <>
                  <span>
                    <i>{option.candidate.taxon.scientific_name}</i>{" "}
                    {option.candidate.taxon.authorship}
                  </span>
                  <small>
                    WFO ·{" "}
                    {option.candidate.taxon.taxonomic_status === "accepted"
                      ? "accepted"
                      : option.candidate.taxon.taxonomic_status}
                    {familyOf(option.candidate) &&
                      ` · ${familyOf(option.candidate) ?? ""}`}
                  </small>
                </>
              )}
            </li>
          ))}
      </ul>
      <p className="field-help" id={statusId} role="status">
        {status}
      </p>
    </div>
  );
}
