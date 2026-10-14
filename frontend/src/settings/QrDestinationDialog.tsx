import { useState, type SyntheticEvent } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { TaskDialog } from "../components/TaskDialog";
import {
  publicQrValidationMessage,
  savePublicQrBaseUrl,
  type ApplicationSettings,
} from "./api";

export function QrDestinationDialog({
  value,
  onSaved,
  onClose,
}: {
  value: string | null;
  onSaved: (settings: ApplicationSettings) => void;
  onClose: () => void;
}) {
  const auth = useAuth();
  const [draft, setDraft] = useState(value ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [discard, setDiscard] = useState(false);
  const dirty = draft !== (value ?? "");
  function dismiss() {
    if (saving) return;
    if (discard) {
      setDiscard(false);
      return;
    }
    if (dirty) setDiscard(true);
    else onClose();
  }
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!("csrfToken" in auth.state)) return;
    setSaving(true);
    setError("");
    try {
      const settings = await savePublicQrBaseUrl(draft, auth.state.csrfToken);
      onSaved(settings);
      onClose();
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else
        setError(
          failure instanceof ApiError && failure.status === 422
            ? publicQrValidationMessage
            : "Could not save the QR destination. Your changes are retained. Try again.",
        );
    } finally {
      setSaving(false);
    }
  }
  return (
    <TaskDialog
      title="QR destination"
      className="qr-destination-dialog"
      onClose={dismiss}
      dismissOnBackdrop
    >
      <h3>QR destination</h3>
      <form
        onSubmit={(event) => {
          void submit(event);
        }}
      >
        <label htmlFor="labels-qr-base-url">Public / QR base URL</label>
        <input
          id="labels-qr-base-url"
          type="url"
          inputMode="url"
          maxLength={200}
          value={draft}
          onChange={(event) => {
            setDraft(event.target.value);
            setError("");
          }}
          aria-describedby="labels-qr-base-help"
          disabled={saving}
        />
        <p id="labels-qr-base-help" className="field-help">
          Printed QR codes will open records using this address. Use an HTTP(S)
          origin; leave blank to disable printing.
        </p>
        {error && (
          <p role="alert" className="notice notice--error">
            {error}
          </p>
        )}
        {discard ? (
          <div className="qr-discard" role="alert">
            <p>Discard unsaved QR destination changes?</p>
            <div className="actions">
              <button
                type="button"
                className="button--secondary"
                onClick={() => {
                  setDiscard(false);
                }}
              >
                Continue editing
              </button>
              <button type="button" onClick={onClose}>
                Discard changes
              </button>
            </div>
          </div>
        ) : (
          <div className="actions">
            <button
              type="button"
              className="button--secondary"
              disabled={saving}
              onClick={dismiss}
            >
              Cancel
            </button>
            <button type="submit" disabled={saving || !dirty}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        )}
      </form>
    </TaskDialog>
  );
}
