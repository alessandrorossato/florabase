import { useState, type RefObject, type SyntheticEvent } from "react";

import { activeCsrfToken } from "../auth/api";
import { useOptionalAuth } from "../auth/context";
import { ActionButton } from "../components/Action";
import { TaskDialog } from "../components/TaskDialog";
import { deleteSavedView } from "../saved-views/api";
import { savedViewsChanged } from "../saved-views/events";
import type { SavedViewLink } from "./useSavedViewLinks";

/** Confirms removing a Saved View from the Workbench menu; records are never touched. */
export function SavedViewRemoval({
  view,
  returnFocusTo,
  onClose,
}: {
  view: SavedViewLink;
  returnFocusTo: RefObject<HTMLElement | null>;
  onClose: () => void;
}) {
  const auth = useOptionalAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event: SyntheticEvent) => {
    event.preventDefault();
    const capability = auth?.capability;
    const token = auth ? activeCsrfToken(auth.state) : "";
    if (!capability || !token || pending) return;
    setPending(true);
    setError("");
    try {
      await deleteSavedView(view.id, token, capability);
      window.dispatchEvent(new Event(savedViewsChanged));
      onClose();
    } catch {
      setError("Could not remove the saved view. Try again.");
      setPending(false);
    }
  };
  return (
    <TaskDialog
      title="Remove saved view"
      returnFocusTo={returnFocusTo}
      onClose={() => {
        if (!pending) onClose();
      }}
    >
      <form
        onSubmit={(event) => {
          void submit(event);
        }}
      >
        <h3>Remove saved view</h3>
        <p>{`Remove “${view.name}” from ${view.surface}? Collection and reference records are kept.`}</p>
        {error && (
          <p role="alert" className="notice notice--error">
            {error}
          </p>
        )}
        <div className="actions">
          <ActionButton type="submit" variant="danger" disabled={pending}>
            {pending ? "Removing…" : "Remove saved view"}
          </ActionButton>
          <button
            type="button"
            className="button--secondary"
            disabled={pending}
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
      </form>
    </TaskDialog>
  );
}
