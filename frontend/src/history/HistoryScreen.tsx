import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { Page, StatusBadge } from "../components/WorkspaceUI";
import { ActivityChoices } from "../events/ActivityFilters";
import { selectionLabel } from "../events/filterSelection";
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
    <Page className="activity-page" titleId="history-title">
      <ActivityPageHeader
        name="History"
        titleId="history-title"
        subtitle="Past collection activity, with links to its source records."
        query={filters.q}
        onSearch={(q) => {
          update({ ...filters, q }, true);
        }}
        filterCount={
          Number(filters.category.length > 0 && filters.category.length < 6) +
          Number(
            filters.subject_kind.length > 0 &&
              filters.subject_kind.length < Object.keys(subjectLabels).length,
          ) +
          Number(Boolean(filters.year))
        }
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
        summary={
          <>
            {filters.category.length > 0 && filters.category.length < 6 && (
              <button
                type="button"
                className="filter-chip"
                aria-label="Remove fact type filter"
                onClick={() => {
                  update({ ...filters, category: [] });
                }}
              >
                Fact type: {selectionLabel(filters.category, categoryLabels)} ×
              </button>
            )}
            {filters.subject_kind.length > 0 &&
              filters.subject_kind.length <
                Object.keys(subjectLabels).length && (
                <button
                  type="button"
                  className="filter-chip"
                  aria-label="Remove record type filter"
                  onClick={() => {
                    update({ ...filters, subject_kind: [] });
                  }}
                >
                  Primary record:{" "}
                  {selectionLabel(filters.subject_kind, subjectLabels)} ×
                </button>
              )}
            {filters.year && (
              <button
                type="button"
                className="filter-chip"
                aria-label="Remove year filter"
                onClick={() => {
                  update({ ...filters, year: "" });
                }}
              >
                {filters.year} ×
              </button>
            )}
          </>
        }
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
    </Page>
  );
}
function HistoryRow({ entry }: { entry: HistoryEntry }) {
  const origin = historyOrigin(entry);
  return (
    <li>
      <article className="history-row">
        <div className="history-date">
          <time>{historyDateLabel(entry)}</time>
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
