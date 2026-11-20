import { DirectoryResults } from "../components/DirectoryResults";
import { SavedViews } from "../saved-views/SavedViews";
import { useDirectoryView } from "../saved-views/useDirectoryView";
import { useEffect, useMemo, useState } from "react";

import { ApiError, isExpectedAuthCancellation } from "../auth/api";
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
  listJournalRootingObservations,
  type JournalRootingObservation,
} from "./api";
import {
  filteredEvents,
  notebookEvents,
  searchJournal,
  rootingStageLabels,
  type EntryCategory,
  entryLabels,
} from "./eventData";

type State =
  | { status: "loading" }
  | {
      status: "ready";
      events: EventResponse[];
      rooting: JournalRootingObservation[];
    }
  | { status: "error" };

export function GlobalEventsScreen() {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const [state, setState] = useState<State>({ status: "loading" });
  const view = useDirectoryView("events");
  const filter = view.state.category;
  const setFilter = (value: EntryCategory[]) => {
    view.update("category", value);
  };

  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    void Promise.all([
      listGlobalEvents(capability, controller.signal),
      listJournalRootingObservations(capability, controller.signal),
    ])
      .then(([events, rooting]) => {
        if (!controller.signal.aborted)
          setState({ status: "ready", events, rooting });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) sessionExpired();
        else setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, authorized, capability, sessionExpired]);

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

  const visibleRooting =
    state.status === "ready" &&
    (!filter.length || filter.includes("observations"))
      ? state.rooting.filter((entry) => {
          const query = view.state.q.trim().toLowerCase();
          return [
            "Rooting observation",
            rootingStageLabels[entry.stage],
            entry.attempt_label ?? "Rooting attempt",
            entry.notes,
          ].some((value) => value?.toLowerCase().includes(query));
        })
      : [];
  const visibleCount = visible.length + visibleRooting.length;

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
              <DirectoryResults count={visibleCount} />
              {notebookEvents(state.events).length === 0 &&
              state.rooting.length === 0 ? (
                <div className="empty-state">
                  <p>
                    No Journal entries yet. Choose a{" "}
                    <a href="#/plants">Plant</a> or{" "}
                    <a href="#/plants?type=group">Plant group</a> to record an
                    observation, note or action.
                  </p>
                </div>
              ) : visibleCount === 0 ? (
                <p className="notice" role="status">
                  No Journal entries match this search or filter.
                </p>
              ) : (
                <EventFeed
                  journal
                  periods
                  events={visible}
                  rootingObservations={visibleRooting}
                />
              )}
            </>
          )}
        </>
      }
    />
  );
}
