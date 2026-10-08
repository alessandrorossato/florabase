import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { WorkspaceIntro } from "../components/CollectionUI";
import { InfoDisclosure } from "../components/ContextualHelp";
import { DirectoryResults } from "../components/DirectoryResults";
import { SavedViews } from "../saved-views/SavedViews";
import { formatPartialDate } from "../events/eventData";
import {
  getHistory,
  historyHref,
  type HistoryEntry,
  type HistoryResponse,
} from "./api";
import {
  categories,
  categoryLabels,
  historyHash,
  readHistoryState,
  saveHistoryState,
  subjectLabels,
  type HistoryState,
  type SubjectKind,
} from "./state";

const recordedDate = (value: string) =>
  new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(value));
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
  function update(next: HistoryState) {
    const hash = historyHash(next);
    if (window.location.hash !== hash) window.history.pushState(null, "", hash);
    reset(next);
  }
  return (
    <section className="workspace" aria-labelledby="history-title">
      <WorkspaceIntro
        eyebrow="Activity"
        title="History"
        titleId="history-title"
        description="Read-only timeline of recorded collection activity: Events, propagation, germination, Harvests and stored material."
      />
      <p className="activity-orientation">
        For editable Plant and Plant group Event entries, use{" "}
        <a href="#/events">Journal</a>. Some activity has no recorded history.
      </p>
      <InfoDisclosure label="About recorded history">
        <p>
          History reflects existing domain records and their corrections. It is
          not an immutable audit log. Some current-state changes have no
          recorded history.
        </p>
        <p>
          Partial dates keep their recorded precision. “Recorded” indicates a
          recording date, rather than an occurrence date. Timeline year follows
          the date shown.
        </p>
      </InfoDisclosure>
      <SavedViews surface="history" state={saveHistoryState(filters)} />
      <div className="history-filters">
        <div
          className="history-categories"
          role="group"
          aria-label="Activity categories"
        >
          <button
            className="filter-chip"
            type="button"
            aria-pressed={filters.category.length === 0}
            onClick={() => {
              update({ ...filters, category: [] });
            }}
          >
            All activity
          </button>
          {categories.map((category) => (
            <button
              key={category}
              type="button"
              className="filter-chip"
              aria-pressed={filters.category.includes(category)}
              onClick={() => {
                update({
                  ...filters,
                  category: categories.filter((c) =>
                    c === category
                      ? !filters.category.includes(c)
                      : filters.category.includes(c),
                  ),
                });
              }}
            >
              {categoryLabels[category]}
            </button>
          ))}
        </div>
        <div className="field">
          <label htmlFor="history-subject">Primary record type</label>
          <select
            id="history-subject"
            value={filters.subject_kind}
            onChange={(event) => {
              update({
                ...filters,
                subject_kind: event.target.value as SubjectKind | "",
              });
            }}
          >
            <option value="">All record types</option>
            {Object.entries(subjectLabels).map(([kind, label]) => (
              <option key={kind} value={kind}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <form
          className="history-year"
          onSubmit={(event) => {
            event.preventDefault();
            if (
              yearInput &&
              (!/^\d{1,4}$/.test(yearInput) || Number(yearInput) < 1)
            ) {
              setYearError(true);
              return;
            }
            update({
              ...filters,
              year: yearInput ? String(Number(yearInput)) : "",
            });
          }}
        >
          <div className="field">
            <label htmlFor="history-year">Timeline year</label>
            <input
              id="history-year"
              inputMode="numeric"
              value={yearInput}
              maxLength={4}
              aria-invalid={yearError}
              aria-describedby={yearError ? "history-year-error" : undefined}
              onChange={(event) => {
                setYearInput(event.target.value);
                setYearError(false);
              }}
            />
            {yearError && (
              <span id="history-year-error">Enter a year from 1 to 9999.</span>
            )}
          </div>
          <button type="submit">Apply year</button>
          {(yearInput || filters.year) && (
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                update({ ...filters, year: "" });
              }}
            >
              Clear year
            </button>
          )}
        </form>
        {Object.keys(saveHistoryState(filters)).length > 0 && (
          <button
            type="button"
            onClick={() => {
              update({ category: [], subject_kind: "", year: "" });
            }}
          >
            Clear filters
          </button>
        )}
      </div>
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
    </section>
  );
}
function HistoryRow({ entry }: { entry: HistoryEntry }) {
  return (
    <li>
      <article className="history-row">
        <div className="history-date">
          {entry.date_basis === "recorded" ? (
            <>
              Recorded{" "}
              <time dateTime={entry.recorded_at}>
                {recordedDate(entry.recorded_at)}
              </time>
            </>
          ) : (
            <time>{formatPartialDate(entry.occurred_on)}</time>
          )}
        </div>
        <div className="history-content">
          <div className="history-badges">
            <span className="record-state">
              {categoryLabels[entry.category]}
            </span>
            {entry.status === "reversed" && (
              <span className="record-state">Reversed</span>
            )}
          </div>
          <h3>{entry.title}</h3>
          <a
            className="history-primary"
            href={historyHref(entry.primary, entry.source_kind)}
          >
            {entry.primary.label}
          </a>
          <span className="history-subject">
            {subjectLabels[entry.primary.kind as SubjectKind]}
          </span>
          {entry.context && <p>{entry.context}</p>}
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
