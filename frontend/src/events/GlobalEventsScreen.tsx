import { DirectoryResults } from "../components/DirectoryResults";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { ActivityPage } from "../components/ActivityPage";
import "./activity.css";
import { listGlobalEvents, type EventResponse } from "../collection/api";
import { RecordLauncher } from "./RecordLauncher";
import { ActivityPageHeader } from "./ActivityPageHeader";
import { ActivityChoices } from "./ActivityFilters";
import { selectionLabel } from "./filterSelection";
import { EventFeed } from "./EventFeed";
import {
  filteredEvents,
  notebookEvents,
  searchJournal,
  type EntryCategory,
  entryLabels,
} from "./eventData";

type State =
  | { status: "loading" }
  | { status: "ready"; events: EventResponse[] }
  | { status: "error" };

export function GlobalEventsScreen() {
  const auth = useAuth();
  const [state, setState] = useState<State>({ status: "loading" });
  const view = useDirectoryView("events");
  const filter = view.state.category;
  const setFilter = (value: EntryCategory[]) => {
    view.update("category", value);
  };

  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void listGlobalEvents(controller.signal)
      .then((events) => {
        if (!controller.signal.aborted) setState({ status: "ready", events });
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
      state.status === "ready"
        ? searchJournal(
            filteredEvents(notebookEvents(state.events), filter),
            view.state.q,
          )
        : [],
    [filter, state, view.state.q],
  );

  return (
    <ActivityPage
      titleId="global-events-title"
      className="activity-page"
      header={
        <ActivityPageHeader
          name="Journal"
          titleId="global-events-title"
          subtitle="Record collection work and keep observations and notes."
          primaryAction={<RecordLauncher />}
          query={view.state.q}
          onSearch={(q) => {
            view.update("q", q);
          }}
          resetFilters={() => {
            setFilter([]);
          }}
          savedViews={
            <SavedViews
              presentation="dialog"
              surface="events"
              state={view.savedState}
            />
          }
          activeFilters={
            filter.length
              ? [
                  {
                    label: "Entry type",
                    value: selectionLabel(filter, entryLabels),
                    onRemove: () => {
                      setFilter([]);
                    },
                  },
                ]
              : []
          }
        >
          <ActivityChoices
            title="Entry type"
            labels={entryLabels}
            selected={filter}
            onChange={setFilter}
          />
        </ActivityPageHeader>
      }
      chronology={
        <>
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
              <DirectoryResults count={visible.length} />
              {notebookEvents(state.events).length === 0 ? (
                <div className="empty-state">
                  <p>
                    No Journal entries yet. Choose a Plant or Plant group to
                    record an observation, note or action.
                  </p>
                </div>
              ) : visible.length === 0 ? (
                <p className="notice" role="status">
                  No Journal entries match this search or filter.
                </p>
              ) : (
                <EventFeed journal events={visible} />
              )}
            </>
          )}
        </>
      }
    />
  );
}
