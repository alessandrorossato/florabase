import {
  useEffect,
  useId,
  useMemo,
  useState,
  type KeyboardEvent,
  type RefObject,
} from "react";

import { requestJson } from "../auth/api";
import { searchKindLabels, type SearchResponse } from "../collection/searchApi";
import { Icon, type IconName } from "../components/Icon";
import { TaskDialog } from "../components/TaskDialog";
import { allDestinations, createActions } from "./navigation";
import type { SavedViewLink } from "./useSavedViewLinks";

type SearchHit = SearchResponse["groups"][number]["items"][number];
type RecordState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; hits: SearchHit[]; total: number }
  | { status: "error" };
type Answer =
  | { query: string; status: "ready"; hits: SearchHit[]; total: number }
  | { query: string; status: "error" };

interface Option {
  key: string;
  label: string;
  detail: string;
  href: string;
  icon: IconName;
}
interface Group {
  label: string;
  options: Option[];
}

const RECORD_LIMIT = 8;
const recordIcon: IconName = "document";
const savedViewIcon: IconName = "saved-views";

function includes(text: string, query: string) {
  return text.toLocaleLowerCase().includes(query.toLocaleLowerCase());
}

/**
 * Global finder: sections and creation actions are local and always available;
 * records come from the existing authenticated search endpoint. Choosing an
 * option navigates through the shell's unsaved-changes guard.
 */
export function CommandPalette({
  onClose,
  onNavigate,
  returnFocusTo,
  savedViews = [],
}: {
  onClose: () => void;
  onNavigate: (href: string) => void;
  returnFocusTo?: RefObject<HTMLElement | null>;
  savedViews?: SavedViewLink[];
}) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [active, setActive] = useState(0);
  const id = useId();
  const trimmed = query.trim();

  useEffect(() => {
    if (trimmed.length < 2) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ q: trimmed, limit: "5" });
      requestJson<SearchResponse>(`/api/v1/search?${params.toString()}`, {
        signal: controller.signal,
      })
        .then((response) => {
          setAnswer({
            query: trimmed,
            status: "ready",
            hits: response.groups.flatMap((group) => group.items),
            total: response.total,
          });
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === "AbortError")
            return;
          setAnswer({ query: trimmed, status: "error" });
        });
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [trimmed]);
  // Record state is derived: a query without its own answer yet is loading.
  const records = useMemo<RecordState>(
    () =>
      trimmed.length < 2
        ? { status: "idle" }
        : answer?.query !== trimmed
          ? { status: "loading" }
          : answer,
    [trimmed, answer],
  );

  const groups = useMemo<Group[]>(() => {
    const destinations = allDestinations()
      .filter(
        (item) =>
          !trimmed ||
          includes(item.label, trimmed) ||
          includes(item.workspace, trimmed),
      )
      .map((item) => ({
        key: `go:${item.href}`,
        label: item.label,
        detail: item.workspace,
        href: item.href,
        icon: item.icon,
      }));
    const actions = createActions
      .filter(([label]) => !trimmed || includes(label, trimmed))
      .map(([label, href, icon]) => ({
        key: `new:${href}`,
        label,
        detail: "Create",
        href,
        icon,
      }));
    const views = savedViews
      .filter(
        (view) =>
          !trimmed ||
          includes(view.name, trimmed) ||
          includes(view.surface, trimmed),
      )
      .map((view) => ({
        key: `view:${view.id}`,
        label: view.name,
        detail: `Saved view · ${view.surface}`,
        href: view.href,
        icon: savedViewIcon,
      }));
    const found =
      records.status === "ready"
        ? records.hits.slice(0, RECORD_LIMIT).map((hit) => ({
            key: `record:${hit.kind}:${hit.id}`,
            label: hit.title,
            detail:
              hit.context && hit.context !== hit.title
                ? `${searchKindLabels[hit.kind]} · ${hit.context}`
                : searchKindLabels[hit.kind],
            href: hit.href,
            icon: recordIcon,
          }))
        : [];
    const all: Group[] = trimmed
      ? [
          { label: "Records", options: found },
          { label: "Saved views", options: views },
          { label: "Go to", options: destinations },
          { label: "Create", options: actions },
          {
            label: "Search",
            options:
              trimmed.length >= 2
                ? [
                    {
                      key: "search:all",
                      label: `All results for “${trimmed}”`,
                      detail: "Collection search with filters",
                      href: `#/dashboard?${new URLSearchParams({ q: trimmed }).toString()}`,
                      icon: "search",
                    },
                  ]
                : [],
          },
        ]
      : [
          { label: "Saved views", options: views },
          { label: "Create", options: actions },
          { label: "Go to", options: destinations },
        ];
    return all.filter((group) => group.options.length);
  }, [trimmed, records, savedViews]);

  const options = groups.flatMap((group) => group.options);
  const current = Math.min(active, Math.max(options.length - 1, 0));
  const optionId = (index: number) => `${id}-option-${String(index)}`;
  useEffect(() => {
    document
      .getElementById(optionId(current))
      ?.scrollIntoView({ block: "nearest" });
  });

  function choose(option: Option | undefined) {
    if (!option) return;
    onClose();
    onNavigate(option.href);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!options.length) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((current + step + options.length) % options.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(options[current]);
    }
  }

  const status =
    records.status === "loading"
      ? "Searching records…"
      : records.status === "error"
        ? "Record search is unavailable right now. Sections and actions still work."
        : records.status === "ready"
          ? records.total
            ? `${String(records.total)} matching ${records.total === 1 ? "record" : "records"}${records.total > RECORD_LIMIT ? `, showing ${String(Math.min(RECORD_LIMIT, records.hits.length))}` : ""}.`
            : `No records match “${trimmed}”.`
          : trimmed
            ? "Type at least two characters to search records."
            : "Jump to any section or start a new record.";

  let index = -1;
  return (
    <TaskDialog
      title="Search and commands"
      className="wb-palette"
      onClose={onClose}
      dismissOnBackdrop
      returnFocusTo={returnFocusTo}
    >
      <div className="wb-palette__field">
        <Icon name="search" />
        <input
          role="combobox"
          aria-label="Search records, sections and actions"
          aria-expanded={options.length > 0}
          aria-controls={`${id}-list`}
          aria-autocomplete="list"
          aria-activedescendant={options.length ? optionId(current) : undefined}
          autoComplete="off"
          spellCheck={false}
          placeholder="Search records, sections and actions"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
        />
        <kbd>Esc</kbd>
      </div>
      <p className="wb-palette__status" role="status" aria-live="polite">
        {status}
      </p>
      <div
        className="wb-palette__results"
        id={`${id}-list`}
        role="listbox"
        aria-label="Results"
      >
        {groups.map((group) => (
          <div
            key={group.label}
            role="group"
            aria-labelledby={`${id}-${group.label}`}
          >
            <div
              className="wb-palette__group"
              id={`${id}-${group.label}`}
              role="presentation"
            >
              {group.label}
            </div>
            {group.options.map((option) => {
              index += 1;
              const position = index;
              return (
                <div
                  key={option.key}
                  id={optionId(position)}
                  role="option"
                  aria-selected={position === current}
                  tabIndex={-1}
                  className="wb-palette__option"
                  onPointerMove={() => {
                    if (position !== current) setActive(position);
                  }}
                  onClick={() => {
                    choose(option);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") choose(option);
                  }}
                >
                  <Icon name={option.icon} />
                  <span className="wb-palette__label">{option.label}</span>
                  <span className="wb-palette__detail">{option.detail}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </TaskDialog>
  );
}
