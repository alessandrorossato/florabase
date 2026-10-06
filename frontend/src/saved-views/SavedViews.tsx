import { useEffect, useId, useRef, useState, type SyntheticEvent } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { TaskDialog } from "../components/TaskDialog";
import { openDirectoryRoute } from "../components/recordNavigation";
import {
  createSavedView,
  deleteSavedView,
  listSavedViews,
  updateSavedView,
  type SavedView,
} from "./api";
import {
  savedViewHash,
  surfaceLabels,
  type SavedState,
  type Surface,
} from "./state";

type Action =
  | { kind: "create" }
  | { kind: "rename" | "update" | "delete"; view: SavedView };

export function SavedViews({
  surface,
  state,
  allSurfaces = false,
}: {
  surface: Surface;
  state: SavedState | null;
  allSurfaces?: boolean;
}) {
  const auth = useAuth();
  const panelId = useId();
  const listTrigger = useRef<HTMLButtonElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [views, setViews] = useState<SavedView[] | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [loadError, setLoadError] = useState(false);
  const [action, setAction] = useState<Action | null>(null);
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const meaningful = Boolean(state && Object.keys(state).length);
  const token =
    auth.state.status === "authenticated" ||
    auth.state.status === "logout-failed"
      ? auth.state.csrfToken
      : null;

  useEffect(() => {
    if (!expanded) return;
    const controller = new AbortController();
    void listSavedViews(
      allSurfaces ? undefined : surface,
      controller.signal,
      offset,
    )
      .then((rows) => {
        if (!controller.signal.aborted) {
          setViews((previous) =>
            offset === 0 ? rows : [...(previous ?? []), ...rows],
          );
          setHasMore(rows.length === 100);
          setLoadingMore(false);
          setLoadError(false);
        }
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else {
          setLoadError(true);
          setLoadingMore(false);
        }
      });
    return () => {
      controller.abort();
    };
  }, [expanded, surface, allSurfaces, offset, attempt, auth]);

  function begin(next: Action) {
    setError(null);
    setNotice(null);
    setName(next.kind === "rename" ? next.view.name : "");
    setAction(next);
  }
  function open(view: SavedView) {
    const hash =
      view.compatibility === "supported"
        ? savedViewHash(view.surface, view.state_version, view.state)
        : null;
    if (!hash) {
      setNotice(
        `“${view.name}” has unsupported or incompatible saved state. You can rename or delete it.`,
      );
      return;
    }
    setExpanded(false);
    openDirectoryRoute(hash);
  }
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!action || !token || pending) return;
    if (
      (action.kind === "create" || action.kind === "rename") &&
      !name.trim()
    ) {
      setError("Enter a name for this view.");
      return;
    }
    if ((action.kind === "create" || action.kind === "update") && !meaningful) {
      setError("Choose a search, filter or view mode before saving.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      if (action.kind === "delete")
        await deleteSavedView(action.view.id, token);
      else if (action.kind === "rename")
        await updateSavedView(action.view.id, { name }, token);
      else if (action.kind === "update")
        await updateSavedView(
          action.view.id,
          { state_version: 1, state: state ?? {} },
          token,
        );
      else
        await createSavedView(
          { name, surface, state_version: 1, state: state ?? {} },
          token,
        );
      setNotice(
        action.kind === "delete"
          ? "Saved View deleted. Your records are unchanged."
          : action.kind === "rename"
            ? "Saved View renamed."
            : action.kind === "update"
              ? "Saved View updated with the current filters."
              : "View saved.",
      );
      setAction(null);
      setExpanded(true);
      setViews(null);
      setOffset(0);
      setAttempt((value) => value + 1);
      window.setTimeout(() => listTrigger.current?.focus(), 0);
    } catch (failure: unknown) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else
        setError(
          failure instanceof ApiError && failure.status === 409
            ? "A Saved View with this name already exists on this surface. Choose another name."
            : "Could not save this change. Check the name and filters, then try again.",
        );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="saved-views">
      <div className="saved-views__controls">
        {meaningful && (
          <button
            type="button"
            className="button--secondary"
            onClick={() => {
              begin({ kind: "create" });
            }}
          >
            Save view
          </button>
        )}
        <button
          type="button"
          className="button--secondary"
          aria-expanded={expanded}
          ref={listTrigger}
          aria-controls={panelId}
          onClick={() => {
            if (!expanded) {
              setOffset(0);
              setViews(null);
              setHasMore(false);
              setLoadError(false);
            }
            setExpanded((value) => !value);
          }}
        >
          Saved views{allSurfaces ? " · all surfaces" : ""}
        </button>
      </div>
      {notice && (
        <p role="status" className="field-help">
          {notice}
        </p>
      )}
      {expanded && (
        <section
          id={panelId}
          aria-label={
            allSurfaces
              ? "All Saved Views"
              : `${surfaceLabels[surface]} Saved Views`
          }
          className="saved-views__panel"
        >
          <h3>
            Saved views
            {allSurfaces ? " across Florabase" : ` · ${surfaceLabels[surface]}`}
          </h3>
          {loadError ? (
            <p role="alert">
              Could not load Saved Views.{" "}
              <button
                type="button"
                onClick={() => {
                  setLoadError(false);
                  setAttempt((value) => value + 1);
                }}
              >
                Retry Saved Views
              </button>
            </p>
          ) : !views ? (
            <p role="status">Loading Saved Views…</p>
          ) : !views.length ? (
            <p className="field-help">
              No Saved Views yet. Apply a search or filter, then choose Save
              view.
            </p>
          ) : (
            <ul className="saved-views__list">
              {views.map((view) => {
                const compatible =
                  view.compatibility === "supported" &&
                  Boolean(
                    savedViewHash(view.surface, view.state_version, view.state),
                  );
                return (
                  <li key={view.id}>
                    <div className="saved-views__name">
                      <strong>{view.name}</strong>
                      <span className="field-help">
                        {surfaceLabels[view.surface]}
                      </span>
                      {!compatible && (
                        <span className="field-help">
                          Unsupported or incompatible saved state
                        </span>
                      )}
                    </div>
                    <div className="saved-views__actions">
                      <button
                        type="button"
                        className="button--secondary"
                        aria-label={`Open ${view.name}`}
                        onClick={() => {
                          open(view);
                        }}
                      >
                        Open
                      </button>
                      <button
                        type="button"
                        className="button--secondary"
                        aria-label={`Rename ${view.name}`}
                        onClick={() => {
                          begin({ kind: "rename", view });
                        }}
                      >
                        Rename
                      </button>
                      {view.surface === surface && meaningful && (
                        <button
                          type="button"
                          className="button--secondary"
                          aria-label={`Update ${view.name} with current view`}
                          onClick={() => {
                            begin({ kind: "update", view });
                          }}
                        >
                          Update with current view
                        </button>
                      )}
                      <button
                        type="button"
                        className="button--secondary"
                        aria-label={`Delete ${view.name}`}
                        onClick={() => {
                          begin({ kind: "delete", view });
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
          {hasMore && views && (
            <button
              type="button"
              className="button--secondary"
              disabled={loadingMore || loadError}
              onClick={() => {
                setLoadingMore(true);
                setOffset((value) => value + 100);
              }}
            >
              {" "}
              {loadingMore
                ? "Loading more Saved Views…"
                : "Show more Saved Views"}
            </button>
          )}
        </section>
      )}
      {action && (
        <TaskDialog
          title={
            action.kind === "create"
              ? "Save view"
              : action.kind === "rename"
                ? "Rename Saved View"
                : action.kind === "update"
                  ? "Update with current view"
                  : "Delete Saved View"
          }
          onClose={() => {
            if (!pending) setAction(null);
          }}
        >
          <form
            onSubmit={(event) => {
              void submit(event);
            }}
          >
            <h3>
              {action.kind === "create"
                ? "Save view"
                : action.kind === "rename"
                  ? "Rename Saved View"
                  : action.kind === "update"
                    ? "Update with current view"
                    : "Delete Saved View"}
            </h3>
            <p>
              {
                surfaceLabels[
                  action.kind === "create" ? surface : action.view.surface
                ]
              }
            </p>
            {action.kind === "create" || action.kind === "rename" ? (
              <div className="field">
                <label htmlFor={`${panelId}-name`}>View name</label>
                <input
                  id={`${panelId}-name`}
                  value={name}
                  maxLength={120}
                  disabled={pending}
                  aria-describedby={error ? `${panelId}-error` : undefined}
                  onChange={(event) => {
                    setName(event.currentTarget.value);
                  }}
                />
                <p className="field-help">
                  A unique name on this surface, up to 120 characters.
                </p>
              </div>
            ) : (
              <p>
                {action.kind === "delete"
                  ? `Delete “${action.view.name}”? Collection and reference records are kept.`
                  : `Replace the saved filters in “${action.view.name}” with your current view? Manual filter changes are saved only when you confirm.`}
              </p>
            )}
            {error && (
              <p
                id={`${panelId}-error`}
                role="alert"
                className="notice notice--error"
              >
                {error}
              </p>
            )}
            <div className="actions">
              <button type="submit" disabled={pending}>
                {pending
                  ? "Saving…"
                  : action.kind === "delete"
                    ? "Delete Saved View"
                    : action.kind === "update"
                      ? "Update Saved View"
                      : action.kind === "rename"
                        ? "Rename Saved View"
                        : "Save view"}
              </button>
              <button
                type="button"
                className="button--secondary"
                disabled={pending}
                onClick={() => {
                  setAction(null);
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </TaskDialog>
      )}
    </div>
  );
}
