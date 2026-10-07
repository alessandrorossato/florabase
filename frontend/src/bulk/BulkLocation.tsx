import { useEffect, useId, useRef, useState } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { TaskDialog } from "../components/TaskDialog";
import { listLocations, type LocationResponse } from "../locations/api";
import { ReferencePicker } from "../seed-lots/ReferencePicker";
import {
  applyLocation,
  previewLocation,
  type BulkPreview,
  type BulkReference,
  type BulkResult,
} from "./api";
import {
  BULK_LIMIT,
  type BulkChoice,
  type BulkSelection,
} from "./useBulkSelection";

export function BulkCheckbox({
  selection,
  choice,
}: {
  selection: BulkSelection;
  choice: BulkChoice;
}) {
  if (!selection.active) return null;
  return (
    <label className="bulk-checkbox">
      <input
        type="checkbox"
        aria-label={`Select ${choice.label}`}
        checked={selection.checked(choice)}
        disabled={
          !choice.eligible ||
          (!selection.checked(choice) &&
            selection.selected.length >= BULK_LIMIT)
        }
        onChange={() => {
          selection.toggle(choice);
        }}
      />
      <span className="sr-only">
        {choice.eligible
          ? "Current record"
          : "Historical record cannot be moved"}
      </span>
    </label>
  );
}

export function BulkSelect({
  selection,
  visible,
  onStart,
}: {
  selection: BulkSelection;
  visible: BulkChoice[];
  onStart?: () => void;
}) {
  if (selection.active) return null;
  return (
    <button
      type="button"
      id={selection.entryId}
      className="button--secondary"
      disabled={!visible.some((row) => row.eligible)}
      onClick={() => {
        onStart?.();
        selection.start();
      }}
    >
      Select
    </button>
  );
}

export function BulkToolbar({
  selection,
  visible,
  onSuccess,
}: {
  selection: BulkSelection;
  visible: BulkChoice[];
  onSuccess: (result: BulkResult) => void;
}) {
  const [message, setMessage] = useState("");
  const eligibleCount = visible.filter((row) => row.eligible).length;
  if (!selection.active && !message) return null;
  return (
    <div className="bulk-actions">
      {!selection.active && message && <p role="status">{message}</p>}
      {selection.active && (
        <div
          className="bulk-toolbar"
          role="group"
          aria-label="Selected records"
        >
          <strong role="status">{selection.selected.length} selected</strong>
          <button
            type="button"
            disabled={!selection.selected.length}
            onClick={() => {
              setMessage("");
              selection.openDialog();
            }}
          >
            Move to location
          </button>
          <div className="bulk-toolbar-secondary">
            <button
              type="button"
              className="bulk-secondary"
              disabled={!eligibleCount || eligibleCount > BULK_LIMIT}
              onClick={selection.selectVisible}
            >
              Select visible
            </button>
            <button
              type="button"
              className="bulk-secondary"
              disabled={!selection.selected.length}
              onClick={selection.clear}
            >
              Clear selection
            </button>
            <button
              type="button"
              className="bulk-secondary"
              onClick={() => {
                setMessage("");
                selection.cancel();
                window.setTimeout(selection.focusEntry, 0);
              }}
            >
              Done
            </button>
          </div>
          <small>
            Current visible records only · Maximum {BULK_LIMIT}
            {eligibleCount > BULK_LIMIT
              ? " — narrow the filters or select individually"
              : ""}
          </small>
        </div>
      )}
      {selection.dialog && (
        <MoveDialog
          records={selection.selected.map(({ kind, id }) => ({ kind, id }))}
          onClose={selection.closeDialog}
          onSuccess={(result) => {
            selection.cancel();
            setMessage(
              `${String(result.moved_count)} moved${result.unchanged_count ? ` · ${String(result.unchanged_count)} already there` : ""}.`,
            );
            onSuccess(result);
            window.setTimeout(selection.focusEntry, 0);
          }}
        />
      )}
    </div>
  );
}

