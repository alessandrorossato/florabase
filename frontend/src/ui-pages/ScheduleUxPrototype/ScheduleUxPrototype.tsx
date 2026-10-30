import { useEffect, useRef, useState } from "react";
import { ActivityPage } from "../../components/ActivityPage";
import { TaskDialog } from "../../components/TaskDialog";
import { ActivityPageHeader } from "../../events/ActivityPageHeader";
import { ActivityChoices } from "../../events/ActivityFilters";
import { StatusBadge } from "../../components/WorkspaceUI";
import { ActivityDialog } from "../../schedule/ScheduleScreen";
import {
  ScheduleActivityRow,
  type ActivityAction,
} from "../../schedule/ScheduleActivityRow";
import { ScheduleCalendar } from "../../schedule/ScheduleCalendar";
import { ScheduleTargetLabel } from "../../schedule/ScheduleTargetLabel";
import {
  getActivity,
  listCalendar,
  listSchedule,
  transitionActivity,
  writeActivity,
  type Activity,
  type SchedulePage,
} from "../../schedule/api";
import {
  activityLabels,
  statusLabels,
  targetLabels,
  windowLabels,
  targetHref,
  type ScheduleState,
  type DateWindow,
} from "../../schedule/state";
import { dayLabel, monthLabel } from "../../schedule/calendar";
import {
  useAppearance,
  paletteLabels,
  type Palette,
} from "../../appearance/theme";
import { ApiError } from "../../auth/api";
import { fixtureToday, type FixtureSchedule } from "./fixtures";
import {
  agendaGroups,
  loadWeek,
  prototypeHash,
  readPrototype,
  shiftDay,
  weekDays,
  type UxView,
} from "./model";
import "../../events/activity.css";
import "../../schedule/schedule.css";
import "./prototype.css";

