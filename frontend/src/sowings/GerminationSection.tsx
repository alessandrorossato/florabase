import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { FieldHelp } from "../components/ContextualHelp";
import {
  deleteGerminationObservation,
  getSowingGermination,
  saveGerminationObservation,
  type GerminationObservationResponse,
  type SowingGerminationDetail,
} from "./api";

type Editor =
  | { kind: "add" }
  | { kind: "edit"; observation: GerminationObservationResponse }
  | { kind: "delete"; observation: GerminationObservationResponse };

function metric(value: string | number | null, unavailable: string): string {
  return value === null ? unavailable : String(value);
}

function decimal(value: string): string {
  const [whole, fraction = ""] = value.split(".");
  const hundredths = fraction.slice(0, 2).padEnd(2, "0");
  const rounded =
    BigInt(whole) * 100n +
    BigInt(hundredths) +
    (Number(fraction.charAt(2) || "0") >= 5 ? 1n : 0n);
  const integer = String(rounded / 100n);
  const decimals = String(rounded % 100n)
    .padStart(2, "0")
    .replace(/0+$/, "");
  return decimals ? `${integer}.${decimals}` : integer;
}

function errorMessage(error: unknown): string {
  if (
    error instanceof ApiError &&
    typeof error.body === "object" &&
    error.body !== null
  ) {
    const detail = "detail" in error.body ? error.body.detail : null;
    if (
      typeof detail === "object" &&
      detail !== null &&
      "message" in detail &&
      typeof detail.message === "string"
    )
      return detail.message;
  }
  if (error instanceof ApiError && error.status === 422)
    return "Enter an exact date and a non-negative whole number.";
  return "Florabase could not save the observation. Check the connection and try again.";
}

