import { useEffect, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { CollectionCard } from "../components/CollectionUI";
import { EventFeed } from "../events/EventFeed";
import { getDashboard, type DashboardResponse } from "./api";

type State =
  | { status: "loading" }
  | { status: "ready"; value: DashboardResponse }
  | { status: "error" };

function isDashboardResponse(value: unknown): value is DashboardResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<DashboardResponse>;
  return (
    candidate.counts !== undefined && Array.isArray(candidate.recent_events)
  );
}

export function DashboardScreen() {
  const auth = useAuth();
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void getDashboard(controller.signal)
      .then((value: unknown) => {
        if (!isDashboardResponse(value))
          throw new Error("Invalid Dashboard response");
        setState({ status: "ready", value });
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

  return (
    <section
      aria-labelledby="dashboard-title"
      className="workspace workspace--dashboard"
    >
      <div className="workspace-intro">
        <p className="eyebrow">Collection overview</p>
        <h2 id="dashboard-title">Dashboard</h2>
        <p>A concise view of what is active now and what happened recently.</p>
      </div>
      {state.status === "loading" && (
        <p role="status">Loading collection overview…</p>
      )}
      {state.status === "error" && (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load the Dashboard.</p>
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
          <div className="summary-grid" aria-label="Collection totals">
            <CollectionCard
              eyebrow="Active"
              href="#/plants"
              title={String(state.value.counts.active_plants)}
            >
              <p>Plants</p>
            </CollectionCard>
            <CollectionCard
              eyebrow="Active"
              href="#/plants?type=group"
              title={String(state.value.counts.active_plant_groups)}
            >
              <p>Plant groups</p>
            </CollectionCard>
            <CollectionCard
              eyebrow="Active"
              href="#/seeds"
              title={String(state.value.counts.active_seed_lots)}
            >
              <p>Seed lots</p>
            </CollectionCard>
            <CollectionCard
              eyebrow="Active"
              href="#/sowings"
              title={String(state.value.counts.active_sowings)}
            >
              <p>Sowings</p>
            </CollectionCard>
            <CollectionCard
              eyebrow="Botany"
              href="#/identities"
              title={String(state.value.counts.botanical_identities)}
            >
              <p>Botanical identities</p>
            </CollectionCard>
            <CollectionCard
              eyebrow="History"
              href="#/events"
              title={String(state.value.counts.events)}
            >
              <p>Events</p>
            </CollectionCard>
          </div>
          <section
            aria-labelledby="recent-activity-title"
            className="dashboard-activity"
          >
            <div className="section-heading">
              <div>
                <p className="eyebrow">Across the collection</p>
                <h3 id="recent-activity-title">Recent activity</h3>
              </div>
              <a href="#/events">View all Events</a>
            </div>
            {state.value.recent_events.length ? (
              <EventFeed compact events={state.value.recent_events} />
            ) : (
              <div className="empty-state">
                <p>No Events have been recorded yet.</p>
              </div>
            )}
          </section>
        </>
      )}
    </section>
  );
}
