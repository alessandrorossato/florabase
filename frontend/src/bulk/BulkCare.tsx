import { useId, useRef, useState } from "react";
import {
  activeCsrfToken,
  ApiError,
  isExpectedAuthCancellation,
} from "../auth/api";
import { useAuth } from "../auth/context";
import { FieldLabel } from "../components/FieldLabel";
import { TaskDialog } from "../components/TaskDialog";
import { OccurrenceDateChoice } from "../events/OccurrenceDateChoice";
import { localDay } from "../schedule/calendar";
import type { PartialDate } from "../seed-lots/api";
import { hasDateDraft, invalidDateControls } from "../seed-lots/dateControls";
import {
  applyBulkCare,
  bulkCareKeptReasonLabels,
  bulkCareKindLabels,
  bulkCareKinds,
  formatBulkCareSummary,
  previewBulkCare,
  undoBulkCare,
  type BulkCareApplyResponse,
  type BulkCareEventKind,
  type BulkCarePreviewRequest,
  type BulkCarePreviewResponse,
  type BulkCareRecordReference,
  type BulkCareUndoResponse,
} from "./careApi";

export type BulkCareDialogTargets =
  | { mode: "records"; records: BulkCareRecordReference[] }
  | { mode: "location"; locationId: string; locationLabel: string };

function todayPartialDate(): PartialDate {
  const [year, month, day] = localDay().split("-").map(Number);
  return { precision: "day", year, month, day };
}

function plural(count: number, singular: string, pluralWord: string): string {
  return `${String(count)} ${count === 1 ? singular : pluralWord}`;
}

function extractApiError(failure: unknown): {
  code?: string;
  message: string;
} {
  if (failure instanceof ApiError) {
    const body = failure.body;
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as { detail?: { code?: string; message?: string } | string })
            .detail
        : undefined;
    if (typeof detail === "string" && detail.trim()) {
      return { message: detail };
    }
    if (detail && typeof detail === "object" && detail.message) {
      return { code: detail.code, message: detail.message };
    }
    return { message: `Request failed (${String(failure.status)}).` };
  }
  return { message: "Could not reach Florabase. Try again." };
}

