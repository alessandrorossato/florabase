import { ScheduleTargetLabel } from "./ScheduleTargetLabel";
import { useState } from "react";
import { TaskDialog } from "../components/TaskDialog";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "../components/WorkspaceUI";
import type { Activity, SchedulePage } from "./api";
import {
  calendarDate,
  dayLabel,
  monthDays,
  monthLabel,
  shiftMonth,
} from "./calendar";
import {
  ScheduleActivityRow,
  type ActivityAction,
} from "./ScheduleActivityRow";
import { activityLabels, activityState, type ScheduleState } from "./state";
import "./calendar.css";

const weekdays = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export function ScheduleCalendar({
  state,
  page,
  error,
  today,
  owner,
  onChange,
  onRetry,
  onAction,
  onCreate,
}: {
  state: ScheduleState;
  page: SchedulePage | null;
  error: boolean;
  today: string;
  owner: boolean;
  onChange: (state: ScheduleState) => void;
  onRetry: () => void;
  onAction: (action: ActivityAction, item: Activity) => void;
  onCreate: (day: string) => void;
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const days = monthDays(state.month);
  const selected =
    state.date || (today.startsWith(state.month) ? today : (days[0] ?? ""));
  const byDay = new Map<string, Activity[]>();
  for (const item of page?.items ?? []) {
    const items = byDay.get(item.due_on) ?? [];
    items.push(item);
    byDay.set(item.due_on, items);
  }
  const leading = (calendarDate(`${state.month}-01`).getDay() + 6) % 7;
  const slots = Array<string | null>(leading).fill(null).concat(days);
  while (slots.length % 7) slots.push(null);
  const weeks = Array.from({ length: slots.length / 7 }, (_, i) =>
    slots.slice(i * 7, i * 7 + 7),
  );
  function select(day: string, forceDrawer = false) {
    onChange({ ...state, date: day });
    if (forceDrawer || !window.matchMedia("(max-width: 48rem)").matches)
      setDrawerOpen(true);
  }
  function navigate(month: string) {
    setDrawerOpen(false);
    onChange({ ...state, month, date: "" });
  }
  function detail() {
    const items = byDay.get(selected) ?? [];
    return (
      <>
        {owner && (
          <button
            type="button"
            onClick={() => {
              onCreate(selected);
            }}
          >
            Add activity
          </button>
        )}
        {error ? (
          <ErrorState onRetry={onRetry}>
            Florabase could not load this day.
          </ErrorState>
        ) : !page ? (
          <LoadingState>Loading scheduled activities…</LoadingState>
        ) : items.length ? (
          <ol className="schedule-list">
            {items.map((item) => (
              <li key={item.id}>
                <ScheduleActivityRow
                  item={item}
                  owner={owner}
                  today={today}
                  onAction={onAction}
                />
              </li>
            ))}
          </ol>
        ) : (
          <EmptyState>No activities match the filters for this day.</EmptyState>
        )}
      </>
    );
  }
  return (
    <section className="schedule-calendar" aria-labelledby="calendar-period">
      <div className="schedule-calendar-nav">
        <h3 id="calendar-period" aria-live="polite">
          {monthLabel(state.month)}
        </h3>
        <nav className="schedule-compact-nav" aria-label="Calendar period">
          <button
            type="button"
            className="button--secondary"
            aria-label="Previous month"
            disabled={state.month === "0001-01"}
            onClick={() => {
              navigate(shiftMonth(state.month, -1));
            }}
          >
            <span aria-hidden="true">‹</span>
          </button>
          <button
            type="button"
            className="button--secondary schedule-period-today"
            onClick={() => {
              setDrawerOpen(false);
              onChange({ ...state, month: today.slice(0, 7), date: today });
            }}
          >
            Today
          </button>
          <button
            type="button"
            className="button--secondary"
            aria-label="Next month"
            disabled={state.month === "9999-12"}
            onClick={() => {
              navigate(shiftMonth(state.month, 1));
            }}
          >
            <span aria-hidden="true">›</span>
          </button>
        </nav>
      </div>
      <p className="muted schedule-calendar-help">
        Month overview · Select a day for its work. Dates show intended work,
        not occurrences.
      </p>
      {error ? (
        <ErrorState onRetry={onRetry}>
          Florabase could not load Calendar.
        </ErrorState>
      ) : !page ? (
        <LoadingState>Loading scheduled activities…</LoadingState>
      ) : (
        <>
          <p className="schedule-calendar-summary" role="status">
            {page.items.length}{" "}
            {state.status === "planned" ? "planned" : state.status} activities
            in this month
          </p>
          {!page.items.length && (
            <div className="schedule-calendar-empty">
              <EmptyState>
                No activities match this month and its filters.
              </EmptyState>
            </div>
          )}
        </>
      )}
      <table
        className="schedule-month"
        aria-label={`${monthLabel(state.month)} scheduled work`}
        aria-busy={!page && !error}
      >
        <thead>
          <tr>
            {weekdays.map((label) => (
              <th key={label} scope="col">
                <abbr title={label}>{label.slice(0, 3)}</abbr>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((week, i) => (
            <tr key={i}>
              {week.map((day, j) => {
                const items = day ? (byDay.get(day) ?? []) : [];
                return (
                  <td
                    key={day ?? `blank-${String(j)}`}
                    className={`${day === today ? "schedule-day--today " : ""}${day === selected ? "schedule-day--selected" : ""}`}
                  >
                    {day && (
                      <>
                        <button
                          type="button"
                          className="schedule-day-button"
                          aria-pressed={day === selected}
                          aria-current={day === today ? "date" : undefined}
                          aria-label={`${dayLabel(day)}${day === today ? ", today" : ""}${page ? `, ${String(items.length)} ${state.status} activities` : ""}`}
                          onClick={() => {
                            select(day);
                          }}
                        >
                          <time dateTime={day}>{Number(day.slice(-2))}</time>
                          {day === today && (
                            <span className="schedule-day-today">Today</span>
                          )}
                          {items.length > 0 && (
                            <span
                              className="schedule-day-count"
                              aria-hidden="true"
                            >
                              {items.length}
                            </span>
                          )}
                        </button>
                        <ol className="schedule-cell-items">
                          {items.slice(0, 2).map((item) => (
                            <li key={item.id}>
                              <button
                                type="button"
                                className="schedule-cell-activity"
                                aria-label={`${item.title}, ${activityLabels[item.activity_kind]}, ${item.target?.label ?? "Whole collection"}, ${activityState(item, today)}`}
                                onClick={() => {
                                  onAction("inspect", item);
                                }}
                              >
                                <strong>{item.title}</strong>
                                <span>
                                  {activityLabels[item.activity_kind]} ·{" "}
                                  {item.target ? (
                                    <ScheduleTargetLabel target={item.target} />
                                  ) : (
                                    "Whole collection"
                                  )}
                                </span>
                                {(item.status !== "planned" ||
                                  item.due_on <= today) && (
                                  <StatusBadge attention={item.overdue}>
                                    {activityState(item, today)}
                                  </StatusBadge>
                                )}
                              </button>
                            </li>
                          ))}
                        </ol>
                        {items.length > 2 && (
                          <button
                            type="button"
                            className="link-button schedule-day-more"
                            aria-label={`${String(items.length - 2)} more activities on ${dayLabel(day)}`}
                            onClick={() => {
                              select(day, true);
                            }}
                          >
                            {items.length - 2} more
                          </button>
                        )}
                      </>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <section
        className="schedule-mobile-day"
        aria-labelledby="schedule-selected-day"
      >
        <h4 id="schedule-selected-day">{dayLabel(selected)}</h4>
        {page && detail()}
      </section>
      {drawerOpen && (
        <TaskDialog
          title={`Scheduled work · ${dayLabel(selected)}`}
          className="schedule-day-drawer"
          dismissOnBackdrop
          onClose={() => {
            setDrawerOpen(false);
          }}
        >
          <header className="ui-section-header">
            <h3>{dayLabel(selected)}</h3>
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setDrawerOpen(false);
              }}
            >
              Close day
            </button>
          </header>
          <p className="muted">
            {state.status === "planned"
              ? "Planned"
              : state.status === "completed"
                ? "Completed"
                : "Cancelled"}{" "}
            work · current Schedule filters
          </p>
          {detail()}
        </TaskDialog>
      )}
    </section>
  );
}