function MoveDialog({
  records,
  onClose,
  onSuccess,
}: {
  records: BulkReference[];
  onClose: () => void;
  onSuccess: (result: BulkResult) => void;
}) {
  const auth = useAuth();
  const errorId = useId();
  const [locations, setLocations] = useState<LocationResponse[] | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [target, setTarget] = useState("");
  const [preview, setPreview] = useState<BulkPreview | null>(null);
  const [busy, setBusy] = useState<"preview" | "apply" | null>(null);
  const [error, setError] = useState("");
  const [conflicts, setConflicts] = useState<string[]>([]);
  const controller = useRef<AbortController | null>(null);
  const scopes = {
    seed_lot: "seed_lots",
    sowing: "sowings",
    plant: "plants",
    plant_group: "plants",
    harvest_inventory: "harvest_inventory",
  } as const;
  useEffect(() => {
    const abort = new AbortController();
    void listLocations(abort.signal)
      .then(setLocations)
      .catch((failure: unknown) => {
        if (!abort.signal.aborted) {
          if (failure instanceof ApiError && failure.status === 401)
            auth.sessionExpired();
          else setError("Could not load Locations. Retry.");
        }
      });
    return () => {
      abort.abort();
      controller.current?.abort();
    };
  }, [auth, attempt]);
  const choices =
    locations
      ?.filter(
        (row) =>
          !row.retired_at &&
          records.every((ref) => row.usage_scopes.includes(scopes[ref.kind])),
      )
      .map((row) => ({ id: row.id, label: row.display_path })) ?? [];
  const token = "csrfToken" in auth.state ? auth.state.csrfToken : "";
  const showError = (failure: unknown) => {
    if (failure instanceof ApiError && failure.status === 401) {
      auth.sessionExpired();
      return;
    }
    if (failure instanceof ApiError && failure.status === 403) {
      setError(
        "Session protection changed. No records moved. Reload the page before retrying.",
      );
      setConflicts([]);
      setPreview(null);
      return;
    }
    const detail =
      failure instanceof ApiError
        ? (
            failure.body as
              | {
                  detail?: {
                    message?: string;
                    rows?: { label: string; message?: string }[];
                  };
                }
              | undefined
          )?.detail
        : undefined;
    setError(
      detail?.message ??
        "Could not complete the move. Refresh the preview and retry.",
    );
    setConflicts(
      detail?.rows?.map(
        (row) =>
          `${row.label}${row.message ? `: ${row.message}` : " — changed since preview"}`,
      ) ?? [],
    );
    setPreview(null);
  };
  return (
    <TaskDialog
      title="Move to location"
      className="bulk-move-dialog"
      dismissOnBackdrop
      onClose={() => {
        if (busy !== "apply") onClose();
      }}
    >
      <h2 className="bulk-move-title">Move to location</h2>
      <p>
        {records.length} selected · Review before applying.
        {records.some(
          (row) => row.kind === "plant" || row.kind === "plant_group",
        ) &&
          " Plants and groups retain an undated Movement Event for each move."}
      </p>
      <ReferencePicker
        label="Target Location"
        value={target}
        choices={choices}
        disabled={Boolean(busy) || !locations}
        required
        onChange={(value) => {
          setTarget(value);
          setPreview(null);
          setError("");
          setConflicts([]);
        }}
      />
      {!locations && !error && <p role="status">Loading Locations…</p>}
      {!locations && error && (
        <button
          type="button"
          onClick={() => {
            setError("");
            setAttempt((value) => value + 1);
          }}
        >
          Retry Locations
        </button>
      )}
      {locations && !choices.length && (
        <p role="status">
          No active Location supports every selected record kind.
        </p>
      )}
      {error && (
        <div role="alert" id={errorId} tabIndex={-1}>
          <p>{error}</p>
          {conflicts.length > 0 && (
            <ul>
              {conflicts.map((row, index) => (
                <li key={index}>{row}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {preview && (
        <section className="bulk-preview" aria-label="Move preview">
          <p role="status">
            {preview.move_count} will move · {preview.unchanged_count} already
            there · {preview.selected_count} selected
          </p>
          <p>
            Target: <strong>{preview.target_location}</strong>
          </p>
          <ul>
            {preview.rows.map((row) => (
              <li key={`${row.kind}:${row.id}`}>
                <strong>{row.label}</strong>
                <small>{row.kind.replaceAll("_", " ")}</small>
                <span>
                  {row.current_location ?? "Location not recorded"} →{" "}
                  {preview.target_location}
                </span>
                <span>
                  {row.status === "unchanged"
                    ? "Already at this Location"
                    : row.status === "conflict"
                      ? row.message
                      : "Will move"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      <div className="form-actions">
        <button
          type="button"
          disabled={!target || Boolean(busy)}
          aria-describedby={error ? errorId : undefined}
          onClick={() => {
            setBusy("preview");
            setError("");
            setConflicts([]);
            controller.current?.abort();
            const abort = new AbortController();
            controller.current = abort;
            void previewLocation(records, target, token, abort.signal)
              .then((result) => {
                if (!abort.signal.aborted) setPreview(result);
              })
              .catch((failure: unknown) => {
                if (!abort.signal.aborted) showError(failure);
              })
              .finally(() => {
                if (!abort.signal.aborted) setBusy(null);
              });
          }}
        >
          {busy === "preview"
            ? "Previewing…"
            : preview
              ? "Refresh preview"
              : "Preview move"}
        </button>
        <button
          type="button"
          disabled={!preview?.can_apply || Boolean(busy)}
          onClick={() => {
            if (!preview) return;
            setBusy("apply");
            setError("");
            void applyLocation(preview, token)
              .then(onSuccess)
              .catch(showError)
              .finally(() => {
                setBusy(null);
              });
          }}
        >
          {busy === "apply"
            ? "Moving…"
            : `Apply move${preview ? ` (${String(preview.move_count)})` : ""}`}
        </button>
        <button
          type="button"
          className="button--secondary"
          disabled={busy === "apply"}
          onClick={onClose}
        >
          Cancel
        </button>
      </div>
    </TaskDialog>
  );
}
