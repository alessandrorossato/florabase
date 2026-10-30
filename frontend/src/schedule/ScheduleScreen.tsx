import { FieldLabel } from "../components/FieldLabel";
import { ScheduleTargetLabel } from "./ScheduleTargetLabel";
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { FormActions } from "../components/ReferenceUI";
import { ActivityPage } from "../components/ActivityPage";
import { ActivityChoices } from "../events/ActivityFilters";
import { selectionLabel } from "../events/filterSelection";
import { ActivityPageHeader } from "../events/ActivityPageHeader";
import "../events/activity.css";
import { ScheduleNavigation } from "./ScheduleNavigation";
import { ScheduleCalendar } from "./ScheduleCalendar";
import { ScheduleActivityRow } from "./ScheduleActivityRow";
import { TaskDialog } from "../components/TaskDialog";
import {
  getActivity,
  getTarget,
  listSchedule,
  listCalendar,
  transitionActivity,
  writeActivity,
  type Activity,
  type ScheduleEvent,
  type SchedulePage,
  type Target,
} from "./api";
import { ScheduleTargetPicker } from "./ScheduleTargetPicker";
import {
  activityLabels,
  defaultState,
  localDay,
  readScheduleState,
  scheduleHash,
  targetHref,
  targetLabels,
  statusLabels,
  windowLabels,
  type ActivityKind,
  type ScheduleState,
  type TargetKind,
} from "./state";
import "./schedule.css";

interface Dialog {
  action: "create" | "edit" | "complete" | "cancel" | "inspect";
  item: Activity | null;
  target: Target | null;
  due?: string;
}
const eventKinds: Partial<Record<ActivityKind, ScheduleEvent["kind"][]>> = {
  repot: ["repotting"],
  move: ["movement"],
  inspect: ["observation"],
  follow_up: ["observation", "other"],
};
function message(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409)
      return "This activity changed or its target is no longer compatible. Reload the current activity before trying again.";
    const body = error.body as { detail?: { message?: string } } | undefined;
    if (body?.detail?.message) return body.detail.message;
  }
  return "Florabase could not save this activity. Your entries are still here; try again.";
}

