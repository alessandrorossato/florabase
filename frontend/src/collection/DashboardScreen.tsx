import { Icon, type IconName } from "../components/Icon";
import { DashboardPhotos } from "./DashboardPhotos";
import { useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { OverflowMenu, PageHeader } from "../components/ReferenceUI";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Metric,
  Page,
  SectionHeader,
  StatusBadge,
} from "../components/WorkspaceUI";
import { historyDateLabel, historyOrigin } from "../history/presentation";
import { historyHref } from "../history/api";
import { SavedViews } from "../saved-views/SavedViews";
import { localDay, targetLabels } from "../schedule/state";
import { getDashboard, type DashboardResponse } from "./api";
import { useDashboardSearch } from "./DashboardSearch";
import "./dashboard.css";

type State =
  | { status: "loading" }
  | { status: "ready"; value: DashboardResponse }
  | { status: "error" };
const actions = [
  ["New seed lot", "#/seeds?action=create", "seed"],
  ["New sowing", "#/sowings?action=create", "sprout"],
  ["New plant", "#/plants?action=create&kind=plant", "plant"],
  ["New plant group", "#/plants?action=create&kind=group", "layers"],
  ["Record harvest", "#/harvests?action=create", "harvest"],
  ["New botanical identity", "#/identities?action=create", "flower"],
  ["New supplier", "#/suppliers?action=create", "store"],
  ["New location", "#/locations?action=create", "pin"],
  ["New local place", "#/geography?action=create", "globe"],
] satisfies [string, string, IconName][];

function isDashboardResponse(value: unknown): value is DashboardResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<DashboardResponse>;
  return (
    candidate.counts !== undefined &&
    candidate.overview !== undefined &&
    Array.isArray(candidate.overview.upcoming) &&
    Array.isArray(candidate.overview.recent_activity)
  );
}

