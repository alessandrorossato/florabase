import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { listSchedule, type SchedulePage } from "./api";
import { defaultState, localDay, scheduleHash, type TargetKind } from "./state";
import "./schedule.css";
export function UpcomingActivities({
  kind,
  id,
  current = true,
}: {
  kind?: TargetKind;
  id?: string;
  current?: boolean;
}) {
  const auth = useAuth();
  const [result, setResult] = useState<{
    key: string;
    page: SchedulePage | null;
    error: boolean;
  } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [day, setDay] = useState(localDay);
  useEffect(() => {
    const timer = window.setInterval(() => {
      setDay(localDay());
    }, 30000);
    return () => {
      window.clearInterval(timer);
    };
  }, []);
  const key = JSON.stringify([kind, id, attempt, day]);
  const currentResult = result?.key === key ? result : null;
  const page = currentResult?.page;
  const error = currentResult?.error ?? false;
  useEffect(() => {
    const c = new AbortController();
    void listSchedule(
      { ...defaultState, target_kind: kind ?? "", target_id: id ?? "" },
      0,
      3,
      c.signal,
    )
      .then((value) => {
        if (!c.signal.aborted) setResult({ key, page: value, error: false });
      })
      .catch((e: unknown) => {
        if (c.signal.aborted) return;
        if (e instanceof ApiError && e.status === 401) auth.sessionExpired();
        else setResult({ key, page: null, error: true });
      });
    return () => {
      c.abort();
    };
  }, [kind, id, key, auth]);
  const href = scheduleHash({
    ...defaultState,
    target_kind: kind ?? "",
    target_id: id ?? "",
  });
  return (
    <section className="schedule-upcoming" aria-label="Upcoming activities">
      <h3>Upcoming activities</h3>
      {error ? (
        <p role="alert">
          Could not load scheduled activities.{" "}
          <button
            onClick={() => {
              setAttempt((a) => a + 1);
            }}
          >
            Retry activities
          </button>
        </p>
      ) : !page ? (
        <p role="status">Loading activities…</p>
      ) : (
        <>
          {!kind && (
            <p>
              <a href={scheduleHash({ ...defaultState, window: "overdue" })}>
                {page.overdue_count} overdue
              </a>{" "}
              ·{" "}
              <a href={scheduleHash({ ...defaultState, window: "today" })}>
                {page.today_count} due today
              </a>
            </p>
          )}
          {page.items.length ? (
            <ol>
              {page.items.map((item) => (
                <li key={item.id}>
                  <a href={`#/schedule/${item.id}`}>{item.title}</a> ·{" "}
                  <time dateTime={item.due_on}>{item.due_on}</time>
                  {item.overdue ? " · Overdue" : ""}
                </li>
              ))}
            </ol>
          ) : (
            <p>No active activities.</p>
          )}
        </>
      )}
      <div className="button-row">
        <a href={href}>View all in Schedule</a>
        {kind && id && current && (
          <a href={`${href}${href.includes("?") ? "&" : "?"}action=create`}>
            Schedule activity
          </a>
        )}
      </div>
    </section>
  );
}
