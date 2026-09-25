import { useEffect, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";

import { EventFeed } from "../events/EventFeed";
import { getDashboard, type DashboardResponse } from "./api";
import { useDashboardSearch } from "./DashboardSearch";

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

function DashboardOverview() {
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
    <>
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
          <section
            aria-labelledby="collection-snapshot-title"
            className="dashboard-snapshot"
          >
            <div className="section-heading">
              <div>
                <p className="eyebrow">Current holdings</p>
                <h3 id="collection-snapshot-title">Collection snapshot</h3>
              </div>
            </div>
            <div className="dashboard-stat-strip">
              {[
                {
                  label: "Seed lots",
                  value: state.value.counts.active_seed_lots,
                  href: "#/seeds",
                },
                {
                  label: "Sowings",
                  value: state.value.counts.active_sowings,
                  href: "#/sowings",
                },
                {
                  label: "Plants",
                  value: state.value.counts.active_plants,
                  href: "#/plants?type=plant",
                },
                {
                  label: "Plant groups",
                  value: state.value.counts.active_plant_groups,
                  href: "#/plants?type=group",
                },
              ].map((item) => (
                <a href={item.href} key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </a>
              ))}
            </div>
          </section>
          <nav aria-label="Quick actions" className="dashboard-quick-actions">
            <h3>Quick actions</h3>
            <a
              className="button-link button--secondary"
              href="#/seeds?action=create"
            >
              Add seed lot
            </a>
            <a
              className="button-link button--secondary"
              href="#/plants?action=create&kind=plant"
            >
              Add plant
            </a>
            <a
              className="button-link button--secondary"
              href="#/plants?action=create&kind=group"
            >
              Add plant group
            </a>
            <a className="button-link button--secondary" href="#/import-export">
              Import / Export
            </a>
          </nav>
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
    </>
  );
}

export function DashboardScreen() {
  const search = useDashboardSearch();
  return (
    <section
      aria-labelledby="dashboard-title"
      className="workspace workspace--dashboard"
    >
      <header className="page-header">
        <div>
          <p className="eyebrow">Collection overview</p>
          <h2 id="dashboard-title">Dashboard</h2>
          <p>What is in your collection, and what happened recently.</p>
        </div>
        {search.header}
      </header>
      {search.content}
      {!search.active && <DashboardOverview />}
    </section>
  );
}