export function DashboardOverview() {
  const auth = useAuth();
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [day, setDay] = useState(localDay);
  useEffect(() => {
    // Check the calendar locally; no network polling while the day is unchanged.
    const timer = window.setInterval(() => {
      setDay(localDay());
    }, 30000);
    return () => {
      window.clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void getDashboard(controller.signal, day)
      .then((value: unknown) => {
        if (!isDashboardResponse(value))
          throw new Error("Invalid Dashboard response");
        if (!controller.signal.aborted)
          setState((current) => ({
            status: "ready",
            value: {
              ...value,
              photos:
                current.status === "ready"
                  ? current.value.photos
                  : value.photos,
            },
          }));
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
  }, [attempt, auth, day]);
  if (state.status === "loading")
    return <LoadingState>Loading collection overview…</LoadingState>;
  if (state.status === "error")
    return (
      <ErrorState
        onRetry={() => {
          setState({ status: "loading" });
          setAttempt((n) => n + 1);
        }}
      >
        Florabase could not load the Dashboard.
      </ErrorState>
    );
  const { counts, overview: data } = state.value;
  return (
    <div className="dashboard-content">
      <section aria-labelledby="collection-snapshot-title">
        <h3 id="collection-snapshot-title" className="sr-only">
          Collection snapshot
        </h3>
        <div className="dashboard-metrics">
          <Metric
            label="Individual Plants"
            value={counts.active_plants}
            context="Active individual records"
            href="#/plants?type=plant"
          />
          <Metric
            label="Plant groups"
            value={counts.active_plant_groups}
            context="Active groups, not plant totals"
            href="#/plants?type=group"
          />
          <Metric
            label="Seed lots"
            value={counts.active_seed_lots}
            context="Active; quantity may be unknown"
            href="#/seeds"
          />
          <Metric
            label="Sowings"
            value={counts.active_sowings}
            context="Active propagation records"
            href="#/sowings"
          />
        </div>
        <p className="dashboard-membership">
          <strong>{data.current_identities}</strong> botanical identities
          represented in current material, including stored harvests ·{" "}
          <time dateTime={data.today}>{data.today}</time>.{" "}
          <a href="#/species-distribution?scope=current">Explore collection</a>
        </p>
      </section>
      <div className="dashboard-columns">
        <DashboardPhotos photos={state.value.photos ?? []} />
        <section
          className="dashboard-attention"
          aria-labelledby="attention-title"
        >
          <SectionHeader id="attention-title" title="Next work">
            <a href="#/schedule">Open Schedule</a>
          </SectionHeader>
          <div className="dashboard-attention-counts">
            {(
              [
                ["Overdue", data.overdue, "overdue"],
                ["Due today", data.due_today, "today"],
                ["Next 7 days", data.next_seven_days, "next_seven_days"],
              ] as const
            ).map(([label, value, window]) => (
              <a
                key={window}
                aria-label={`${label}: ${String(value)}`}
                href={`#/schedule?window=${window}`}
                className={
                  window === "overdue" && value > 0
                    ? "has-attention"
                    : undefined
                }
              >
                <strong>{value}</strong>
                <span>{label}</span>
              </a>
            ))}
          </div>
          <p className="dashboard-context">Next 7 days starts tomorrow</p>
          {data.upcoming.length ? (
            <ol className="dashboard-rows">
              {data.upcoming.map((item) => (
                <li key={item.id}>
                  <div>
                    <a
                      className="dashboard-row-title"
                      href={`#/schedule/${item.id}`}
                    >
                      {item.title}
                    </a>
                    <p>
                      {item.target
                        ? `${targetLabels[item.target.kind]} · ${item.target.label}${item.target.lifecycle && item.target.lifecycle !== "active" ? ` · ${item.target.lifecycle}` : ""}`
                        : "Collection-wide"}
                    </p>
                  </div>
                  <div className="dashboard-row-meta">
                    <StatusBadge
                      attention={item.overdue || item.due_on === data.today}
                    >
                      {item.overdue
                        ? "Overdue"
                        : item.due_on === data.today
                          ? "Due today"
                          : "Planned"}
                    </StatusBadge>
                    <time dateTime={item.due_on}>{item.due_on}</time>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState>
              No planned activities. Schedule work when your collection needs
              it.
            </EmptyState>
          )}
        </section>
      </div>
      <div className="dashboard-secondary-strip">
        <details className="dashboard-activity-disclosure" open>
          <summary>
            Recent activity · {data.recent_activity.length} latest entries
          </summary>
          <section
            className="dashboard-recent"
            aria-labelledby="recent-activity-title"
          >
            <SectionHeader id="recent-activity-title" title="Recent activity">
              <span className="dashboard-section-links">
                <a href="#/events">Open Journal</a>
                <a href="#/history">Open History</a>
              </span>
            </SectionHeader>
            <p className="dashboard-context">
              Recorded observations and operational facts
            </p>
            {data.recent_activity.length ? (
              <ol className="dashboard-rows">
                {data.recent_activity.map((entry) => (
                  <li key={entry.key}>
                    <article>
                      <div className="dashboard-activity-heading">
                        <StatusBadge>
                          {historyOrigin(entry).surface}
                        </StatusBadge>
                        <time>{historyDateLabel(entry)}</time>
                        {entry.status === "reversed" && (
                          <StatusBadge>Reversed</StatusBadge>
                        )}
                      </div>
                      <a
                        className="dashboard-row-title"
                        href={historyHref(entry.primary, entry.source_kind)}
                      >
                        {entry.title}
                      </a>
                      <p>
                        {entry.primary.label}
                        {entry.context ? ` · ${entry.context}` : ""}
                      </p>
                    </article>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState>
                No recent activity. Journal observations and recorded operations
                will appear here.
              </EmptyState>
            )}
          </section>
        </details>
        <nav
          className="dashboard-secondary-links"
          aria-label="Activity destinations"
        >
          <a href="#/events">Open Journal</a>
          <a href="#/history">Open History</a>
        </nav>
      </div>
    </div>
  );
}

export function DashboardScreen() {
  const search = useDashboardSearch();
  return (
    <Page titleId="dashboard-title" className="workspace--dashboard">
      <PageHeader
        title="Dashboard"
        titleId="dashboard-title"
        eyebrow="Overview"
        description="Current holdings, planned work and recent activity."
        tools={
          <div
            className="dashboard-toolbar"
            role="group"
            aria-label="Dashboard controls"
          >
            {search.header}
            <SavedViews
              surface="global_search"
              state={search.savedState}
              allSurfaces
              presentation="dialog"
            />
            <OverflowMenu label="Quick add ▾" ariaLabel="Quick add">
              <nav className="dashboard-quick-add" aria-label="Quick actions">
                {actions.map(([label, href, icon]) => (
                  <a key={label} href={href}>
                    <Icon name={icon} />
                    {label}
                  </a>
                ))}
              </nav>
            </OverflowMenu>
          </div>
        }
      />
      {search.content}
      {!search.active && <DashboardOverview />}
    </Page>
  );
}
