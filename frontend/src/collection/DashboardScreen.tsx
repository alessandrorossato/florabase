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
import { localDay, targetLabels } from "../schedule/state";
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

type Upcoming = DashboardResponse["overview"]["upcoming"][number];
const targetRoutes: Record<string, string> = {
  plant: "plants",
  plant_group: "plant-groups",
  seed_lot: "seeds",
  sowing: "sowings",
  location: "locations",
  botanical_identity: "identities",
};

/** Planned items grouped by their target record, in the order the Schedule returned them. */
function workGroups(items: Upcoming[]) {
  const groups: {
    key: string;
    label: string;
    detail: string;
    href: string | null;
    items: Upcoming[];
  }[] = [];
  for (const item of items) {
    const target = item.target;
    const key = target ? `${target.kind}:${target.id}` : "collection";
    let group = groups.find((candidate) => candidate.key === key);
    if (!group) {
      group = {
        key,
        label: target ? target.label : "Collection-wide",
        detail: target
          ? `${targetLabels[target.kind]}${target.lifecycle && target.lifecycle !== "active" ? ` · ${target.lifecycle}` : ""}`
          : "Not tied to a record",
        href: target ? `#/${targetRoutes[target.kind]}/${target.id}` : null,
        items: [],
      };
      groups.push(group);
    }
    group.items.push(item);
  }
  return groups;
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
  const coverage = (value: number) =>
    `${String(value)} of ${String(data.current_identities)}`;
  return (
    <div className="today">
      <p className="today-lede">{summary(state.value)}</p>

      <section
        className="today-holdings"
        aria-labelledby="collection-snapshot-title"
      >
        <h3 id="collection-snapshot-title" className="today-label">
          Collection snapshot
        </h3>
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
        </div>
        <p className="today-note">
          <strong>{data.current_identities}</strong> botanical identities
          represented in current material, including stored harvests.{" "}
          <a href="#/species-distribution?scope=current">Explore collection</a>
        </p>
      </section>

      <div className="today-grid">
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
          {data.upcoming.length ? (
            // Grouped by record: each record is named once over its planned items.
            <div className="today-work-groups">
              {workGroups(data.upcoming).map((group) => (
                <div key={group.key} className="today-work-group">
                  <h4>
                    {group.href ? (
                      <a href={group.href}>{group.label}</a>
                    ) : (
                      group.label
                    )}
                    <span>{group.detail}</span>
                  </h4>
                  <ol className="today-work-list">
                    {group.items.map((item) => {
                      const state = item.overdue
                        ? "Overdue"
                        : item.due_on === data.today
                          ? "Due today"
                          : "Planned";
                      return (
                        <li key={item.id}>
                          <time dateTime={item.due_on}>{item.due_on}</time>
                          <a href={`#/schedule/${item.id}`}>{item.title}</a>
                          <StatusBadge attention={state !== "Planned"}>
                            {state}
                          </StatusBadge>
                        </li>
                      );
                    })}
                  </ol>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState>
              No planned activities. Schedule work when your collection needs
              it.
            </EmptyState>
          )}
          <p className="today-footnote">
            Overdue is derived from the due date; it does not mean the work
            happened or did not. Next 7 days starts tomorrow. The list shows the
            earliest planned items.
          </p>
        </section>

        <DashboardPhotos photos={state.value.photos ?? []} />
      </div>

      <div className="today-stack">
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

      <section className="today-quality" aria-labelledby="data-quality-title">
        <details>
          <summary>
            <span id="data-quality-title" className="today-quality__title">
              Data quality
            </span>
            <span className="today-quality__hint">
              Derived counts of current records, for occasional review
            </span>
          </summary>
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
        </details>
      </section>
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
