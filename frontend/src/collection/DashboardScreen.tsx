import { useEffect, useState } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { PageHeader } from "../components/ReferenceUI";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  Metric,
  Page,
  StatusBadge,
} from "../components/WorkspaceUI";
import { historyHref } from "../history/api";
import { historyDateLabel, historyOrigin } from "../history/presentation";
import { SavedViews } from "../saved-views/SavedViews";
import { recordWorkflows } from "../events/recordWorkflows";
import type { Activity } from "../schedule/api";
import { ScheduleTargetLabel } from "../schedule/ScheduleTargetLabel";
import {
  activityAge,
  localDay,
  targetHref,
  targetLabels,
} from "../schedule/state";
import { getDashboard, type DashboardResponse } from "./api";
import { DashboardPhotos } from "./DashboardPhotos";
import { useDashboardSearch } from "./DashboardSearch";
import "./dashboard.css";
import "./today.css";

type State =
  | { status: "loading" }
  | { status: "ready"; value: DashboardResponse }
  | { status: "error" };

function isDashboardResponse(value: unknown): value is DashboardResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<DashboardResponse>;
  return (
    candidate.counts !== undefined &&
    candidate.overview !== undefined &&
    Array.isArray(candidate.overview.upcoming) &&
    Array.isArray(candidate.overview.overdue_items) &&
    Array.isArray(candidate.overview.due_today_items) &&
    Array.isArray(candidate.overview.next_seven_days_items) &&
    Array.isArray(candidate.overview.recent_activity)
  );
}

/** The operator's local calendar day, written out; it is never a stored fact. */
function dayLabel(day: string) {
  const [year, month, date] = day.split("-").map(Number);
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(year, month - 1, date));
}

function plural(count: number, one: string, many: string) {
  return `${String(count)} ${count === 1 ? one : many}`;
}

/** Calendar-day distance from the dashboard's own day, capitalised for a row badge. */
function relativeAge(item: Activity, today: string) {
  const age = activityAge(item, today) ?? "";
  return age.charAt(0).toUpperCase() + age.slice(1);
}

