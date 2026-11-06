import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { StatusBadge } from "../components/WorkspaceUI";
import { ActivityPage } from "../components/ActivityPage";
import { ActivityChoices } from "../events/ActivityFilters";
import { selectionLabel, toggleSelection } from "../events/filterSelection";
import { ActivityPageHeader } from "../events/ActivityPageHeader";
import { DirectoryResults } from "../components/DirectoryResults";
import { SavedViews } from "../saved-views/SavedViews";
import { historyDateLabel, historyOrigin } from "./presentation";
import "../events/activity.css";
import {
  getHistory,
  historyHref,
  type HistoryEntry,
  type HistoryResponse,
} from "./api";
import {
  categoryLabels,
  historyHash,
  readHistoryState,
  saveHistoryState,
  subjectLabels,
  type Category,
  type HistoryState,
  type SubjectKind,
} from "./state";

export function HistoryScreen() {
  const auth = useAuth();
  const [filters, setFilters] = useState(readHistoryState);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    filters: HistoryState;
    offset: number;
    attempt: number;
    data: HistoryResponse | null;
    error: boolean;
  } | null>(null);
  const current =
    result?.filters === filters &&
    result.offset === offset &&
    result.attempt === attempt
      ? result
      : null;
  const data = current?.data;
  const loading = !current;
  const error = current?.error ?? false;
  const [yearInput, setYearInput] = useState(filters.year);
  const [yearError, setYearError] = useState(false);
  const reset = useCallback((next: HistoryState) => {
    setFilters(next);
    setYearInput(next.year);
    setYearError(false);
    setOffset(0);
  }, []);
  useEffect(() => {
    const sync = () => {
      if (window.location.hash.split("?", 2)[0] === "#/history")
        reset(readHistoryState());
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, [reset]);
  useEffect(() => {
    const controller = new AbortController();
    void getHistory(filters, offset, controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) {
          setResult({ filters, offset, attempt, data: response, error: false });
        }
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else setResult({ filters, offset, attempt, data: null, error: true });
      });
    return () => {
      controller.abort();
    };
  }, [filters, offset, attempt, auth]);
  function update(next: HistoryState, typing = false) {
    const hash = historyHash(next);
    if (window.location.hash !== hash) {
      if (typing) window.history.replaceState(null, "", hash);
      else window.history.pushState(null, "", hash);
    }
    reset(next);
  }
  return (
    <ActivityPage
      className="activity-page"
      titleId="history-title"
      header={
        <ActivityPageHeader
          name="History"
          titleId="history-title"
          subtitle="Past collection activity, with links to its source records."
          query={filters.q}
          onSearch={(q) => {
            update({ ...filters, q }, true);
          }}
          resetFilters={() => {
            update({ q: filters.q, category: [], subject_kind: [], year: "" });
          }}
          savedViews={
            <SavedViews
              presentation="dialog"
              surface="history"
              state={saveHistoryState(filters)}
            />
          }
          activeFilters={[
            ...(filters.category.length > 0 && filters.category.length < 6
              ? [
                  {
                    label: "Fact type",
                    value: selectionLabel(filters.category, categoryLabels),
                    onRemove: () => {
                      update({ ...filters, category: [] });
                    },
                  },
                ]
              : []),
            ...(filters.subject_kind.length > 0 &&
            filters.subject_kind.length < Object.keys(subjectLabels).length
              ? [
                  {
                    label: "Record type",
                    value: selectionLabel(filters.subject_kind, subjectLabels),
                    onRemove: () => {
                      update({ ...filters, subject_kind: [] });
                    },
                  },
                ]
              : []),
            ...(filters.year
              ? [
                  {
                    label: "Year",
                    value: filters.year,
                    onRemove: () => {
                      update({ ...filters, year: "" });
                    },
                  },
                ]
              : []),
          ]}
        >
          <ActivityChoices
            title="Fact type"
            labels={categoryLabels}
            selected={filters.category}
            onChange={(category) => {
              update({ ...filters, category });
            }}
          />
          <ActivityChoices
            title="Primary record type"
            labels={subjectLabels}
            selected={filters.subject_kind}
            onChange={(subject_kind) => {
              update({ ...filters, subject_kind });
            }}
          />
          <div className="field activity-year-field">
            <label htmlFor="history-year">Timeline year</label>
            <input
              id="history-year"
              inputMode="numeric"
              value={yearInput}
              maxLength={4}
              aria-invalid={yearError}
              aria-describedby="history-year-help"
              onChange={(event) => {
                const value = event.target.value;
                const invalid = Boolean(
                  value && (!/^\d{1,4}$/.test(value) || Number(value) < 1),
                );
                setYearInput(value);
                setYearError(invalid);
                if (!invalid) {
                  update(
                    { ...filters, year: value ? String(Number(value)) : "" },
                    true,
                  );
                  setYearInput(value);
                }
              }}
            />
            <span id="history-year-help" role={yearError ? "alert" : undefined}>
              {yearError
                ? "Enter a year from 1 to 9999."
                : "Leave empty for every year."}
            </span>
          </div>
        </ActivityPageHeader>
      }
      chronology={
        <>
          <HistoryCategoryChips
            selected={filters.category}
            onChange={(category) => {
              update({ ...filters, category });
            }}
          />
          {loading && <p role="status">Loading History…</p>}
          {error && (
            <div className="notice notice--error" role="alert">
              <p>Florabase could not load History.</p>
              <button
                type="button"
                onClick={() => {
                  setAttempt((n) => n + 1);
                }}
              >
                Retry
              </button>
            </div>
          )}
          {!loading && !error && data && (
            <>
              <DirectoryResults count={data.items.length} total={data.total} />
              {!data.items.length ? (
                <p className="empty-state">
                  {data.total
                    ? "No entries on this page."
                    : "No recorded activity matches these filters."}
                </p>
              ) : (
                <ol className="history-list">
                  <li className="history-columns" aria-hidden="true">
                    <span>When</span>
                    <span>Fact type</span>
                    <span>What happened</span>
                    <span>Record</span>
                    <span>Related</span>
                    <span>State</span>
                  </li>
                  {data.items.map((entry) => (
                    <HistoryRow key={entry.key} entry={entry} />
                  ))}
                </ol>
              )}
              {(offset > 0 || offset + data.items.length < data.total) && (
                <nav
                  className="actions history-pagination"
                  aria-label="History pages"
                >
                  <button
                    type="button"
                    disabled={offset === 0}
                    onClick={() => {
                      setOffset(Math.max(0, offset - data.limit));
                    }}
                  >
                    Previous page
                  </button>
                  <span>Page {Math.floor(offset / data.limit) + 1}</span>
                  <button
                    type="button"
                    disabled={offset + data.items.length >= data.total}
                    onClick={() => {
                      setOffset(offset + data.limit);
                    }}
                  >
                    Next page
                  </button>
                </nav>
              )}
            </>
          )}
        </>
      }
    />
  );
}
/**
 * One-tap fact types (M8 final, D1). They read and write the same category selection as
 * the Filters drawer, through the same URL update, so the two can never disagree.
 */