export function BulkCareDialog({
  targets,
  onClose,
  onSuccess,
}: {
  targets: BulkCareDialogTargets;
  onClose: () => void;
  onSuccess: (result: BulkCareApplyResponse) => void;
}) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const token = activeCsrfToken(auth.state);
  const kindId = useId();
  const dateId = useId();
  const notesId = useId();
  const sublocationsId = useId();
  const errorId = useId();
  const formRef = useRef<HTMLFormElement>(null);
  const controller = useRef<AbortController | null>(null);

  const [kind, setKind] = useState<BulkCareEventKind>("watering");
  const [occurredOn, setOccurredOn] = useState<PartialDate | null>(() =>
    todayPartialDate(),
  );
  const [notes, setNotes] = useState("");
  const [includeSublocations, setIncludeSublocations] = useState(true);
  const [preview, setPreview] = useState<BulkCarePreviewResponse | null>(null);
  const [busy, setBusy] = useState<"preview" | "apply" | null>(null);
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);

  const title =
    targets.mode === "location"
      ? `Log care in ${targets.locationLabel}`
      : `Log care for ${plural(targets.records.length, "selected record", "selected records")}`;

  function buildRequest(): BulkCarePreviewRequest {
    return {
      targets:
        targets.mode === "location"
          ? {
              location_id: targets.locationId,
              include_sublocations: includeSublocations,
            }
          : { records: targets.records },
      kind,
      occurred_on: occurredOn,
      notes: notes.trim() ? notes : null,
    };
  }

  function handleFailure(failure: unknown) {
    if (isExpectedAuthCancellation(failure)) return;
    if (failure instanceof ApiError && failure.status === 401) {
      sessionExpired();
      return;
    }
    const parsed = extractApiError(failure);
    setStale(parsed.code === "stale_preview");
    setError(parsed.message);
  }

  async function runPreview() {
    if (!authorized || !token) return;
    if (formRef.current) {
      const invalid = invalidDateControls(formRef.current);
      if (invalid.length > 0 || hasDateDraft(formRef.current)) {
        setError("Finish or clear the date before previewing.");
        invalid[0]?.focus();
        return;
      }
    }
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy("preview");
    setError("");
    setStale(false);
    try {
      const next = await previewBulkCare(
        buildRequest(),
        token,
        capability,
        abort.signal,
      );
      if (!abort.signal.aborted) {
        setPreview(next);
      }
    } catch (failure: unknown) {
      if (!abort.signal.aborted) {
        setPreview(null);
        handleFailure(failure);
      }
    } finally {
      if (!abort.signal.aborted) setBusy(null);
    }
  }

  async function runApply() {
    if (!authorized || !token || !preview?.can_apply) return;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy("apply");
    setError("");
    setStale(false);
    try {
      const result = await applyBulkCare(
        {
          ...buildRequest(),
          target_signature: preview.target_signature,
        },
        token,
        capability,
        abort.signal,
      );
      if (!abort.signal.aborted) {
        onSuccess(result);
      }
    } catch (failure: unknown) {
      if (!abort.signal.aborted) {
        handleFailure(failure);
      }
    } finally {
      if (!abort.signal.aborted) setBusy(null);
    }
  }

  const skippedRows = preview?.rows.filter((row) => row.status === "skipped");

  return (
    <TaskDialog
      title={title}
      onClose={onClose}
      dismissOnBackdrop
      className="bulk-move-dialog"
    >
      <h2 className="bulk-move-title">{title}</h2>
      <form
        className="bulk-move-form"
        style={{ display: "grid", gap: "0.75rem" }}
        ref={formRef}
        onSubmit={(event) => {
          event.preventDefault();
          if (preview?.can_apply && !stale) void runApply();
          else void runPreview();
        }}
      >
        <div className="field">
          <FieldLabel required htmlFor={kindId}>
            Care type
          </FieldLabel>
          <select
            id={kindId}
            value={kind}
            disabled={busy !== null}
            onChange={(event) => {
              setKind(event.currentTarget.value as BulkCareEventKind);
              setPreview(null);
              setError("");
              setStale(false);
            }}
          >
            {bulkCareKinds.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        {targets.mode === "location" && (
          <label htmlFor={sublocationsId} className="checkbox-label">
            <input
              id={sublocationsId}
              type="checkbox"
              checked={includeSublocations}
              disabled={busy !== null}
              onChange={(event) => {
                setIncludeSublocations(event.currentTarget.checked);
                setPreview(null);
                setError("");
                setStale(false);
              }}
            />
            Include sub-locations
          </label>
        )}

        <OccurrenceDateChoice
          id={dateId}
          value={occurredOn}
          disabled={busy !== null}
          initialChoice="today"
          onChange={(next) => {
            setOccurredOn(next);
            setPreview(null);
            setError("");
          }}
        />

        <div className="field">
          <FieldLabel htmlFor={notesId}>Notes</FieldLabel>
          <textarea
            id={notesId}
            rows={2}
            maxLength={20_000}
            disabled={busy !== null}
            value={notes}
            placeholder="Optional product, dose, or care details…"
            onChange={(event) => {
              setNotes(event.currentTarget.value);
              setPreview(null);
              setError("");
            }}
          />
        </div>

        {error && (
          <div id={errorId} className="notice notice--error" role="alert">
            <p>{error}</p>
            {stale && (
              <button
                type="button"
                className="button--secondary"
                disabled={busy !== null}
                onClick={() => void runPreview()}
              >
                Refresh preview
              </button>
            )}
          </div>
        )}

        {preview && (
          <section
            className="bulk-preview"
            aria-label="Care log preview"
            aria-live="polite"
          >
            {preview.can_apply ? (
              <p>
                <strong>{formatBulkCareSummary(preview)}</strong>
              </p>
            ) : (
              <div className="notice notice--error" role="alert">
                Nothing to log. There are no active plants or plant groups in
                this scope.
              </div>
            )}
            {skippedRows && skippedRows.length > 0 && (
              <details>
                <summary>
                  {plural(
                    skippedRows.length,
                    "skipped record",
                    "skipped records",
                  )}
                </summary>
                <ul>
                  {skippedRows.map((row) => (
                    <li key={`${row.kind}-${row.id}`}>
                      {row.label} — {row.reason ?? "Skipped"}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </section>
        )}

        <div className="form-actions">
          {!preview ? (
            <button type="submit" disabled={busy !== null || !token}>
              {busy === "preview" ? "Checking targets…" : "Preview care log"}
            </button>
          ) : (
            <>
              <button
                type="submit"
                disabled={
                  busy !== null || !preview.can_apply || stale || !token
                }
              >
                {busy === "apply"
                  ? "Logging…"
                  : `Log for ${String(preview.log_count)}`}
              </button>
              <button
                type="button"
                className="button--secondary"
                disabled={busy !== null}
                onClick={() => {
                  setPreview(null);
                  setError("");
                  setStale(false);
                }}
              >
                Edit details
              </button>
            </>
          )}
          <button
            type="button"
            className="button--secondary"
            disabled={busy !== null}
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
      </form>
    </TaskDialog>
  );
}

export function BulkCareSuccessNotice({
  result,
  onDismiss,
  onUndone,
}: {
  result: BulkCareApplyResponse;
  onDismiss: () => void;
  onUndone?: (undoResult: BulkCareUndoResponse) => void;
}) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const token = activeCsrfToken(auth.state);
  const [undoBusy, setUndoBusy] = useState(false);
  const [undoResult, setUndoResult] = useState<BulkCareUndoResponse | null>(
    null,
  );
  const [undoError, setUndoError] = useState("");

  async function handleUndo() {
    if (!authorized || !token || undoBusy || undoResult) return;
    setUndoBusy(true);
    setUndoError("");
    try {
      const response = await undoBulkCare(result.batch_id, token, capability);
      setUndoResult(response);
      onUndone?.(response);
    } catch (failure: unknown) {
      if (isExpectedAuthCancellation(failure)) return;
      if (failure instanceof ApiError && failure.status === 401) {
        sessionExpired();
        return;
      }
      setUndoError(extractApiError(failure).message);
    } finally {
      setUndoBusy(false);
    }
  }

  return (
    <div className="notice notice--success bulk-care-toast" role="status">
      {!undoResult ? (
        <>
          <p>
            Logged {bulkCareKindLabels[result.kind]} for{" "}
            {plural(result.logged_count, "record", "records")}
            {result.skipped_count > 0
              ? ` (${String(result.skipped_count)} skipped)`
              : ""}
            .
          </p>
          <div className="form-actions">
            <button
              type="button"
              className="button--secondary"
              disabled={undoBusy || !token}
              onClick={() => void handleUndo()}
            >
              {undoBusy ? "Undoing…" : "Undo"}
            </button>
            <button
              type="button"
              className="button--quiet"
              disabled={undoBusy}
              onClick={onDismiss}
            >
              Dismiss
            </button>
          </div>
          {undoError && <p role="alert">{undoError}</p>}
        </>
      ) : (
        <>
          <p>
            Undone: {plural(undoResult.deleted_count, "entry", "entries")}{" "}
            removed
            {undoResult.kept_count > 0
              ? ` · ${plural(undoResult.kept_count, "entry", "entries")} kept`
              : ""}
            .
          </p>
          {undoResult.kept.length > 0 && (
            <ul>
              {undoResult.kept.map((item) => (
                <li key={item.id}>
                  {item.label} — {bulkCareKeptReasonLabels[item.reason]}
                </li>
              ))}
            </ul>
          )}
          <div className="form-actions">
            <button type="button" className="button--quiet" onClick={onDismiss}>
              Dismiss
            </button>
          </div>
        </>
      )}
    </div>
  );
}
