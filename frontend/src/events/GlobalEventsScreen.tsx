import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { listGlobalEvents, type EventResponse } from "../collection/api";
import { EventFeed, EventFilters } from "./EventFeed";
import { filteredEvents, type EventFilter } from "./eventData";

type State =
  | { status: "loading" }
  | { status: "ready"; events: EventResponse[] }
  | { status: "error" };

export function GlobalEventsScreen() {
  const auth = useAuth();
  const [state, setState] = useState<State>({ status: "loading" });
  const [filter, setFilter] = useState<EventFilter>("all");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void listGlobalEvents(controller.signal)
      .then((events) => {
        setState({ status: "ready", events });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, auth]);

  const visible = useMemo(
    () =>
      state.status === "ready" ? filteredEvents(state.events, filter) : [],
    [filter, state],
  );

  return (
    <section aria-labelledby="global-events-title" className="workspace">
      <div className="workspace-intro">
        <p className="eyebrow">Collection history</p>
        <h2 id="global-events-title">Events</h2>
        <p>
          Chronological observations, cultivation work, and status changes
          across Plants and Plant groups.
        </p>
      </div>
      {state.status === "loading" && <p role="status">Loading Events…</p>}
      {state.status === "error" && (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load collection Events.</p>
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry
          </button>
        </div>
      )}
      {state.status === "ready" && (
        <>
          <EventFilters selected={filter} onSelect={setFilter} />
          {state.events.length === 0 ? (
            <div className="empty-state">
              <p>No Events have been recorded yet.</p>
            </div>
          ) : visible.length === 0 ? (
            <p className="notice" role="status">
              No Events match this filter.
            </p>
          ) : (
            <EventFeed events={visible} />
          )}
        </>
      )}
    </section>
  );
}