type Dialog = Parameters<typeof ActivityDialog>[0]["dialog"];
export function ScheduleUxPrototype({ fixture }: { fixture: FixtureSchedule }) {
  const [route, setRoute] = useState(readPrototype);
  const { state, ux, selected } = route;
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    page: SchedulePage | null;
    error: boolean;
  } | null>(null);
  const [inspection, setInspection] = useState<Activity | null>(null);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [mobile, setMobile] = useState(
    () => window.matchMedia("(max-width: 75rem)").matches,
  );
  const trigger = useRef<HTMLElement | null>(null);
  const fallback = useRef<HTMLButtonElement>(null);
  const inspector = useRef<HTMLElement>(null);
  const theme = useAppearance();
  const key = JSON.stringify([state, ux, offset, attempt]);
  const current = result?.key === key ? result : null;
  const page = current?.page ?? null;
  const selectedDay =
    state.date ||
    (fixtureToday.startsWith(state.month) ? fixtureToday : `${state.month}-01`);
  const days = weekDays(selectedDay);
  useEffect(() => {
    const sync = () => {
      setRoute(readPrototype());
      setInspection(null);
      setOffset(0);
      setDialog(null);
      setError("");
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    const query = window.matchMedia("(max-width: 75rem)");
    const resize = () => {
      setMobile(query.matches);
    };
    query.addEventListener("change", resize);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
      query.removeEventListener("change", resize);
    };
  }, []);
  useEffect(() => {
    const c = new AbortController();
    void (
      ux === "month"
        ? listCalendar(state, c.signal)
        : ux === "week"
          ? loadWeek(state, c.signal)
          : listSchedule(state, offset, 50, c.signal)
    )
      .then((value) => {
        if (!c.signal.aborted) setResult({ key, page: value, error: false });
      })
      .catch(() => {
        if (!c.signal.aborted) setResult({ key, page: null, error: true });
      });
    return () => {
      c.abort();
    };
  }, [key, offset, state, ux]);
  useEffect(() => {
    const c = new AbortController();
    if (selected)
      void getActivity(selected, c.signal)
        .then((item) => {
          if (!c.signal.aborted) setInspection(item);
        })
        .catch(() => {
          if (!c.signal.aborted) setNotice("Synthetic activity unavailable.");
        });
    return () => {
      c.abort();
    };
  }, [selected, attempt]);
  useEffect(() => {
    if (inspection && !mobile) inspector.current?.focus();
  }, [inspection, mobile]);
  function update(
    next: ScheduleState,
    nextView = ux,
    typing = false,
    id = selected,
  ) {
    const hash = prototypeHash(next, nextView, id);
    if (hash !== window.location.hash)
      window.history[typing ? "replaceState" : "pushState"](null, "", hash);
    setRoute({ state: next, ux: nextView, selected: id });
    setOffset(0);
  }
  function selectDay(day: string) {
    update({ ...state, date: day, month: day.slice(0, 7) });
  }
  function open(action: ActivityAction, item: Activity) {
    trigger.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    if (action === "inspect") {
      setInspection(item);
      update(state, ux, false, item.id);
    } else {
      setError("");
      setDialog({ action, item, target: item.target });
    }
  }
  function closeInspection() {
    setInspection(null);
    update(state, ux, false, "");
    (trigger.current?.isConnected
      ? trigger.current
      : fallback.current
    )?.focus();
  }
  async function save(work: () => Promise<Activity>) {
    setBusy(true);
    setError("");
    try {
      const item = await work();
      setNotice(
        `Synthetic activity ${item.status === "planned" ? "saved" : item.status}${item.linked_event_id ? " with a simulated linked Event" : " without creating an occurrence"}. Reload resets all fixture changes.`,
      );
      setDialog(null);
      setOffset(0);
      setAttempt((n) => n + 1);
      if (inspection?.id === item.id) setInspection(item);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? "This activity changed or its target is no longer compatible. Reload the current activity before trying again."
          : "Fixture save failed. Your entries are still here; try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function reload() {
    if (!dialog?.item) return;
    setBusy(true);
    try {
      const item = await getActivity(dialog.item.id);
      setDialog({
        ...dialog,
        item,
        target: item.target,
        action: item.status === "planned" ? dialog.action : "inspect",
      });
      setError("");
      setAttempt((n) => n + 1);
    } catch {
      setError("Could not reload the synthetic activity. Try again.");
    } finally {
      setBusy(false);
    }
  }
  const active = [
    ...(state.status.length && state.status.length < 3
      ? [
          {
            label: "Status",
            value: state.status.map((s) => statusLabels[s]).join(" + "),
            onRemove: () => {
              update({ ...state, status: [] });
            },
          },
        ]
      : []),
    ...(state.window !== "all"
      ? [
          {
            label: "Date window",
            value: windowLabels[state.window],
            onRemove: () => {
              update({ ...state, window: "all" });
            },
          },
        ]
      : []),
    ...(state.activity_kind.length &&
    state.activity_kind.length < Object.keys(activityLabels).length
      ? [
          {
            label: "Activity kind",
            value: state.activity_kind
              .map((s) => activityLabels[s])
              .join(" + "),
            onRemove: () => {
              update({ ...state, activity_kind: [] });
            },
          },
        ]
      : []),
    ...(state.target_kind.length
      ? [
          {
            label: "Target type",
            value: state.target_kind.map((s) => targetLabels[s]).join(" + "),
            onRemove: () => {
              update({ ...state, target_kind: [], target_id: "" });
            },
          },
        ]
      : []),
    ...(state.target_id
      ? [
          {
            label: "Exact target",
            value: state.target_id,
            onRemove: () => {
              update({ ...state, target_id: "" });
            },
          },
        ]
      : []),
  ];
  function rows(items: Activity[]) {
    return (
      <ol className="schedule-list">
        {items.map((item) => (
          <li key={item.id} data-selected={selected === item.id || undefined}>
            <ScheduleActivityRow
              item={item}
              owner
              today={fixtureToday}
              onAction={open}
            />
          </li>
        ))}
      </ol>
    );
  }
  const viewSwitcher = (
    <nav className="schedule-view-switch" aria-label="Schedule presentation">
      {(["agenda", "week", "month"] as UxView[]).map((view) => (
        <a
          key={view}
          href={prototypeHash(state, view, selected)}
          aria-current={ux === view ? "page" : undefined}
        >
          {view === "agenda" ? "Agenda" : view === "week" ? "Week" : "Month"}
        </a>
      ))}
    </nav>
  );
  const inspectionContent = inspection && (
    <>
      <button type="button" className="button--quiet" onClick={closeInspection}>
        Close inspection
      </button>
      <p className="eyebrow">Scheduled intention</p>
      <h3>{inspection.title}</h3>
      <StatusBadge>{inspection.status}</StatusBadge>
      <dl>
        <dt>Due day</dt>
        <dd>
          <time dateTime={inspection.due_on}>
            {dayLabel(inspection.due_on)}
          </time>
        </dd>
        <dt>Activity</dt>
        <dd>{activityLabels[inspection.activity_kind]}</dd>
        <dt>Exact target</dt>
        <dd>
          {inspection.target ? (
            <>
              <a href={targetHref(inspection.target)}>
                <ScheduleTargetLabel target={inspection.target} />
              </a>
              <p>
                {targetLabels[inspection.target.kind]} ·{" "}
                {inspection.target.lifecycle ?? "Reference record"}
              </p>
            </>
          ) : (
            "Whole collection"
          )}
        </dd>
        <dt>Planning notes</dt>
        <dd>{inspection.notes ?? "No planning notes"}</dd>
      </dl>
      {inspection.target?.lifecycle &&
        inspection.target.lifecycle !== "active" && (
          <p className="notice">
            Historical target retained. Complete without an Event or explicitly
            retarget.
          </p>
        )}
      {inspection.completed_at && (
        <p>
          Completion recorded (UTC): {inspection.completed_at}. This is not an
          occurrence date.
        </p>
      )}
      {inspection.cancelled_at && (
        <p>Cancellation recorded (UTC): {inspection.cancelled_at}</p>
      )}
      {inspection.linked_event_id && inspection.target ? (
        <a href={`${targetHref(inspection.target)}?tab=events`}>
          Linked Journal context
        </a>
      ) : (
        inspection.status === "completed" && (
          <p>Completed without a Journal Event.</p>
        )
      )}
      {inspection.status === "planned" && (
        <div className="actions">
          <button
            onClick={() => {
              setDialog({
                action: "complete",
                item: inspection,
                target: inspection.target,
              });
            }}
          >
            Complete
          </button>
          <button
            className="button--secondary"
            onClick={() => {
              setDialog({
                action: "edit",
                item: inspection,
                target: inspection.target,
              });
            }}
          >
            Edit / reschedule
          </button>
          <button
            className="button--quiet"
            onClick={() => {
              setDialog({
                action: "cancel",
                item: inspection,
                target: inspection.target,
              });
            }}
          >
            Cancel activity
          </button>
        </div>
      )}
    </>
  );
  return (
    <div className="activity-prototype">
      <header className="prototype-review-bar">
        <strong>Activity UX study</strong>
        <span>Synthetic · 30 Oct 2026 · memory only</span>
        <label>
          Palette{" "}
          <select
            value={theme.palette}
            onChange={(e) => {
              theme.setPalette(e.target.value as Palette);
            }}
          >
            {Object.entries(paletteLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Appearance{" "}
          <select
            value={theme.appearance}
            onChange={(e) => {
              theme.setAppearance(
                e.target.value as "light" | "dark" | "system",
              );
            }}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </label>
        <details>
          <summary>Fixture tools</summary>
          <button
            onClick={() => {
              fixture.injectConflict();
              setNotice("Next fixture write will conflict.");
            }}
          >
            Conflict next write
          </button>
          <button
            onClick={() => {
              fixture.injectFailure();
              setNotice("Next fixture request will fail.");
            }}
          >
            Fail next request
          </button>
        </details>
      </header>
      <div className="prototype-shell">
        <aside className="prototype-sidebar">
          <h1>Florabase</h1>
          <p className="eyebrow">Activity</p>
          <p>Journal · concept only</p>
          <p>History · retained</p>
          <a href={prototypeHash(state, ux)} aria-current="page">
            Schedule
          </a>
          <p className="field-help">
            Independent frontend study. No live collection, authentication or
            API connection.
          </p>
        </aside>
        <main className="app-content">
          <ActivityPage
            titleId="schedule-title"
            className="activity-page"
            header={
              <ActivityPageHeader
                name="Schedule"
                titleId="schedule-title"
                subtitle="Plan the next care of your collection."
                query={state.q}
                onSearch={(q) => {
                  update({ ...state, q }, ux, true);
                }}
                resetFilters={() => {
                  update({
                    ...state,
                    status: [],
                    window: "all",
                    activity_kind: [],
                    target_kind: [],
                    target_id: "",
                  });
                }}
                primaryAction={
                  <button
                    ref={fallback}
                    onClick={() => {
                      setError("");
                      setDialog({
                        action: "create",
                        item: null,
                        target: null,
                        due: selectedDay,
                      });
                    }}
                  >
                    + Schedule activity
                  </button>
                }
                activeFilters={active}
              >
                <ActivityChoices
                  title="Status"
                  labels={statusLabels}
                  selected={state.status}
                  onChange={(status) => {
                    update({ ...state, status });
                  }}
                />
                <ActivityChoices
                  title="Activity kind"
                  labels={activityLabels}
                  selected={state.activity_kind}
                  onChange={(activity_kind) => {
                    update({ ...state, activity_kind });
                  }}
                />
                <ActivityChoices
                  title="Target type"
                  labels={targetLabels}
                  selected={state.target_kind}
                  onChange={(target_kind) => {
                    update({ ...state, target_kind, target_id: "" });
                  }}
                />
                <label className="field">
                  Date window
                  <select
                    value={state.window}
                    onChange={(e) => {
                      update({
                        ...state,
                        window: e.target.value as DateWindow,
                      });
                    }}
                  >
                    {Object.entries(windowLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </ActivityPageHeader>
            }
            feedback={
              <>
                <p className="field-help">
                  Date-only work · projection day {fixtureToday} · search
                  matches titles and planning notes.
                </p>
                {notice && (
                  <p role="status" className="notice">
                    {notice}
                  </p>
                )}
                {window.location.hash &&
                  !window.location.hash.startsWith("#/schedule") && (
                    <p className="notice">
                      Exact canonical record destination: {window.location.hash}
                      . Record details are outside this fixture.{" "}
                      <a href={prototypeHash(state, ux)}>Return to Schedule</a>
                    </p>
                  )}
              </>
            }
            chronology={
              <>
                {ux !== "month" && (
                  <>
                    <div className="schedule-view-heading">
                      <h3>{monthLabel(selectedDay.slice(0, 7))}</h3>
                      {viewSwitcher}
                    </div>
                    <nav
                      className="prototype-date-nav"
                      aria-label="Planning dates"
                    >
                      <div className="actions">
                        <button
                          className="button--secondary"
                          disabled={days[0] <= "0001-01-07"}
                          onClick={() => {
                            selectDay(shiftDay(selectedDay, -7));
                          }}
                        >
                          Previous week
                        </button>
                        <button
                          className="button--secondary"
                          onClick={() => {
                            selectDay(fixtureToday);
                          }}
                        >
                          Today
                        </button>
                        <button
                          className="button--secondary"
                          disabled={days[6] >= "9999-12-24"}
                          onClick={() => {
                            selectDay(shiftDay(selectedDay, 7));
                          }}
                        >
                          Next week
                        </button>
                        <label className="prototype-jump">
                          Jump to date
                          <input
                            type="date"
                            min="0001-01-01"
                            max="9999-12-31"
                            value={selectedDay}
                            onChange={(e) => {
                              if (e.target.validity.valid && e.target.value)
                                selectDay(e.target.value);
                            }}
                          />
                        </label>
                      </div>
                      <div className="prototype-week-strip">
                        {days.map((day) => (
                          <a
                            href={prototypeHash(
                              { ...state, date: day, month: day.slice(0, 7) },
                              ux,
                              selected,
                            )}
                            key={day}
                            aria-current={
                              day === selectedDay ? "date" : undefined
                            }
                          >
                            <span>
                              {dayLabel(day).split(",")[0].slice(0, 3)}
                            </span>
                            <strong>{Number(day.slice(-2))}</strong>
                            <span>
                              {day === fixtureToday
                                ? "Today"
                                : day.slice(5, 7) !== selectedDay.slice(5, 7)
                                  ? monthLabel(day.slice(0, 7))
                                      .split(" ")[0]
                                      .slice(0, 3)
                                  : "\u00a0"}
                            </span>
                          </a>
                        ))}
                      </div>
                    </nav>
                  </>
                )}
                <div
                  className={`prototype-workspace${inspection && !mobile ? " prototype-workspace--inspect" : ""}`}
                >
                  <div>
                    {ux === "month" ? (
                      <ScheduleCalendar
                        state={state}
                        viewSwitcher={viewSwitcher}
                        page={page}
                        error={current?.error ?? false}
                        today={fixtureToday}
                        owner
                        onChange={(next) => {
                          update(next);
                        }}
                        onRetry={() => {
                          setAttempt((n) => n + 1);
                        }}
                        onAction={open}
                        onCreate={(due) => {
                          setDialog({
                            action: "create",
                            item: null,
                            target: null,
                            due,
                          });
                        }}
                      />
                    ) : current?.error ? (
                      <div role="alert">
                        <p>Could not load synthetic work.</p>
                        <button
                          onClick={() => {
                            setAttempt((n) => n + 1);
                          }}
                        >
                          Retry
                        </button>
                      </div>
                    ) : !page ? (
                      <p role="status">Loading scheduled activities…</p>
                    ) : (
                      <>
                        <p className="field-help" role="status">
                          {page.total} matching activities
                          {ux === "agenda"
                            ? ` · page ${String(offset / 50 + 1)}`
                            : " in this week"}
                          . Counts describe activities, not hours.
                        </p>
                        {ux === "week" && (
                          <div className="prototype-week-board">
                            {days.map((day) => (
                              <section key={day} aria-label={dayLabel(day)}>
                                <h4>
                                  {dayLabel(day).split(",")[0]}{" "}
                                  {Number(day.slice(-2))}
                                </h4>
                                {page.items.some((i) => i.due_on === day) ? (
                                  rows(
                                    page.items.filter((i) => i.due_on === day),
                                  )
                                ) : (
                                  <p className="field-help">No matching work</p>
                                )}
                              </section>
                            ))}
                          </div>
                        )}
                        <div
                          className={
                            ux === "week"
                              ? "prototype-selected-mobile"
                              : "prototype-agenda"
                          }
                        >
                          {ux === "week" ? (
                            <section>
                              <h3>{dayLabel(selectedDay)}</h3>
                              {rows(
                                page.items.filter(
                                  (i) => i.due_on === selectedDay,
                                ),
                              )}
                              {!page.items.some(
                                (i) => i.due_on === selectedDay,
                              ) && <p>No matching work for this day.</p>}
                            </section>
                          ) : (
                            agendaGroups(page.items, selectedDay).map(
                              ([label, items]) => (
                                <section
                                  key={label}
                                  className={`prototype-day-section${/^\d/.test(label) && label !== selectedDay ? " prototype-other-day" : ""}`}
                                >
                                  <div className="prototype-section-heading">
                                    <h3>
                                      {label === fixtureToday
                                        ? "Today"
                                        : /^\d/.test(label)
                                          ? dayLabel(label)
                                          : label}
                                    </h3>
                                    <span>{items.length} on this page</span>
                                  </div>
                                  {label === "Overdue" && (
                                    <p className="field-help">
                                      Review individually. A passed due day
                                      remains planned.
                                    </p>
                                  )}
                                  {items.length ? (
                                    rows(items)
                                  ) : (
                                    <p className="field-help">
                                      No matching work
                                      {label === "Overdue"
                                        ? " overdue on this page"
                                        : " for this day on this page"}
                                      .
                                    </p>
                                  )}
                                </section>
                              ),
                            )
                          )}
                        </div>
                        {ux === "agenda" && (
                          <nav className="actions" aria-label="Schedule pages">
                            <button
                              className="button--secondary"
                              disabled={!offset}
                              onClick={() => {
                                setOffset((n) => Math.max(0, n - 50));
                              }}
                            >
                              Previous page
                            </button>
                            <button
                              className="button--secondary"
                              disabled={offset + 50 >= page.total}
                              onClick={() => {
                                setOffset((n) => n + 50);
                              }}
                            >
                              Next page
                            </button>
                          </nav>
                        )}
                      </>
                    )}
                  </div>
                  {inspection && !mobile && (
                    <aside
                      ref={inspector}
                      tabIndex={-1}
                      className="prototype-inspector"
                      aria-label="Activity inspection"
                      onKeyDown={(e) => {
                        if (e.key === "Escape") closeInspection();
                      }}
                    >
                      {inspectionContent}
                    </aside>
                  )}
                </div>
                {inspection && mobile && (
                  <TaskDialog
                    title="Activity inspection"
                    className="ui-directory-preview-overlay"
                    onClose={closeInspection}
                    returnFocusTo={trigger}
                    fallbackFocusTo={fallback}
                    dismissOnBackdrop
                  >
                    {inspectionContent}
                  </TaskDialog>
                )}
              </>
            }
          />
          {dialog && (
            <ActivityDialog
              key={`${dialog.action}-${dialog.item?.id ?? "new"}-${String(dialog.item?.version ?? "")}`}
              dialog={dialog}
              busy={busy}
              error={error}
              onClose={() => {
                if (!busy) {
                  setDialog(null);
                  setError("");
                }
              }}
              onSave={(payload) => {
                void save(() =>
                  writeActivity(
                    dialog.item?.id ?? null,
                    payload,
                    "fixture-only",
                  ),
                );
              }}
              onTransition={(event) => {
                if (dialog.item) {
                  const item = dialog.item;
                  void save(() =>
                    transitionActivity(
                      item,
                      dialog.action === "cancel" ? "cancel" : "complete",
                      "fixture-only",
                      event,
                    ),
                  );
                }
              }}
              onReload={() => {
                void reload();
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}
