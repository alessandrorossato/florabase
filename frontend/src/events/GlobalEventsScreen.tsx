import { DirectoryResults } from "../components/DirectoryResults";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { InfoDisclosure } from "../components/ContextualHelp";
import { WorkspaceIntro } from "../components/CollectionUI";
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
  const view = useDirectoryView("events");
  const filter = view.state.category;
  const setFilter = (value: EventFilter) => {
    view.update("category", value);
  };

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
      <WorkspaceIntro
        eyebrow="Activity"
        title="Journal"
        titleId="global-events-title"
        description="Observations and actions recorded for Plants and Plant groups. Review and correct Event entries through their Plant or Plant group."
      />
      <p className="activity-orientation">
        For a read-only timeline across the collection, use{" "}
        <a href="#/history">History</a>.
      </p>
      <InfoDisclosure label="How Event corrections affect current state">
        <p>
          Editing or deleting an ordinary Event does not recompute a Plant or
          Plant group’s current lifecycle, Location or lineage. Authoritative
          operation reversal is a separate contextual action.
        </p>
      </InfoDisclosure>
      {state.status === "loading" && <p role="status">Loading Journal…</p>}
      {state.status === "error" && (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load Journal.</p>
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
          <SavedViews surface="events" state={view.savedState} />
          <EventFilters selected={filter} onSelect={setFilter} />
          <DirectoryResults count={visible.length} />
          {state.events.length === 0 ? (
            <div className="empty-state">
              <p>No Events have been recorded yet.</p>
            </div>
          ) : visible.length === 0 ? (
            <p className="notice" role="status">
              No Events match this filter.
            </p>
          ) : (
            <EventFeed journal showTargetPhoto events={visible} />
          )}
        </>
      )}
    </section>
  );
}
