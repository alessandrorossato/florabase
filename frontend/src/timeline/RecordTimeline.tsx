import { useEffect, useId, useState, type ReactNode } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { type EventResponse, type EventTargetKind } from "../events/api";
import { useJournalReader } from "../events/journalReader";
import {
  eventLabels,
  eventSourceLabel,
  formatPartialDate,
} from "../events/eventData";
import { historyHash } from "../history/state";
import { listSchedule, type SchedulePage } from "../schedule/api";
import {
  defaultState,
  localDay,
  scheduleHash,
  type TargetKind,
} from "../schedule/state";
import "./record-timeline.css";

type Loaded<T> =
  { key: string; status: "ready"; value: T } | { key: string; status: "error" };
type Lane<T> = { status: "loading" } | Loaded<T>;

function laneFor<T>(result: Loaded<T> | null, key: string): Lane<T> {
  return result?.key === key ? result : { status: "loading" };
}

/** The record's next three planned activities; refetched when the local day changes. */
function usePlanned(kind: TargetKind, id: string, day: string) {
  const auth = useAuth();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<Loaded<SchedulePage> | null>(null);
  const key = JSON.stringify([kind, id, day, attempt]);
  useEffect(() => {
    const controller = new AbortController();
    void listSchedule(
      { ...defaultState, target_kind: [kind], target_id: id },
      0,
      3,
      controller.signal,
    )
      .then((value) => {
        if (!controller.signal.aborted)
          setResult({ key, status: "ready", value });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setResult({ key, status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [kind, id, key, auth]);
  return [
    laneFor(result, key),
    () => {
      setAttempt((value) => value + 1);
    },
  ] as const;
}

/** A Plant's or Plant group's Journal, latest first as the API orders it. */
function useJournal(target: EventTargetKind | undefined, id: string) {
  const auth = useAuth();
  const reader = useJournalReader();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<Loaded<EventResponse[]> | null>(null);
  const key = JSON.stringify([target, id, attempt]);
  useEffect(() => {
    if (!target) return;
    const controller = new AbortController();
    // Inside a record view the Journal tab reuses this response (JournalScope).
    void reader
      .read(target, id)
      .then((value) => {
        if (!controller.signal.aborted)
          setResult({ key, status: "ready", value });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setResult({ key, status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [target, id, key, auth, reader]);
  return [
    laneFor(result, key),
    () => {
      if (target) reader.invalidate(target, id);
      setAttempt((value) => value + 1);
    },
  ] as const;
}

/**
 * One record's timeline, kept honest by lane: Planned work comes from the Schedule and is
 * never shown as done; Recorded entries come from the Journal with the date precision that
 * was recorded. System history (edits, operations) stays in History.
 */
export function RecordTimeline({
  kind,
  id,
  current = true,
  journal,
  recordedElsewhere,
  className = "",
}: {
  kind: TargetKind;
  id: string;
  /** Inactive records can still show plans but cannot gain new ones. */
  current?: boolean;
  /** Plants and Plant groups: the record's Journal, and how to open its tab. */
  journal?: { target: EventTargetKind; href: string; onOpen?: () => void };
  /** Other records: where their recorded observations are kept instead. */
  recordedElsewhere?: ReactNode;
  className?: string;
}) {
  const titleId = useId();
  const [day, setDay] = useState(localDay);
  useEffect(() => {
    // Overdue is derived from today's date; check the calendar locally, no polling.
    const timer = window.setInterval(() => {
      setDay(localDay());
    }, 30000);
    return () => {
      window.clearInterval(timer);
    };
  }, []);
  const [planned, retryPlanned] = usePlanned(kind, id, day);
  const [recorded, retryRecorded] = useJournal(journal?.target, id);
  const href = scheduleHash({
    ...defaultState,
    target_kind: [kind],
    target_id: id,
  });
  const history =
    kind === "botanical_identity" || kind === "location"
      ? null
      : historyHash({ q: "", category: [], subject_kind: [kind], year: "" });

  return (
    <section
      className={`record-timeline ${className}`}
      aria-labelledby={titleId}
    >
      <h4 id={titleId}>Timeline</h4>
      <div className="record-timeline__lanes">
        <section
          className="record-timeline__lane record-timeline__lane--planned"
          aria-label="Planned"
        >
          <p className="record-timeline__lane-title" aria-hidden="true">
            Planned <span>in Schedule, not yet done</span>
          </p>
          {planned.status === "error" ? (
            <p role="alert" className="record-timeline__note">
              Could not load scheduled activities.{" "}
              <button
                type="button"
                className="button--quiet"
                onClick={retryPlanned}
              >
                Retry activities
              </button>
            </p>
          ) : planned.status !== "ready" ? (
            <p role="status" className="record-timeline__note">
              Loading activities…
            </p>
          ) : planned.value.items.length ? (
            <ol className="record-timeline__list">
              {planned.value.items.map((item) => (
                <li
                  key={item.id}
                  className={
                    item.overdue
                      ? "record-timeline__item record-timeline__item--overdue"
                      : "record-timeline__item"
                  }
                >
                  <time dateTime={item.due_on}>{item.due_on}</time>
                  <div>
                    <a href={`#/schedule/${item.id}`}>{item.title}</a>
                    <p>
                      {item.overdue
                        ? "Overdue · not recorded as done"
                        : item.due_on === planned.value.today
                          ? "Due today"
                          : "Planned"}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="record-timeline__note">No planned activities.</p>
          )}
          <p className="record-timeline__links">
            <a href={href}>
              {planned.status === "ready" &&
              planned.value.total > planned.value.items.length
                ? `View all ${String(planned.value.total)} in Schedule`
                : "View all in Schedule"}
            </a>
            {current && (
              <a href={`${href}${href.includes("?") ? "&" : "?"}action=create`}>
                Schedule activity
              </a>
            )}
          </p>
        </section>

        <section
          className="record-timeline__lane record-timeline__lane--recorded"
          aria-label="Recorded"
        >
          <p className="record-timeline__lane-title" aria-hidden="true">
            Recorded <span>{journal ? "in the Journal" : "observations"}</span>
          </p>
          {!journal ? (
            <p className="record-timeline__note">{recordedElsewhere}</p>
          ) : recorded.status === "error" ? (
            <p role="alert" className="record-timeline__note">
              Could not load Journal entries.{" "}
              <button
                type="button"
                className="button--quiet"
                onClick={retryRecorded}
              >
                Retry Journal
              </button>
            </p>
          ) : recorded.status !== "ready" ? (
            <p role="status" className="record-timeline__note">
              Loading Journal…
            </p>
          ) : recorded.value.length ? (
            <ol className="record-timeline__list">
              {recorded.value.slice(0, 3).map((event) => (
                <li key={event.id} className="record-timeline__item">
                  {event.occurred_on ? (
                    <time>{formatPartialDate(event.occurred_on)}</time>
                  ) : (
                    <span className="record-timeline__undated">
                      Date not recorded
                    </span>
                  )}
                  <div>
                    <strong>{eventLabels[event.kind]}</strong>
                    <p>
                      {eventSourceLabel(event)}
                      {event.notes?.trim() ? ` · ${event.notes.trim()}` : ""}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="record-timeline__note">No Journal entries yet.</p>
          )}
          {journal && (
            <p className="record-timeline__links">
              <a href={journal.href} onClick={journal.onOpen}>
                {recorded.status === "ready" && recorded.value.length > 3
                  ? `Open Journal (${String(recorded.value.length)} entries)`
                  : "Open Journal"}
              </a>
            </p>
          )}
        </section>
      </div>
      {history && (
        <p className="record-timeline__footnote">
          Edits and collection operations are kept in{" "}
          <a href={history}>History</a>.
        </p>
      )}
    </section>
  );
}
