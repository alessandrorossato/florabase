import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { TaskDialog } from "../components/TaskDialog";
import {
  getActivity,
  getTarget,
  listSchedule,
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

function ActivityDialog({
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
  const [due, setDue] = useState(item?.due_on ?? localDay());
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
    <TaskDialog
      title={heading}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
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
        <h3>{heading}</h3>
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
          <fieldset disabled={busy}>
            <label className="field">
              Title
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
              Activity kind
              <select
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
              Due date
              <input
                required
                type="date"
                value={due}
                onChange={(e) => {
                  setDue(e.target.value);
                }}
              />
            </label>
            <p className="muted">
              A complete calendar day. Passing this day leaves the activity
              planned.
            </p>
            <label className="field">
              Target type
              <select
                value={targetKind}
                onChange={(e) => {
                  setTargetKind(e.target.value as TargetKind | "");
                  setTargetId("");
                }}
              >
                <option value="">Whole collection / no specific record</option>
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
            <label className="field">
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
                <a href={targetHref(item.target)}>{item.target.label}</a>
                {item.target.lifecycle && item.target.lifecycle !== "active"
                  ? ` (${item.target.lifecycle})`
                  : ""}
              </p>
            )}
            {dialog.action === "inspect" ? (
              <>
                <p>Status: {item?.status}</p>
                {item?.notes && <p className="schedule-notes">{item.notes}</p>}
                {item?.completed_at && (
                  <p>
                    Completed: {new Date(item.completed_at).toLocaleString()}
                  </p>
                )}
                {item?.cancelled_at && (
                  <p>
                    Cancelled: {new Date(item.cancelled_at).toLocaleString()}
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
                Cancel this intention? The planning record will remain available
                under Cancelled.
              </p>
            ) : (
              <fieldset disabled={busy}>
                <p>
                  Completion closes this intention. Choose explicitly whether to
                  record what happened.
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
                    This target or activity uses completion without an Event.
                    Record structured Harvests and germination observations in
                    their existing workflows.
                  </p>
                )}
                {recordEvent && (
                  <>
                    <label className="field">
                      Event kind
                      <select
                        value={eventKind}
                        onChange={(e) => {
                          setEventKind(e.target.value as ScheduleEvent["kind"]);
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
                      Actual occurrence date
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
                      Confirm the actual day, independently of the scheduled due
                      date.
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
        <div className="button-row">
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
          <button
            type="button"
            className="button--secondary"
            disabled={busy}
            onClick={onClose}
          >
            {dialog.action === "inspect" ? "Close" : "Keep editing / close"}
          </button>
        </div>
      </form>
    </TaskDialog>
  );
}

export function ScheduleScreen() {
  const auth = useAuth();
  const [state, setState] = useState(readScheduleState);
  const [offset, setOffset] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
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
  const key = JSON.stringify([state, offset, attempt, day]);
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
    void listSchedule(state, offset, 50, c.signal)
      .then((value) => {
        if (!c.signal.aborted) setResult({ key, page: value, error: false });
      })
      .catch((e: unknown) => {
        if (c.signal.aborted) return;
        if (e instanceof ApiError && e.status === 401) expire();
        else setResult({ key, page: null, error: true });
      });
    return () => {
      c.abort();
    };
  }, [state, offset, key, expire]);
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
      if (parsed.target_kind && parsed.target_id)
        void getTarget(parsed.target_kind, parsed.target_id, c.signal)
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
  const groups =
    state.status === "planned"
      ? ["Overdue", "Today", "Next 7 days", "Later"]
      : [state.status === "completed" ? "Completed" : "Cancelled"];
  function group(item: Activity): string {
    if (state.status !== "planned") return groups[0] ?? "";
    if (item.due_on < projectionDay) return "Overdue";
    if (item.due_on === projectionDay) return "Today";
    const horizon = new Date(`${projectionDay}T12:00:00`);
    horizon.setDate(horizon.getDate() + 7);
    return item.due_on <= localDay(horizon) ? "Next 7 days" : "Later";
  }
  return (
    <section className="schedule-workspace" aria-labelledby="schedule-title">
      <header className="section-heading">
        <div>
          <p className="eyebrow">Activity</p>
          <h2 id="schedule-title">Schedule</h2>
          <p>
            Future intended collection work. Journal records occurrences;
            History shows recorded facts.
          </p>
        </div>
        {owner && (
          <button
            onClick={() => {
              open("create");
            }}
          >
            Schedule activity
          </button>
        )}
      </header>
      <p className="muted">
        Dates use this device’s calendar day ({projectionDay}). Overdue
        activities remain planned until you complete or cancel them.
      </p>
      {notice && <p role="status">{notice}</p>}
      <div className="button-row">
        <button
          type="button"
          aria-expanded={filtersOpen}
          aria-controls="schedule-filters"
          onClick={() => {
            setFiltersOpen((open) => !open);
          }}
        >
          Filters
        </button>
        <span>
          {state.status === "planned"
            ? "Active"
            : state.status === "completed"
              ? "Completed"
              : "Cancelled"}{" "}
          · {windowLabels[state.window]}
          {state.activity_kind
            ? ` · ${activityLabels[state.activity_kind]}`
            : ""}
          {state.target_kind ? ` · ${targetLabels[state.target_kind]}` : ""}
          {state.q ? ` · Search: ${state.q}` : ""}
        </span>
      </div>
      <div
        id="schedule-filters"
        className="schedule-filters"
        hidden={!filtersOpen}
      >
        <label className="field">
          Status
          <select
            value={state.status}
            onChange={(e) => {
              update({
                ...state,
                status: e.target.value as ScheduleState["status"],
                window: "all",
              });
            }}
          >
            <option value="planned">Active</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
        <label className="field">
          Date window
          <select
            value={state.window}
            onChange={(e) => {
              update({
                ...state,
                window: e.target.value as ScheduleState["window"],
              });
            }}
          >
            {Object.entries(windowLabels)
              .filter(
                ([key]) => state.status === "planned" || key !== "overdue",
              )
              .map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
          </select>
        </label>
        <label className="field">
          Activity kind
          <select
            value={state.activity_kind}
            onChange={(e) => {
              update({
                ...state,
                activity_kind: e.target.value as ScheduleState["activity_kind"],
              });
            }}
          >
            <option value="">All activities</option>
            {Object.entries(activityLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Target type
          <select
            value={state.target_kind}
            onChange={(e) => {
              update({
                ...state,
                target_kind: e.target.value as ScheduleState["target_kind"],
                target_id: "",
              });
            }}
          >
            <option value="">All record types</option>
            {Object.entries(targetLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Search title / notes
          <input
            type="search"
            maxLength={200}
            value={state.q}
            onChange={(e) => {
              update({ ...state, q: e.target.value }, true);
            }}
          />
        </label>
      </div>
      {state.target_id && (
        <p>
          Showing only the selected{" "}
          {state.target_kind && targetLabels[state.target_kind]}.{" "}
          <button
            onClick={() => {
              update({ ...state, target_id: "" });
            }}
          >
            Clear target filter
          </button>
        </p>
      )}
      {loadError ? (
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
          <p>
            {page.total} {state.status === "planned" ? "active" : state.status}{" "}
            activities
          </p>
          {!page.items.length && (
            <div className="empty-state">
              <p>No activities match this view.</p>
              <button
                onClick={() => {
                  update(defaultState);
                }}
              >
                Reset filters
              </button>
            </div>
          )}
          {groups.map((heading) => {
            const items = page.items.filter((item) => group(item) === heading);
            return items.length ? (
              <section key={heading} aria-label={heading}>
                <h3>{heading}</h3>
                <ol className="schedule-list">
                  {items.map((item) => (
                    <li key={item.id}>
                      <div className="schedule-row">
                        <div>
                          <button
                            className="link-button schedule-title"
                            onClick={() => {
                              open("inspect", item);
                            }}
                          >
                            {item.title}
                          </button>
                          <p>
                            <time dateTime={item.due_on}>{item.due_on}</time> ·{" "}
                            {activityLabels[item.activity_kind]} ·{" "}
                            <strong>
                              {item.overdue ? "Planned · Overdue" : item.status}
                            </strong>
                          </p>
                          {item.target ? (
                            <p>
                              {targetLabels[item.target.kind]}:{" "}
                              <a href={targetHref(item.target)}>
                                {item.target.label}
                              </a>
                              {item.target.lifecycle &&
                                item.target.lifecycle !== "active" &&
                                ` (${item.target.lifecycle})`}
                            </p>
                          ) : (
                            <p>Whole collection</p>
                          )}
                          {item.notes && (
                            <p className="schedule-notes">
                              {item.notes.length > 240
                                ? `${item.notes.slice(0, 240)}…`
                                : item.notes}
                            </p>
                          )}
                          {item.linked_event_id && item.target && (
                            <a href={`${targetHref(item.target)}?tab=events`}>
                              Linked Journal Event
                            </a>
                          )}
                          {item.status === "completed" &&
                            !item.linked_event_id && (
                              <p>Completed without a Journal Event</p>
                            )}
                        </div>
                        {owner && item.status === "planned" && (
                          <div className="button-row">
                            <button
                              className="button--secondary"
                              onClick={() => {
                                open("edit", item);
                              }}
                            >
                              Edit / reschedule
                            </button>
                            <button
                              className="button--secondary"
                              onClick={() => {
                                open("complete", item);
                              }}
                            >
                              Complete
                            </button>
                            <button
                              className="button--secondary"
                              onClick={() => {
                                open("cancel", item);
                              }}
                            >
                              Cancel activity
                            </button>
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            ) : null;
          })}
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
    </section>
  );
}
