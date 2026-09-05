import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import type { LocationResponse } from "../locations/api";
import { PartialDateField } from "../seed-lots/PartialDateField";
import type { PartialDate } from "../seed-lots/api";
import {
  createEvent,
  deleteEvent,
  listEvents,
  updateEvent,
  type EventKind,
  type EventResponse,
  type EventTargetKind,
} from "./api";

type TimelineState =
  | { status: "loading" }
  | { status: "ready"; events: EventResponse[] }
  | { status: "error" };
type EventFilter = "all" | "observations" | "cultivation" | "status";
type MutationState =
  | { status: "idle" }
  | { status: "pending" }
  | { status: "error"; message: string };
interface JournalNotice {
  tone: "success" | "error";
  message: string;
}

interface EventFormState {
  kind: EventKind;
  occurredOn: PartialDate | null;
  notes: string;
  destinationLocationId: string;
  recipient: string;
  resultingPlantId: string;
}

const eventKindLabels: Record<EventKind, string> = {
  observation: "Observation",
  movement: "Movement",
  repotting: "Repotting",
  flowering: "Flowering",
  fruiting: "Fruiting",
  pruning: "Pruning",
  treatment: "Treatment",
  harvest: "Harvest",
  extraction: "Extraction",
  transfer: "Transfer",
  death: "Death",
  loss: "Loss",
  discarded: "Discarded",
  other: "Other",
};

const filterKinds: Record<Exclude<EventFilter, "all">, EventKind[]> = {
  observations: ["observation", "flowering", "fruiting"],
  cultivation: [
    "movement",
    "repotting",
    "pruning",
    "treatment",
    "harvest",
    "extraction",
  ],
  status: ["transfer", "death", "loss", "discarded"],
};

const lifecycleKinds = new Set<EventKind>([
  "transfer",
  "death",
  "loss",
  "discarded",
]);

function blankForm(): EventFormState {
  return {
    kind: "observation",
    occurredOn: null,
    notes: "",
    destinationLocationId: "",
    recipient: "",
    resultingPlantId: "",
  };
}

function formFrom(event: EventResponse): EventFormState {
  return {
    kind: event.kind,
    occurredOn: event.occurred_on,
    notes: event.notes ?? "",
    destinationLocationId: event.destination_location_id ?? "",
    recipient: event.recipient ?? "",
    resultingPlantId: event.resulting_plant_id ?? "",
  };
}

function partialDateLabel(value: PartialDate | null): string {
  if (!value) return "Date unknown";
  const year = String(value.year).padStart(4, "0");
  if (value.precision === "year") return year;
  const month = String(value.month).padStart(2, "0");
  if (value.precision === "month") return `${year}-${month}`;
  return `${year}-${month}-${String(value.day).padStart(2, "0")}`;
}

function EventDialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const titleId = useId();
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    dialog.current
      ?.querySelector<HTMLElement>("select, input, textarea, button")
      ?.focus();
  }, []);
  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="context-dialog event-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        ref={dialog}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            onClose();
            return;
          }
          if (event.key !== "Tab" || !dialog.current) return;
          const focusable = Array.from(
            dialog.current.querySelectorAll<HTMLElement>(
              "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])",
            ),
          );
          const first = focusable.at(0);
          const last = focusable.at(-1);
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last?.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first?.focus();
          }
        }}
      >
        <h3 id={titleId}>{title}</h3>
        {children}
      </div>
    </div>
  );
}

