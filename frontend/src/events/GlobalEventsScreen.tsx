import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { InfoDisclosure } from "../components/ContextualHelp";
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
      <header className="page-header">
        <div>
          <p className="eyebrow">Collection history</p>
          <h2 id="global-events-title">Events</h2>
          <p>
            Observations, cultivation work and status changes across the
            collection.
          </p>
        </div>
      </header>
      <InfoDisclosure label="How Event corrections affect current state">
        <p>
          Editing or deleting an ordinary Event does not recompute a Plant or
          Plant group’s current lifecycle, Location or lineage. Authoritative
          operation reversal is a separate contextual action.
        </p>
      </InfoDisclosure>
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