function HistoryCategoryChips({
  selected,
  onChange,
}: {
  selected: readonly Category[];
  onChange: (next: Category[]) => void;
}) {
  const values = Object.keys(categoryLabels) as Category[];
  // Phones show the chips as one scrolling row (QA F4): fades mark the side with more
  // chips, and a selected chip starts in view without moving the page.
  const strip = useRef<HTMLDivElement>(null);
  const [overflow, setOverflow] = useState({ start: false, end: false });
  useEffect(() => {
    const element = strip.current;
    if (!element) return;
    const measure = () => {
      const end = element.scrollWidth - element.clientWidth;
      const next = {
        start: element.scrollLeft > 1,
        end: end > 1 && element.scrollLeft < end - 1,
      };
      setOverflow((current) =>
        current.start === next.start && current.end === next.end
          ? current
          : next,
      );
    };
    const pressed = element.querySelector<HTMLElement>(
      "button[aria-pressed='true']",
    );
    if (pressed && element.scrollWidth > element.clientWidth)
      element.scrollLeft = Math.max(
        0,
        pressed.offsetLeft - element.offsetLeft - 16,
      );
    measure();
    const observer =
      typeof ResizeObserver === "undefined"
        ? undefined
        : new ResizeObserver(measure);
    observer?.observe(element);
    element.addEventListener("scroll", measure, { passive: true });
    return () => {
      observer?.disconnect();
      element.removeEventListener("scroll", measure);
    };
  }, []);
  return (
    <div
      ref={strip}
      className="history-chips"
      role="group"
      aria-label="Quick fact type filters"
      data-overflow-start={overflow.start || undefined}
      data-overflow-end={overflow.end || undefined}
      onFocus={(event) => {
        // Browsers leave a partly clipped chip under the fade; bring it fully in view.
        const chip = event.target;
        if (chip !== event.currentTarget)
          chip.scrollIntoView({ block: "nearest", inline: "nearest" });
      }}
    >
      <button
        type="button"
        aria-pressed={selected.length === 0}
        onClick={() => {
          onChange([]);
        }}
      >
        All facts
      </button>
      {values.map((value) => (
        <button
          key={value}
          type="button"
          aria-pressed={selected.includes(value)}
          onClick={() => {
            onChange(toggleSelection(values, selected, value));
          }}
        >
          {categoryLabels[value]}
        </button>
      ))}
    </div>
  );
}

function HistoryRow({ entry }: { entry: HistoryEntry }) {
  const origin = historyOrigin(entry);
  // Recorded dates already say so ("Recorded …", "Completion recorded …"); occurred dates
  // gain their basis and recorded precision, never a more precise one.
  const occurred =
    entry.date_basis === "occurred" &&
    !(entry.source_kind === "scheduled_activity" && entry.occurred_at !== null)
      ? entry.occurred_on?.precision
      : undefined;
  return (
    <li>
      <article className="history-row">
        <div className="history-date">
          <time>{historyDateLabel(entry)}</time>
          {/* Occurred: when it happened, at its recorded precision. Recorded: when
              Florabase stored it, because no occurrence date was given. */}
          {occurred && (
            <span className="history-basis">{`occurred · ${occurred}`}</span>
          )}
        </div>
        <div className="history-content">
          <div className="activity-row-heading">
            <StatusBadge>{origin.label}</StatusBadge>
            <h3>{entry.title}</h3>
            {entry.status === "reversed" && <StatusBadge>Reversed</StatusBadge>}
          </div>
          <a
            className="history-primary"
            href={historyHref(entry.primary, entry.source_kind)}
          >
            {entry.primary.label}
          </a>
          {subjectLabels[entry.primary.kind as SubjectKind] !==
            origin.label && (
            <span className="history-subject">
              {subjectLabels[entry.primary.kind as SubjectKind]}
            </span>
          )}
          {entry.context && entry.source_kind !== "scheduled_activity" && (
            <p>{entry.context}</p>
          )}
          {entry.related.length > 0 && (
            <ul className="history-related">
              {entry.related.map((ref) => (
                <li key={`${ref.kind}:${ref.id}`}>
                  <a href={historyHref(ref)}>
                    {ref.kind === "location" ? "Destination" : "Related"}:{" "}
                    {ref.label}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </article>
    </li>
  );
}