export function EventJournal({
  targetKind,
  targetId,
  targetLabel,
  locations,
  onTargetRefresh,
}: {
  targetKind: EventTargetKind;
  targetId: string;
  targetLabel: string;
  locations: LocationResponse[];
  onTargetRefresh: () => Promise<void>;
}) {
  const auth = useAuth();
  const [timeline, setTimeline] = useState<TimelineState>({
    status: "loading",
  });
  const [attempt, setAttempt] = useState(0);
  const [filter, setFilter] = useState<EventFilter>("all");
  const [editor, setEditor] = useState<EventResponse | "create" | null>(null);
  const [deleting, setDeleting] = useState<EventResponse | null>(null);
  const [form, setForm] = useState<EventFormState>(blankForm);
  const [mutation, setMutation] = useState<MutationState>({ status: "idle" });
  const [notice, setNotice] = useState<JournalNotice | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void listEvents(targetKind, targetId, controller.signal)
      .then((events) => {
        setTimeline({ status: "ready", events });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setTimeline({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, auth, targetId, targetKind]);

  const visible = useMemo(() => {
    if (timeline.status !== "ready") return [];
    if (filter === "all") return timeline.events;
    return timeline.events.filter((event) =>
      filterKinds[filter].includes(event.kind),
    );
  }, [filter, timeline]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;
  const pending = mutation.status === "pending";

  async function refreshTimeline() {
    const events = await listEvents(targetKind, targetId);
    setTimeline({ status: "ready", events });
  }

  function openCreate() {
    setForm(blankForm());
    setMutation({ status: "idle" });
    setNotice(null);
    setEditor("create");
  }

  function openEdit(event: EventResponse) {
    setForm(formFrom(event));
    setMutation({ status: "idle" });
    setNotice(null);
    setEditor(event);
  }

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor || pending) return;
    if (form.kind === "movement" && !form.destinationLocationId) {
      setMutation({
        status: "error",
        message: "Choose the destination Location for this movement.",
      });
      return;
    }
    const payload = {
      kind: form.kind,
      occurred_on: form.occurredOn,
      notes: form.notes.trim() || null,
      destination_location_id:
        form.kind === "movement" ? form.destinationLocationId : null,
      recipient:
        form.kind === "transfer" ? form.recipient.trim() || null : null,
      resulting_plant_id:
        form.kind === "extraction" ? form.resultingPlantId : null,
    };
    setMutation({ status: "pending" });
    try {
      const creating = editor === "create";
      if (creating) await createEvent(targetKind, targetId, payload, csrfToken);
      else await updateEvent(editor.id, payload, csrfToken);
      setEditor(null);
      setMutation({ status: "idle" });
      let historyRefreshFailed = false;
      try {
        await refreshTimeline();
      } catch {
        historyRefreshFailed = true;
        setTimeline({ status: "error" });
      }
      let targetRefreshFailed = false;
      if (creating)
        try {
          await onTargetRefresh();
        } catch {
          targetRefreshFailed = true;
        }
      setNotice(
        historyRefreshFailed || targetRefreshFailed
          ? {
              tone: "error",
              message: historyRefreshFailed
                ? creating
                  ? "The Event was added, but Florabase could not refresh its history. Retry the Event history and reload the record before making another change."
                  : "The Event changes were saved, but Florabase could not refresh the history. Retry the Event history before making another change."
                : "The Event was added and its history refreshed, but Florabase could not refresh the current record. Reload the record before making another change.",
            }
          : {
              tone: "success",
              message: creating
                ? "Event was added."
                : "Event changes were saved.",
            },
      );
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
        return;
      }
      setMutation({
        status: "error",
        message:
          error instanceof ApiError && error.status === 422
            ? "Check the Event details and try again."
            : "Florabase could not save or refresh this Event. Check the connection and try again.",
      });
    }
  }

  async function confirmDelete() {
    if (!deleting || pending) return;
    setMutation({ status: "pending" });
    try {
      await deleteEvent(deleting.id, csrfToken);
      setDeleting(null);
      setMutation({ status: "idle" });
      try {
        await refreshTimeline();
        setNotice({
          tone: "success",
          message: "Event was deleted from the history.",
        });
      } catch {
        setTimeline({ status: "error" });
        setNotice({
          tone: "error",
          message:
            "The Event was deleted, but Florabase could not refresh the history. Retry the Event history before making another change.",
        });
      }
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        auth.sessionExpired();
        return;
      }
      setMutation({
        status: "error",
        message:
          "Florabase could not delete this Event. Check the connection and try again.",
      });
    }
  }

  return (
    <section className="event-journal" aria-labelledby={`events-${targetId}`}>
      <div className="event-heading">
        <div>
          <p className="eyebrow">Journal</p>
          <h4 id={`events-${targetId}`}>Events</h4>
        </div>
        <button type="button" onClick={openCreate}>
          Add event
        </button>
      </div>
      <p className="field-help">
        Observations and cultivation changes recorded for {targetLabel}.
      </p>
      {notice && (
        <div
          className={`notice notice--${notice.tone}`}
          role={notice.tone === "error" ? "alert" : "status"}
        >
          {notice.message}
        </div>
      )}
      {timeline.status === "loading" ? (
        <p role="status">Loading Events…</p>
      ) : timeline.status === "error" ? (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load this Event history.</p>
          <button
            type="button"
            onClick={() => {
              setTimeline({ status: "loading" });
              setAttempt((value) => value + 1);
            }}
          >
            Retry Events
          </button>
        </div>
      ) : timeline.events.length === 0 ? (
        <div className="event-empty">
          <h5>No Events recorded yet</h5>
          <p>
            Events build a history of observations, cultivation work, movement,
            and status changes.
          </p>
          <button type="button" onClick={openCreate}>
            Add the first event
          </button>
        </div>
      ) : (
        <>
          <fieldset className="lifecycle-filter event-filters">
            <legend>Filter Events</legend>
            {(["all", "observations", "cultivation", "status"] as const).map(
              (item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={filter === item}
                  onClick={() => {
                    setFilter(item);
                  }}
                >
                  {item === "all"
                    ? "All"
                    : item === "observations"
                      ? "Observations"
                      : item === "cultivation"
                        ? "Cultivation"
                        : "Status"}
                </button>
              ),
            )}
          </fieldset>
          {visible.length === 0 ? (
            <p>No Events match this filter.</p>
          ) : (
            <ol className="event-timeline" aria-label="Event history">
              {visible.map((item) => (
                <li
                  className={`event-item event-item--${item.kind}`}
                  key={item.id}
                >
                  <div className="event-marker" aria-hidden="true" />
                  <article className="event-card">
                    <div className="event-card-heading">
                      <div>
                        <h5>{eventKindLabels[item.kind]}</h5>
                        <time>{partialDateLabel(item.occurred_on)}</time>
                      </div>
                      <div
                        className="event-actions"
                        aria-label={`${eventKindLabels[item.kind]} actions`}
                      >
                        <button
                          type="button"
                          className="button--secondary"
                          onClick={() => {
                            openEdit(item);
                          }}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="button--secondary"
                          onClick={() => {
                            setMutation({ status: "idle" });
                            setNotice(null);
                            setDeleting(item);
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    {item.destination_location && (
                      <p className="event-destination">
                        <strong>Destination:</strong>{" "}
                        {item.destination_location.display_path}
                      </p>
                    )}
                    {item.recipient && (
                      <p className="event-destination">
                        <strong>Recipient:</strong> {item.recipient}
                      </p>
                    )}
                    {item.kind === "extraction" && item.resulting_plant && (
                      <p className="event-destination">
                        <strong>1 individual extracted</strong>
                        {" → "}
                        <a href={`#/plants/${item.resulting_plant.id}`}>
                          {item.resulting_plant.label ??
                            item.resulting_plant.botanical_identity
                              .display_label}
                        </a>
                      </p>
                    )}
                    {item.notes && <p className="event-notes">{item.notes}</p>}
                  </article>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
      {editor && (
        <EventDialog
          title={editor === "create" ? "Add event" : "Edit event"}
          onClose={() => {
            if (!pending) setEditor(null);
          }}
        >
          <form
            className="event-form"
            onSubmit={(event) => void submit(event)}
            noValidate
          >
            <div className="field">
              <label htmlFor={`event-kind-${targetId}`}>Event kind</label>
              <select
                id={`event-kind-${targetId}`}
                value={form.kind}
                disabled={pending}
                onChange={(event) => {
                  const kind = event.currentTarget.value as EventKind;
                  setForm((current) => ({
                    ...current,
                    kind,
                    destinationLocationId:
                      kind === "movement" ? current.destinationLocationId : "",
                  }));
                  setMutation({ status: "idle" });
                }}
              >
                {(Object.keys(eventKindLabels) as EventKind[])
                  .filter(
                    (kind) =>
                      kind !== "extraction" ||
                      (editor !== "create" && editor.kind === "extraction"),
                  )
                  .map((kind) => (
                    <option value={kind} key={kind}>
                      {eventKindLabels[kind]}
                    </option>
                  ))}
              </select>
            </div>
            <PartialDateField
              id={`event-date-${targetId}`}
              label="Occurrence date"
              value={form.occurredOn}
              disabled={pending}
              onChange={(value) => {
                setForm((current) => ({ ...current, occurredOn: value }));
              }}
            />
            {form.kind === "movement" && (
              <div className="field">
                <label htmlFor={`event-destination-${targetId}`}>
                  Destination Location
                </label>
                <select
                  id={`event-destination-${targetId}`}
                  required
                  value={form.destinationLocationId}
                  disabled={pending}
                  onChange={(event) => {
                    const destinationLocationId = event.currentTarget.value;
                    setForm((current) => ({
                      ...current,
                      destinationLocationId,
                    }));
                    setMutation({ status: "idle" });
                  }}
                >
                  <option value="">Choose a Location</option>
                  {locations.map((location) => (
                    <option
                      value={location.id}
                      key={location.id}
                      disabled={Boolean(location.retired_at)}
                    >
                      {location.display_path}
                      {location.retired_at ? " (retired)" : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {form.kind === "transfer" && (
              <div className="field">
                <label htmlFor={`event-recipient-${targetId}`}>
                  Recipient <span className="optional">(optional)</span>
                </label>
                <input
                  id={`event-recipient-${targetId}`}
                  value={form.recipient}
                  disabled={pending}
                  maxLength={255}
                  onChange={(event) => {
                    const recipient = event.currentTarget.value;
                    setForm((current) => ({ ...current, recipient }));
                  }}
                />
              </div>
            )}
            <div className="field">
              <label htmlFor={`event-notes-${targetId}`}>
                Notes <span className="optional">(optional)</span>
              </label>
              <textarea
                id={`event-notes-${targetId}`}
                value={form.notes}
                disabled={pending}
                onChange={(event) => {
                  const notes = event.currentTarget.value;
                  setForm((current) => ({ ...current, notes }));
                }}
              />
            </div>
            {editor === "create" && form.kind === "movement" && (
              <p className="notice event-effect">
                Creating this Event also changes the current Location of this
                record.
              </p>
            )}
            {editor === "create" && lifecycleKinds.has(form.kind) && (
              <p className="notice event-effect">
                Creating this Event also changes the current lifecycle of this
                record to {eventKindLabels[form.kind].toLocaleLowerCase()}.
              </p>
            )}
            {editor !== "create" && (
              <p className="notice event-effect">
                Editing changes history only. It does not move the record again,
                change its current lifecycle, or undo an earlier state change.
              </p>
            )}
            {mutation.status === "error" && (
              <div className="notice notice--error" role="alert">
                {mutation.message}
              </div>
            )}
            <div className="actions">
              <button type="submit" disabled={pending}>
                {pending
                  ? "Saving…"
                  : editor === "create"
                    ? "Add event"
                    : "Save changes"}
              </button>
              <button
                type="button"
                className="button--secondary"
                disabled={pending}
                onClick={() => {
                  setEditor(null);
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </EventDialog>
      )}
      {deleting && (
        <EventDialog
          title={`Delete ${eventKindLabels[deleting.kind]} event?`}
          onClose={() => {
            if (!pending) setDeleting(null);
          }}
        >
          <p>
            Deleting this Event removes it from the history. It does not undo
            changes previously made to the record’s current Location or
            lifecycle.
          </p>
          {mutation.status === "error" && (
            <div className="notice notice--error" role="alert">
              {mutation.message}
            </div>
          )}
          <div className="actions">
            <button
              type="button"
              disabled={pending}
              onClick={() => void confirmDelete()}
            >
              {pending ? "Deleting…" : "Delete event"}
            </button>
            <button
              type="button"
              className="button--secondary"
              disabled={pending}
              onClick={() => {
                setDeleting(null);
              }}
            >
              Cancel
            </button>
          </div>
        </EventDialog>
      )}
    </section>
  );
}