export function GerminationSection({ sowingId }: { sowingId: string }) {
  const auth = useAuth();
  const [detail, setDetail] = useState<SowingGerminationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [date, setDate] = useState("");
  const [count, setCount] = useState("");
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void getSowingGermination(sowingId, controller.signal)
      .then((value) => {
        setDetail(value);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401)
          auth.sessionExpired();
        else setLoadError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
    };
  }, [auth, retry, sowingId]);

  useEffect(() => {
    if (!editor) return;
    dialogRef.current?.querySelector<HTMLElement>("input, button")?.focus();
  }, [editor]);

  function open(next: Editor, trigger: HTMLElement) {
    returnFocus.current = trigger;
    setEditor(next);
    setDate(next.kind === "add" ? "" : next.observation.observed_on);
    setCount(
      next.kind === "add"
        ? ""
        : String(next.observation.newly_germinated_count),
    );
    setFeedback("");
  }

  function close() {
    setEditor(null);
    setFeedback("");
    window.setTimeout(() => returnFocus.current?.focus(), 0);
  }

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!editor || editor.kind === "delete" || saving) return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^(0|[1-9]\d*)$/.test(count)) {
      setFeedback("Enter an exact date and a non-negative whole number.");
      return;
    }
    if (auth.state.status !== "authenticated") return;
    setSaving(true);
    setFeedback("");
    try {
      const value = await saveGerminationObservation(
        sowingId,
        { observed_on: date, newly_germinated_count: Number(count) },
        auth.state.csrfToken,
        editor.kind === "edit" ? editor.observation.id : undefined,
      );
      setDetail(value);
      close();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else setFeedback(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (
      editor?.kind !== "delete" ||
      saving ||
      auth.state.status !== "authenticated"
    )
      return;
    setSaving(true);
    setFeedback("");
    try {
      const value = await deleteGerminationObservation(
        sowingId,
        editor.observation.id,
        auth.state.csrfToken,
      );
      setDetail(value);
      close();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401)
        auth.sessionExpired();
      else setFeedback(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p role="status">Loading germination observations…</p>;
  if (loadError || !detail)
    return (
      <div className="notice notice--error" role="alert">
        Could not load germination observations.{" "}
        <button
          type="button"
          onClick={() => {
            setLoading(true);
            setLoadError(false);
            setRetry((value) => value + 1);
          }}
        >
          Retry
        </button>
      </div>
    );

  const summary = detail.summary;
  const exactCount =
    detail.quantity?.kind === "seed_count" && !detail.quantity.is_approximate;
  const exactDate = detail.sowing_date?.precision === "day";
  const canEdit = auth.state.status === "authenticated";
  return (
    <section
      className="germination-section"
      aria-labelledby="germination-title"
    >
      <div className="germination-heading">
        <div>
          <h3 id="germination-title">Germination</h3>
          <p className="field-help">
            The simple total is maintained separately from dated observations.
            They can differ.
          </p>
        </div>
        {canEdit && (
          <button
            type="button"
            onClick={(event) => {
              open({ kind: "add" }, event.currentTarget);
            }}
          >
            Add observation
          </button>
        )}
      </div>
      <dl className="germination-metrics">
        <div>
          <dt>Simple germinated total</dt>
          <dd>{metric(detail.simple_germinated_count, "Not recorded")}</dd>
        </div>
        <div>
          <dt>Observed germinations</dt>
          <dd>{summary.observed_cumulative_count}</dd>
        </div>
        <div>
          <dt>Observed germination</dt>
          <dd>
            {summary.germination_percentage === null
              ? exactCount
                ? "Not enough data"
                : "Exact seed count required"
              : `${decimal(summary.germination_percentage)}%`}
          </dd>
        </div>
        <div>
          <dt>First germination</dt>
          <dd>{metric(summary.first_germination_on, "Not observed")}</dd>
        </div>
        <div>
          <dt>Days to first</dt>
          <dd>
            {summary.days_to_first_germination === null
              ? exactDate
                ? "Not enough data"
                : "Exact sowing date required"
              : `${String(summary.days_to_first_germination)} days`}
          </dd>
        </div>
        <div>
          <dt>Time to 50% (T50)</dt>
          <dd>
            {summary.t50_days === null
              ? !exactCount
                ? "Exact seed count required"
                : !exactDate
                  ? "Exact sowing date required"
                  : "50% threshold not reached"
              : `Estimated ${decimal(summary.t50_days)} days`}
          </dd>
        </div>
      </dl>
      <p className="field-help">
        Time to 50% estimates when recorded cumulative germination reached half
        of the exact seeds sown. Timing requires an exact sowing date;
        percentages require an exact seed count.
      </p>
      <div className="germination-heading">
        <h4>Observation history</h4>
        {summary.last_observation_on && (
          <small>Last checked {summary.last_observation_on}</small>
        )}
      </div>
      {detail.observations.length === 0 ? (
        <p>
          No dated observations yet. Basic Sowing use does not require them.
        </p>
      ) : (
        <table className="germination-history">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">New</th>
              <th scope="col">Cumulative</th>
              <th scope="col">Days since sowing</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {detail.observations.map((observation, index) => {
              const point = summary.cumulative_series[index];
              return (
                <tr key={observation.id}>
                  <th scope="row" data-label="Date">
                    {observation.observed_on}
                  </th>
                  <td data-label="New">{observation.newly_germinated_count}</td>
                  <td data-label="Cumulative">
                    {point.cumulative_germinated_count}
                  </td>
                  <td data-label="Days since sowing">
                    {metric(point.days_since_sowing, "Not available")}
                  </td>
                  <td data-label="Actions" className="germination-actions">
                    {canEdit && (
                      <>
                        <button
                          type="button"
                          className="button--secondary"
                          onClick={(event) => {
                            open(
                              { kind: "edit", observation },
                              event.currentTarget,
                            );
                          }}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="button--secondary"
                          onClick={(event) => {
                            open(
                              { kind: "delete", observation },
                              event.currentTarget,
                            );
                          }}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {editor && (
        <div
          className="dialog-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !saving) close();
          }}
        >
          <div
            className="context-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="germination-dialog-title"
            ref={dialogRef}
            onKeyDown={(event) => {
              if (event.key === "Escape" && !saving) close();
              if (event.key !== "Tab" || !dialogRef.current) return;
              const focusable = Array.from(
                dialogRef.current.querySelectorAll<HTMLElement>(
                  "button:not([disabled]), input:not([disabled])",
                ),
              );
              if (event.shiftKey && document.activeElement === focusable[0]) {
                event.preventDefault();
                focusable.at(-1)?.focus();
              } else if (
                !event.shiftKey &&
                document.activeElement === focusable.at(-1)
              ) {
                event.preventDefault();
                focusable[0]?.focus();
              }
            }}
          >
            <h3 id="germination-dialog-title">
              {editor.kind === "add"
                ? "Add germination observation"
                : editor.kind === "edit"
                  ? "Edit germination observation"
                  : "Delete germination observation"}
            </h3>
            {editor.kind === "delete" ? (
              <>
                <p>
                  Remove the observation from {editor.observation.observed_on}?
                  Derived statistics will be recalculated. The simple germinated
                  total will not change.
                </p>
                <div className="actions">
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={saving}
                    onClick={close}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => void remove()}
                  >
                    {saving ? "Deleting…" : "Delete observation"}
                  </button>
                </div>
              </>
            ) : (
              <form onSubmit={(event) => void submit(event)}>
                <div className="field">
                  <label htmlFor="germination-observed-on">Date</label>
                  <input
                    id="germination-observed-on"
                    type="date"
                    required
                    value={date}
                    disabled={saving}
                    onChange={(event) => {
                      setDate(event.currentTarget.value);
                    }}
                  />
                </div>
                <div className="field">
                  <label htmlFor="germination-new-count">
                    Newly germinated
                  </label>
                  <input
                    id="germination-new-count"
                    aria-describedby="germination-new-count-help"
                    type="number"
                    min="0"
                    step="1"
                    required
                    value={count}
                    disabled={saving}
                    onChange={(event) => {
                      setCount(event.currentTarget.value);
                    }}
                  />
                  <FieldHelp id="germination-new-count-help">
                    Count new germinations since the previous recorded
                    observation. Zero means you checked and saw none. Cumulative
                    totals are calculated automatically.
                  </FieldHelp>
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={saving}
                    onClick={close}
                  >
                    Cancel
                  </button>
                  <button type="submit" disabled={saving}>
                    {saving ? "Saving…" : "Save observation"}
                  </button>
                </div>
              </form>
            )}
            {feedback && (
              <p className="notice notice--error" role="alert">
                {feedback}
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
