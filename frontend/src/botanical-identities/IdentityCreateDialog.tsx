import { useId, useRef, useState, type SyntheticEvent } from "react";
import { createPortal } from "react-dom";
import {
  activeCsrfToken,
  ApiError,
  isExpectedAuthCancellation,
} from "../auth/api";
import { useAuth } from "../auth/context";
import { FieldLabel } from "../components/FieldLabel";
import { TaskDialog } from "../components/TaskDialog";
import {
  conflictExistingId,
  createBotanicalIdentity,
  getBotanicalIdentity,
  validationMessages,
  type BotanicalIdentityResponse,
} from "./api";
import { WfoNameInput } from "./WfoNameInput";

/**
 * UX-ENTRY-002: create a botanical identity from inside a record form's identity picker.
 * An exact duplicate resolves to the existing identity instead of failing.
 */
export function IdentityCreateDialog({
  initialName,
  onClose,
  onCreated,
}: {
  initialName: string;
  onClose: () => void;
  onCreated: (identity: BotanicalIdentityResponse, existing: boolean) => void;
}) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const token = activeCsrfToken(auth.state);
  const ids = {
    name: useId(),
    cultivar: useId(),
    common: useId(),
    error: useId(),
  };
  // The picker's Create button unmounts when the menu closes; return focus to its input.
  const picker = useRef<HTMLElement | null>(
    document.activeElement instanceof HTMLElement
      ? (document.activeElement
          .closest(".reference-picker")
          ?.querySelector<HTMLElement>("input") ?? null)
      : null,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    event.stopPropagation();
    if (saving || !token) return;
    const data = new FormData(event.currentTarget);
    const value = (name: string) => {
      const item = data.get(name);
      return typeof item === "string" ? item : "";
    };
    setSaving(true);
    setError(null);
    try {
      const identity = await createBotanicalIdentity(
        {
          scientific_name: value("scientific_name"),
          cultivar_name: value("cultivar_name") || null,
          common_name: value("common_name") || null,
        },
        token,
        capability,
      );
      onCreated(identity, false);
    } catch (failure: unknown) {
      if (isExpectedAuthCancellation(failure)) return;
      if (failure instanceof ApiError && failure.status === 401) {
        sessionExpired();
        return;
      }
      const existing =
        failure instanceof ApiError && failure.status === 409
          ? conflictExistingId(failure)
          : null;
      if (existing) {
        try {
          onCreated(await getBotanicalIdentity(existing, capability), true);
          return;
        } catch {
          setError(
            "That botanical identity already exists, but Florabase could not load it.",
          );
        }
      } else if (failure instanceof ApiError && failure.status === 409) {
        setError(
          "That botanical identity already exists. Search the existing choices and select it.",
        );
      } else if (failure instanceof ApiError && failure.status === 422) {
        setError(validationMessages(failure).join(" "));
      } else {
        setError(
          "Florabase could not create this identity. Your other details are still here.",
        );
      }
    } finally {
      setSaving(false);
    }
  }

  // Portalled so its form is never nested inside the record form that opened it.
  return createPortal(
    <TaskDialog
      title="Create botanical identity"
      className="seed-context-dialog identity-create-dialog"
      returnFocusTo={picker}
      onClose={() => {
        if (!saving) onClose();
      }}
    >
      <h3>Create botanical identity</h3>
      <form
        aria-describedby={error ? ids.error : undefined}
        onSubmit={(event) => void submit(event)}
      >
        <div className="field">
          <FieldLabel required htmlFor={ids.name}>
            Scientific name
          </FieldLabel>
          <WfoNameInput
            id={ids.name}
            name="scientific_name"
            required
            disabled={saving}
            defaultValue={initialName}
            capability={capability}
          />
        </div>
        <div className="field">
          <label htmlFor={ids.cultivar}>Cultivar</label>
          <input id={ids.cultivar} name="cultivar_name" disabled={saving} />
        </div>
        <div className="field">
          <label htmlFor={ids.common}>Common name</label>
          <input id={ids.common} name="common_name" disabled={saving} />
        </div>
        {error && (
          <p role="alert" id={ids.error}>
            {error}
          </p>
        )}
        <div className="form-actions">
          <button type="submit" disabled={saving}>
            {saving ? "Creating…" : "Create identity"}
          </button>
          <button
            type="button"
            className="button--secondary"
            disabled={saving}
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
      </form>
    </TaskDialog>,
    document.body,
  );
}