export function ActivityDialog({
  dialog,
  busy,
  error,
  onClose,
  onSave,
  onTransition,
  onReload,
}: {
  dialog: Dialog;
  busy: boolean;
  error: string;
  onClose: () => void;
  onSave: (payload: Parameters<typeof writeActivity>[1]) => void;
  onTransition: (event: ScheduleEvent | null) => void;
  onReload: () => void;
}) {
  const item = dialog.item;
  const [title, setTitle] = useState(item?.title ?? "");
  const [kind, setKind] = useState<ActivityKind>(
    item?.activity_kind ?? "inspect",
  );
  const [due, setDue] = useState(item?.due_on ?? dialog.due ?? localDay());
  const [notes, setNotes] = useState(item?.notes ?? "");
  const [targetKind, setTargetKind] = useState<TargetKind | "">(
    (item?.target ?? dialog.target)?.kind ?? "",
  );
  const [targetId, setTargetId] = useState(
    (item?.target ?? dialog.target)?.id ?? "",
  );
  const [recordEvent, setRecordEvent] = useState(false);
  const possible =
    item &&
    (item.target?.kind === "plant" || item.target?.kind === "plant_group") &&
    item.target.lifecycle === "active"
      ? eventKinds[item.activity_kind]
      : undefined;
  const [eventKind, setEventKind] = useState<ScheduleEvent["kind"]>(
    possible?.[0] ?? "observation",
  );
  const [actual, setActual] = useState(localDay());
  const [eventNotes, setEventNotes] = useState("");
  const [destination, setDestination] = useState("");
  const values = JSON.stringify([
    title,
    kind,
    due,
    notes,
    targetKind,
    targetId,
    recordEvent,
    eventKind,
    actual,
    eventNotes,
    destination,
  ]);
  const [initialValues] = useState(values);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  function dismiss() {
    if (busy) return;
    if (values === initialValues) onClose();
    else setConfirmDiscard(true);
  }
  const heading =
    dialog.action === "create"
      ? "Schedule activity"
      : dialog.action === "edit"
        ? "Edit / reschedule activity"
        : dialog.action === "complete"
          ? "Complete activity"
          : dialog.action === "cancel"
            ? "Cancel activity"
            : "Scheduled activity";
  return (
    <>
      <TaskDialog
        title={heading}
        className="schedule-activity-dialog"
        dismissOnBackdrop
        onClose={dismiss}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (busy) return;
            if (dialog.action === "create" || dialog.action === "edit") {
              if (targetKind && !targetId) return;
              onSave({
                activity_kind: kind,
                title,
                due_on: due,
                notes: notes.trim() || null,
                target: targetKind ? { kind: targetKind, id: targetId } : null,
                ...(item ? { expected_version: item.version } : {}),
              });
            } else
              onTransition(
                recordEvent
                  ? {
                      kind: eventKind,
                      occurred_on: actual,
                      notes: eventNotes.trim() || null,
                      destination_location_id:
                        eventKind === "movement" ? destination : null,
                    }
                  : null,
              );
          }}
        >
          <header className="schedule-dialog-header">
            <h3>{heading}</h3>
          </header>
          <div className="schedule-dialog-content">
            {error && (
              <div role="alert">
                <p>{error}</p>
                {item && (
                  <button type="button" disabled={busy} onClick={onReload}>
                    Reload current activity
                  </button>
                )}
              </div>
            )}
            {dialog.action === "create" || dialog.action === "edit" ? (
              <fieldset disabled={busy} className="schedule-edit-fields">
                <label className="field schedule-field-full">
                  <FieldLabel as="span" required>
                    Title
                  </FieldLabel>
                  <input
                    required
                    maxLength={255}
                    value={title}
                    onChange={(e) => {
                      setTitle(e.target.value);
                    }}
                  />
                </label>
                <label className="field">
                  <FieldLabel as="span" required>
                    Activity kind
                  </FieldLabel>
                  <select
                    aria-required="true"
                    value={kind}
                    onChange={(e) => {
                      setKind(e.target.value as ActivityKind);
                    }}
                  >
                    {Object.entries(activityLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <FieldLabel as="span" required>
                    Due date
                  </FieldLabel>
                  <input
                    required
                    type="date"
                    value={due}
                    onChange={(e) => {
                      setDue(e.target.value);
                    }}
                  />
                </label>
                <p className="schedule-guidance schedule-field-full">
                  Date only. Overdue work stays planned.
                </p>
                <label className="field schedule-field-full">
                  Target type
                  <select
                    value={targetKind}
                    onChange={(e) => {
                      setTargetKind(e.target.value as TargetKind | "");
                      setTargetId("");
                    }}
                  >
                    <option value="">
                      Whole collection / no specific record
                    </option>
                    {Object.entries(targetLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                {targetKind && (
                  <ScheduleTargetPicker
                    key={targetKind}
                    kind={targetKind}
                    value={targetId}
                    selected={
                      (item?.target ?? dialog.target)?.kind === targetKind
                        ? (item?.target ?? dialog.target)
                        : null
                    }
                    onChange={setTargetId}
                  />
                )}
                <label className="field schedule-field-full">
                  Planning notes
                  <textarea
                    maxLength={20000}
                    value={notes}
                    onChange={(e) => {
                      setNotes(e.target.value);
                    }}
                  />
                </label>
              </fieldset>
            ) : (
              <>
                <p>
                  <strong>{item?.title}</strong> · Due {item?.due_on}
                </p>
                {item?.target && (
                  <p>
                    {targetLabels[item.target.kind]}:{" "}
                    <a href={targetHref(item.target)}>
                      <ScheduleTargetLabel target={item.target} />
                    </a>
                    {item.target.lifecycle && item.target.lifecycle !== "active"
                      ? ` (${item.target.lifecycle})`
                      : ""}
                  </p>
                )}
                {dialog.action === "inspect" ? (
                  <>
                    <p>Status: {item?.status}</p>
                    {item?.notes && (
                      <p className="schedule-notes">{item.notes}</p>
                    )}
                    {item?.completed_at && (
                      <p>
                        Completed:{" "}
                        {new Date(item.completed_at).toLocaleString()}
                      </p>
                    )}
                    {item?.cancelled_at && (
                      <p>
                        Cancelled:{" "}
                        {new Date(item.cancelled_at).toLocaleString()}
                      </p>
                    )}
                    {item?.linked_event_id && item.target && (
                      <a href={`${targetHref(item.target)}?tab=events`}>
                        View linked Journal Event
                      </a>
                    )}
                    {item?.status === "completed" && !item.linked_event_id && (
                      <p>Completed without a Journal Event.</p>
                    )}
                  </>
                ) : dialog.action === "cancel" ? (
                  <p>
                    Cancel this intention? The planning record will remain
                    available under Cancelled.
                  </p>
                ) : (
                  <fieldset disabled={busy}>
                    <p>
                      Completion closes this intention. Choose explicitly
                      whether to record what happened.
                    </p>
                    <label>
                      <input
                        type="radio"
                        name="completion"
                        checked={!recordEvent}
                        onChange={() => {
                          setRecordEvent(false);
                        }}
                      />{" "}
                      Complete without a Journal Event
                    </label>
                    {possible ? (
                      <label>
                        <input
                          type="radio"
                          name="completion"
                          checked={recordEvent}
                          onChange={() => {
                            setRecordEvent(true);
                          }}
                        />{" "}
                        Record what happened in Journal
                      </label>
                    ) : (
                      <p>
                        This target or activity uses completion without an
                        Event. Record structured Harvests and germination
                        observations in their existing workflows.
                      </p>
                    )}
                    {recordEvent && (
                      <>
                        <label className="field">
                          Event kind
                          <select
                            value={eventKind}
                            onChange={(e) => {
                              setEventKind(
                                e.target.value as ScheduleEvent["kind"],
                              );
                            }}
                          >
                            {possible?.map((k) => (
                              <option key={k} value={k}>
                                {k}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="field">
                          <FieldLabel as="span" required>
                            Actual occurrence date
                          </FieldLabel>
                          <input
                            required
                            type="date"
                            value={actual}
                            onChange={(e) => {
                              setActual(e.target.value);
                            }}
                          />
                        </label>
                        <p className="muted">
                          Confirm the actual day, independently of the scheduled
                          due date.
                        </p>
                        {eventKind === "movement" && (
                          <ScheduleTargetPicker
                            kind="location"
                            value={destination}
                            selected={null}
                            onChange={setDestination}
                          />
                        )}
                        <label className="field">
                          Event notes
                          <textarea
                            value={eventNotes}
                            maxLength={20000}
                            onChange={(e) => {
                              setEventNotes(e.target.value);
                            }}
                          />
                        </label>
                        {eventKind === "movement" && (
                          <p>
                            Recording this Movement also updates the current
                            Location through the existing Event workflow.
                          </p>
                        )}
                      </>
                    )}
                  </fieldset>
                )}
              </>
            )}
          </div>
          <FormActions>
            <button
              type="button"
              className="button--secondary"
              disabled={busy}
              onClick={dismiss}
            >
              {dialog.action === "inspect" ? "Close" : "Cancel"}
            </button>
            {dialog.action !== "inspect" && (
              <button
                type="submit"
                disabled={
                  busy ||
                  ((dialog.action === "create" || dialog.action === "edit") &&
                    Boolean(targetKind) &&
                    !targetId) ||
                  (recordEvent && eventKind === "movement" && !destination)
                }
              >
                {busy
                  ? "Saving…"
                  : dialog.action === "create" || dialog.action === "edit"
                    ? "Save activity"
                    : dialog.action === "cancel"
                      ? "Confirm cancellation"
                      : recordEvent
                        ? "Complete and record Event"
                        : "Complete without Event"}
              </button>
            )}
          </FormActions>
        </form>
      </TaskDialog>
      {confirmDiscard && (
        <TaskDialog
          title="Discard unsaved activity changes?"
          className="schedule-discard-dialog"
          dismissOnBackdrop
          onClose={() => {
            setConfirmDiscard(false);
          }}
        >
          <h3>Discard unsaved activity changes?</h3>
          <p>Your entries will be lost if you discard them.</p>
          <FormActions>
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setConfirmDiscard(false);
              }}
            >
              Continue editing
            </button>
            <button type="button" onClick={onClose}>
              Discard changes
            </button>
          </FormActions>
        </TaskDialog>
      )}
    </>
  );
}

/** An empty filtered page alone cannot prove that its filters removed existing work. */
function EmptyScheduleList({
  state,
  onExpire,
}: {
  state: ScheduleState;
  onExpire: () => void;
}) {
  const filterHash = scheduleHash(state);
  const narrowed = Boolean(
    state.window !== "all" ||
    state.activity_kind.length ||
    state.target_kind.length ||
    state.target_id ||
    state.q,
  );
  const [baseline, setBaseline] = useState<{
    hash: string;
    total: number;
  } | null>(null);
  useEffect(() => {
    if (!narrowed) return;
    const c = new AbortController();
    const status = readScheduleState(filterHash).status;
    void listSchedule({ ...defaultState, status }, 0, 1, c.signal)
      .then((page) => {
        if (!c.signal.aborted)
          setBaseline({ hash: filterHash, total: page.total });
      })
      .catch((error: unknown) => {
        if (
          !c.signal.aborted &&
          error instanceof ApiError &&
          error.status === 401
        )
          onExpire();
      });
    return () => {
      c.abort();
    };
  }, [filterHash, narrowed, onExpire]);
  const total = baseline?.hash === filterHash ? baseline.total : null;
  const filtered = narrowed && total !== 0;
  return (
    <div className="schedule-list-empty" role="status">
      <p>
        {filtered
          ? "No activities match these filters."
          : state.status.length === 1
            ? state.status[0] === "planned"
              ? "No planned activities yet."
              : `No ${state.status[0]} activities.`
            : "No scheduled activities yet."}
      </p>
    </div>
  );
}

export function ScheduleScreen() {
  const auth = useAuth();
  const [state, setState] = useState(readScheduleState);
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    page: SchedulePage | null;
    error: boolean;
  } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [day, setDay] = useState(localDay);
  const csrf =
    auth.state.status === "authenticated" ? auth.state.csrfToken : "";
  const owner =
    auth.state.status === "authenticated" && auth.state.session.owner;
  const expire = useCallback(() => {
    auth.sessionExpired();
  }, [auth]);
  const queryHash = scheduleHash({
    ...state,
    date: state.view === "calendar" ? "" : state.date,
  });
  const key = JSON.stringify([queryHash, offset, attempt, day]);
  const current = result?.key === key ? result : null;
  const page = current?.page;
  const loadError = current?.error ?? false;
  const projectionDay = page?.today ?? day;
  useEffect(() => {
    const timer = window.setInterval(() => {
      setDay(localDay());
    }, 30000);
    return () => {
      window.clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    const c = new AbortController();
    const queryState = readScheduleState(queryHash);
    void (
      queryState.view === "calendar"
        ? listCalendar(queryState, c.signal)
        : listSchedule(
            queryState,
            offset,
            50,
            c.signal,
            queryState.date || undefined,
          )
    )
      .then((value) => {
        if (c.signal.aborted) return;
        if (queryState.view === "list" && offset > 0 && !value.items.length)
          setOffset(0);
        else setResult({ key, page: value, error: false });
      })
      .catch((e: unknown) => {
        if (c.signal.aborted) return;
        if (e instanceof ApiError && e.status === 401) expire();
        else setResult({ key, page: null, error: true });
      });
    return () => {
      c.abort();
    };
  }, [queryHash, offset, key, expire]);
  const route = useCallback(() => {
    setState((previous) => {
      const next = readScheduleState();
      return scheduleHash(previous) === scheduleHash(next) ? previous : next;
    });
    setOffset(0);
    const [path, query = ""] = window.location.hash.split("?", 2);
    const p = new URLSearchParams(query);
    const id = path.split("/")[2];
    setError("");
    setDialog(null);
    const c = new AbortController();
    if (id) {
      void getActivity(id, c.signal)
        .then((item) => {
          if (!c.signal.aborted)
            setDialog({ action: "inspect", item, target: item.target });
        })
        .catch((e: unknown) => {
          if (c.signal.aborted) return;
          if (e instanceof ApiError && e.status === 401) expire();
          else
            setNotice(
              "Could not load this scheduled activity. Open Schedule and try again.",
            );
        });
    } else if (p.get("action") === "create") {
      const parsed = readScheduleState();
      if (parsed.target_kind.length === 1 && parsed.target_id)
        void getTarget(parsed.target_kind[0], parsed.target_id, c.signal)
          .then((target) => {
            if (!c.signal.aborted)
              setDialog({ action: "create", item: null, target });
          })
          .catch((e: unknown) => {
            if (c.signal.aborted) return;
            if (e instanceof ApiError && e.status === 401) expire();
            else
              setNotice(
                "The selected target could not be loaded. Reload its detail before scheduling work.",
              );
          });
      else setDialog({ action: "create", item: null, target: null });
    }
    return () => {
      c.abort();
    };
  }, [expire]);
  useEffect(() => {
    let disposed = false;
    let clean: (() => void) | undefined;
    queueMicrotask(() => {
      if (!disposed) clean = route();
    });
    const sync = () => {
      clean?.();
      clean = route();
    };
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      disposed = true;
      clean?.();
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, [route]);
  function update(next: ScheduleState, typing = false) {
    if (typing) window.history.replaceState(null, "", scheduleHash(next));
    else window.history.pushState(null, "", scheduleHash(next));
    setState(next);
    setOffset(0);
  }
  function close() {
    setDialog(null);
    setError("");
    window.history.replaceState(null, "", scheduleHash(state));
  }
  async function save(work: () => Promise<Activity>) {
    setBusy(true);
    setError("");
    try {
      const saved = await work();
      setNotice(
        `Activity ${saved.status === "planned" ? "saved" : saved.status}${saved.linked_event_id ? " with a linked Journal Event" : ""}.`,
      );
      close();
      setOffset(0);
      setAttempt((a) => a + 1);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) expire();
      else setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  function open(action: Dialog["action"], item: Activity | null = null) {
    setError("");
    setDialog({ action, item, target: item?.target ?? null });
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
      setAttempt((a) => a + 1);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) expire();
      else setError("Could not reload the current activity. Try again.");
    } finally {
      setBusy(false);
    }
  }
  const groups = [
    "Overdue",
    "Today",
    "Next 7 days",
    "Later",
    "Completed",
    "Cancelled",
  ];
  const viewSwitcher = (
    <nav className="schedule-view-switch" aria-label="Schedule view">
      {(["list", "calendar"] as const).map((view) => (
        <a
          key={view}
          href={scheduleHash({ ...state, view })}
          aria-current={state.view === view ? "page" : undefined}
          onClick={(event) => {
            if (
              !event.ctrlKey &&
              !event.metaKey &&
              !event.shiftKey &&
              !event.altKey
            ) {
              event.preventDefault();
              update({ ...state, view });
            }
          }}
        >
          {view === "list" ? "Agenda" : "Month"}
        </a>
      ))}
    </nav>
  );
  function group(item: Activity): string {
    if (item.status !== "planned")
      return item.status === "completed" ? "Completed" : "Cancelled";
    if (item.due_on < projectionDay) return "Overdue";
    if (item.due_on === projectionDay) return "Today";
    const horizon = new Date(`${projectionDay}T12:00:00`);
    horizon.setDate(horizon.getDate() + 7);
    return item.due_on <= localDay(horizon) ? "Next 7 days" : "Later";
  }
  return (
    <ActivityPage
      className="schedule-workspace activity-page"
      titleId="schedule-title"
      header={
        <ActivityPageHeader
          name="Schedule"
          titleId="schedule-title"
          subtitle="Future work planned for your collection."
          query={state.q}
          onSearch={(q) => {
            update({ ...state, q }, true);
          }}
          resetFilters={() => {
            update({
              ...defaultState,
              status: [],
              q: state.q,
              view: state.view,
              month: state.month,
              date: state.date,
            });
          }}
          primaryAction={
            owner && (
              <button
                type="button"
                className="schedule-create"
                aria-label="Schedule activity"
                onClick={() => {
                  setDialog({
                    action: "create",
                    item: null,
                    target: null,
                    due: state.date || undefined,
                  });
                }}
              >
                + Schedule activity
              </button>
            )
          }
          activeFilters={[
            ...(state.status.length > 0 && state.status.length < 3
              ? [
                  {
                    label: "Status",
                    value: selectionLabel(state.status, statusLabels),
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
            ...(state.activity_kind.length > 0 && state.activity_kind.length < 8
              ? [
                  {
                    label: "Activity kind",
                    value: selectionLabel(state.activity_kind, activityLabels),
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
                    value: selectionLabel(state.target_kind, targetLabels),
                    onRemove: () => {
                      update({ ...state, target_kind: [], target_id: "" });
                    },
                  },
                ]
              : []),
            ...(state.target_id
              ? [
                  {
                    label: "Target",
                    value: "Selected record",
                    onRemove: () => {
                      update({ ...state, target_id: "" });
                    },
                  },
                ]
              : []),
          ]}
        >
          <ActivityChoices
            title="Status"
            labels={statusLabels}
            selected={state.status}
            onChange={(status) => {
              update({ ...state, status: status.length === 3 ? [] : status });
            }}
          />
          <label className="field activity-window-field">
            Date window
            <select
              value={state.window}
              onChange={(event) => {
                update({
                  ...state,
                  window: event.target.value as ScheduleState["window"],
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
        </ActivityPageHeader>
      }
      chronology={
        <>
          <ScheduleNavigation
            state={state}
            today={projectionDay}
            switcher={viewSwitcher}
            onChange={update}
          />
          {page && page.overdue_count > 0 && (
            <p className="schedule-attention">
              <a
                href={scheduleHash({
                  ...state,
                  view: "list",
                  date: "",
                  status: ["planned"],
                  window: "overdue",
                })}
              >
                {page.overdue_count} planned overdue activities in the
                collection
              </a>
            </p>
          )}
          {state.view === "list" && page && (
            <p role="status">
              {page.total} matching activities
              {state.date ? ` on ${state.date}` : ""} · counts below refer to
              this page
            </p>
          )}
          {state.view === "list" && page && <h3>{page.total} activities</h3>}
          {notice && <p role="status">{notice}</p>}
          {state.view === "calendar" ? (
            <ScheduleCalendar
              key={state.month}
              state={state}
              navigation={<></>}
              page={page ?? null}
              error={loadError}
              today={projectionDay}
              owner={owner}
              onChange={update}
              onRetry={() => {
                setAttempt((a) => a + 1);
              }}
              onAction={open}
              onCreate={(due) => {
                setError("");
                setDialog({ action: "create", item: null, target: null, due });
              }}
            />
          ) : loadError ? (
            <div role="alert">
              <p>Florabase could not load Schedule.</p>
              <button
                onClick={() => {
                  setAttempt((a) => a + 1);
                }}
              >
                Retry Schedule
              </button>
            </div>
          ) : !page ? (
            <p role="status">Loading scheduled activities…</p>
          ) : (
            <>
              {!page.items.length && (
                <EmptyScheduleList state={state} onExpire={expire} />
              )}
              {groups.map((heading) => {
                const items = page.items.filter(
                  (item) => group(item) === heading,
                );
                return items.length ? (
                  <section
                    className="schedule-group"
                    key={heading}
                    aria-label={heading}
                  >
                    <h3>{heading}</h3>
                    <ol className="schedule-list">
                      {items.map((item) => (
                        <li key={item.id}>
                          <ScheduleActivityRow
                            item={item}
                            owner={owner}
                            onAction={open}
                            today={projectionDay}
                          />
                        </li>
                      ))}
                    </ol>
                  </section>
                ) : null;
              })}
              {page.items.length > 0 && page.total > 50 && (
                <nav className="button-row" aria-label="Schedule pages">
                  <button
                    disabled={!offset}
                    onClick={() => {
                      setOffset((o) => Math.max(0, o - 50));
                    }}
                  >
                    Previous
                  </button>
                  <span>Page {Math.floor(offset / 50) + 1}</span>
                  <button
                    disabled={offset + 50 >= page.total}
                    onClick={() => {
                      setOffset((o) => o + 50);
                    }}
                  >
                    Next
                  </button>
                </nav>
              )}
            </>
          )}
          {dialog && (
            <ActivityDialog
              key={`${dialog.action}:${dialog.item?.id ?? "new"}:${String(dialog.item?.version ?? 0)}`}
              dialog={dialog}
              busy={busy}
              error={error}
              onClose={close}
              onReload={() => {
                void reload();
              }}
              onSave={(payload) => {
                void save(() =>
                  writeActivity(dialog.item?.id ?? null, payload, csrf),
                );
              }}
              onTransition={(event) => {
                if (dialog.item) {
                  const item = dialog.item;
                  void save(() =>
                    transitionActivity(
                      item,
                      dialog.action === "cancel" ? "cancel" : "complete",
                      csrf,
                      event,
                    ),
                  );
                }
              }}
            />
          )}
        </>
      }
    />
  );
}