/** One sentence composed only from returned counts; nothing is inferred. */
function summary(value: DashboardResponse) {
  const { overdue, due_today: today } = value.overview;
  const work =
    overdue + today === 0
      ? "Nothing is overdue or due today in the Schedule"
      : [
          overdue ? `${String(overdue)} overdue` : "",
          today ? `${String(today)} due today` : "",
        ]
          .filter(Boolean)
          .join(" and ") + " in the Schedule";
  const { counts } = value;
  return `${work}. You hold ${plural(counts.active_plants, "active Plant", "active Plants")}, ${plural(counts.active_plant_groups, "Plant group", "Plant groups")}, ${plural(counts.active_seed_lots, "seed lot", "seed lots")} and ${plural(counts.active_sowings, "active sowing", "active sowings")}.`;
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
        Florabase could not load Today.
      </ErrorState>
    );
  const { counts, overview: data } = state.value;
  const windows = [
    {
      key: "overdue",
      label: "Overdue",
      total: data.overdue,
      items: data.overdue_items,
    },
    {
      key: "today",
      label: "Due today",
      total: data.due_today,
      items: data.due_today_items,
    },
    {
      key: "next_seven_days",
      label: "Next 7 days",
      total: data.next_seven_days,
      items: data.next_seven_days_items,
    },
  ];
  const coverage = (value: number) =>
    `${String(value)} of ${String(data.current_identities)}`;
  // DOM order is the visual order at every width (UX-003): work, activity, then support.
  return (
    <div className="today">
      <p className="today-lede">{summary(state.value)}</p>

      <div className="today-main">
        <section
          className="today-panel today-work"
          aria-labelledby="attention-title"
        >
          <header className="today-panel__header">
            <h3 id="attention-title">Next work</h3>
            <a href="#/schedule">Open Schedule</a>
          </header>
          <p className="today-provenance">Planned in Schedule</p>
          <div className="today-windows">
            {windows.map(({ key, label, total }) => (
              <a
                key={key}
                aria-label={`${label}: ${String(total)}`}
                href={`#/schedule?window=${key}`}
                className={
                  key === "overdue" && total > 0 ? "has-attention" : undefined
                }
              >
                <strong>{total}</strong>
                <span>{label}</span>
              </a>
            ))}
          </div>
          {windows.some(({ items }) => items.length) ? (
            // Grouped by window, so overdue work never hides today's or the coming week's.
            windows.map(
              ({ key, label, total, items }) =>
                items.length > 0 && (
                  <section
                    key={key}
                    className="today-work-group"
                    aria-labelledby={`today-work-${key}`}
                  >
                    <header>
                      <h4 id={`today-work-${key}`}>
                        {label}{" "}
                        <span>
                          {items.length < total
                            ? `${String(items.length)} earliest of ${String(total)}`
                            : total}
                        </span>
                      </h4>
                      {items.length < total && (
                        <a
                          href={`#/schedule?window=${key}`}
                          aria-label={`${label}: all ${String(total)} in Schedule`}
                        >
                          All {total} in Schedule
                        </a>
                      )}
                    </header>
                    <ol className="today-work-list">
                      {items.map((item) => (
                        <li key={item.id}>
                          <time dateTime={item.due_on}>{item.due_on}</time>
                          <div>
                            <a href={`#/schedule/${item.id}`}>{item.title}</a>
                            <p>
                              {item.target ? (
                                <>
                                  <a href={targetHref(item.target)}>
                                    <ScheduleTargetLabel target={item.target} />
                                  </a>
                                  {` · ${targetLabels[item.target.kind]}`}
                                  {item.target.lifecycle &&
                                    item.target.lifecycle !== "active" &&
                                    ` · ${item.target.lifecycle}`}
                                  {item.target.kind !== "botanical_identity" &&
                                    item.target.scientific_name && (
                                      <>
                                        {" · "}
                                        <i className="scientific-name">
                                          {item.target.scientific_name}
                                        </i>
                                      </>
                                    )}
                                </>
                              ) : (
                                "Collection-wide · not tied to a record"
                              )}
                            </p>
                          </div>
                          {item.status === "planned" && (
                            <StatusBadge attention={item.overdue}>
                              {relativeAge(item, data.today)}
                            </StatusBadge>
                          )}
                        </li>
                      ))}
                    </ol>
                  </section>
                ),
            )
          ) : (
            <EmptyState>
              {data.upcoming.length
                ? "Nothing is overdue, due today or due in the next 7 days. Later planned work is in Schedule."
                : "No planned activities. Schedule work when your collection needs it."}
            </EmptyState>
          )}
          <p className="today-footnote">
            Overdue is derived from the due date; it does not mean the work
            happened or did not. Next 7 days starts tomorrow. Each list shows
            the earliest planned items.
          </p>
        </section>

        <section
          className="today-panel today-recent"
          aria-labelledby="recent-activity-title"
        >
          <header className="today-panel__header">
            <h3 id="recent-activity-title">Recent activity</h3>
            <span className="today-links">
              <a href="#/events">Open Journal</a>
              <a href="#/history">Open History</a>
            </span>
          </header>
          <p className="today-provenance">
            Recorded in the Journal and derived History, latest first
          </p>
          {data.recent_activity.length ? (
            <ol className="today-activity">
              {data.recent_activity.map((entry) => (
                <li key={entry.key}>
                  <article>
                    <time>{historyDateLabel(entry)}</time>
                    <div>
                      <span className="today-activity__origin">
                        <StatusBadge>
                          {historyOrigin(entry).surface}
                        </StatusBadge>
                        {entry.status === "reversed" && (
                          <StatusBadge>Reversed</StatusBadge>
                        )}
                      </span>
                      <a href={historyHref(entry.primary, entry.source_kind)}>
                        {entry.title}
                      </a>
                      <p>
                        {entry.primary.label}
                        {entry.context ? ` · ${entry.context}` : ""}
                      </p>
                    </div>
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
      </div>

      <div className="today-side">
        <section
          className="today-panel today-record"
          aria-labelledby="record-title"
        >
          <header className="today-panel__header">
            <h3 id="record-title">Record</h3>
          </header>
          <p className="today-provenance">Existing workflows</p>
          <nav className="today-record__links" aria-label="Record choices">
            <a className="button-link" href="#/events">
              Add Journal entry
            </a>
            {recordWorkflows.map(({ label, href }) => (
              <a
                key={href}
                className="button-link button--secondary"
                href={href}
              >
                {label}
              </a>
            ))}
            <a
              className="button-link button--secondary"
              href="#/schedule?action=create"
            >
              Schedule activity
            </a>
          </nav>
        </section>

        <section
          className="today-panel today-holdings"
          aria-labelledby="collection-snapshot-title"
        >
          <header className="today-panel__header">
            <h3 id="collection-snapshot-title">Collection snapshot</h3>
          </header>
          <p className="today-provenance">Active records</p>
          <div className="today-metrics">
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
            <Metric
              label="Botanical identities"
              value={data.current_identities}
              context="In current material, including stored harvests"
              href="#/species-distribution?scope=current"
            />
          </div>
        </section>

        <section
          className="today-panel today-quality"
          aria-labelledby="data-quality-title"
        >
          <header className="today-panel__header">
            <h3 id="data-quality-title">To review</h3>
          </header>
          <p className="today-provenance">
            Derived counts of current records. Prompts to review, not tasks or
            conclusions.
          </p>
          <dl className="today-ledger">
            <div>
              <dt>Active sowings without a germination count</dt>
              <dd>{data.sowings_unknown_germination}</dd>
            </div>
            <div>
              <dt>Active sowings with zero germinated recorded</dt>
              <dd>{data.sowings_zero_germination}</dd>
            </div>
            <div>
              <dt>Active sowings with germination recorded</dt>
              <dd>{data.sowings_with_germination}</dd>
            </div>
            <div>
              <dt>Purchased seed lots without an Order link</dt>
              <dd>{data.purchase_packets_without_order}</dd>
            </div>
            <div>
              <dt>Current identities with reference knowledge</dt>
              <dd>{coverage(data.identities_with_profile)}</dd>
            </div>
            <div>
              <dt>Current identities with a confirmed WFO link</dt>
              <dd>{coverage(data.identities_with_wfo)}</dd>
            </div>
          </dl>
          <p className="today-footnote">
            A zero count is recorded, not a failure. Review in{" "}
            <a href="#/sowings">Sowings</a>, <a href="#/seeds">Seeds</a> or{" "}
            <a href="#/identities">Botanical identities</a>.
          </p>
        </section>

        <DashboardPhotos photos={state.value.photos ?? []} />
      </div>
    </div>
  );
}

export function DashboardScreen() {
  const search = useDashboardSearch();
  return (
    <Page titleId="dashboard-title" className="workspace--dashboard">
      <PageHeader
        title="Today"
        titleId="dashboard-title"
        eyebrow={dayLabel(localDay())}
        description="Planned work, recorded activity and what you hold."
        tools={
          <div
            className="dashboard-toolbar"
            role="group"
            aria-label="Collection search"
          >
            {search.header}
            <SavedViews
              surface="global_search"
              state={search.savedState}
              allSurfaces
              presentation="dialog"
            />
          </div>
        }
      />
      {search.content}
      {!search.active && <DashboardOverview />}
    </Page>
  );
}
