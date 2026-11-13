import {
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import { ApiError } from "../auth/api";
import { PasswordChangeContext, useAuth } from "../auth/context";
import { FieldLabel } from "../components/FieldLabel";
import { PageHeader } from "../components/ReferenceUI";
import { Page } from "../components/WorkspaceUI";
import { isRecordTaskNavigation } from "../components/recordNavigation";
import "./settings.css";

interface BrowserNavigation extends EventTarget {
  currentEntry?: { index: number };
}

interface BrowserNavigateEvent extends Event {
  destination: { url: string; sameDocument: boolean };
  hashChange: boolean;
  navigationType: string;
}

type ErrorField = "current" | "new" | "confirm";
interface FormError {
  message: string;
  field?: ErrorField;
}

function changeError(error: unknown): FormError {
  if (error instanceof ApiError) {
    const body = error.body as { detail?: { code?: string } } | null;
    if (
      error.status === 403 &&
      body?.detail?.code === "invalid_current_password"
    ) {
      return { field: "current", message: "Current password is incorrect." };
    }
    if (error.status === 403) {
      return {
        message:
          "Refresh this page to restore your session before trying again.",
      };
    }
    if (error.status === 422) {
      return {
        field: "new",
        message:
          body?.detail?.code === "password_unchanged"
            ? "Choose a different password."
            : "Check the password fields and try again.",
      };
    }
    if (error.status === 429) {
      const seconds = Number(error.retryAfter);
      return {
        message:
          Number.isSafeInteger(seconds) && seconds > 0
            ? `Too many attempts. Try again in ${String(seconds)} seconds.`
            : "Too many attempts. Wait before trying again.",
      };
    }
  }
  return {
    message:
      "The password change could not be confirmed. Refresh to check your session and verify your password by signing in.",
  };
}

export function AccountScreen({
  registerFormDeparture,
  clearFormChanged,
}: {
  registerFormDeparture: (guard: () => boolean) => () => void;
  clearFormChanged: () => void;
}) {
  const { state } = useAuth();
  const passwordChange = useContext(PasswordChangeContext);
  const currentInput = useRef<HTMLInputElement>(null);
  const newInput = useRef<HTMLInputElement>(null);
  const confirmInput = useRef<HTMLInputElement>(null);
  const notice = useRef<HTMLParagraphElement>(null);
  const dirty = useRef(false);
  const submitting = useRef(false);
  const [error, setError] = useState<FormError>();
  const [success, setSuccess] = useState(false);
  const canLeave = useCallback(() => {
    if (submitting.current) return false;
    if (dirty.current && !window.confirm("Discard the entered passwords?"))
      return false;
    dirty.current = false;
    clearFormChanged();
    return true;
  }, [clearFormChanged]);

  useEffect(() => {
    const unregister = registerFormDeparture(canLeave);
    const navigation = (window as Window & { navigation?: BrowserNavigation })
      .navigation;
    const sourceHash = window.location.hash;
    const sourceIndex = navigation?.currentEntry?.index;
    let restoring = false;
    function nativeNavigation(event: Event) {
      const next = event as BrowserNavigateEvent;
      if (
        restoring ||
        !next.cancelable ||
        !next.destination.sameDocument ||
        (!next.hashChange && next.navigationType !== "traverse") ||
        new URL(next.destination.url).hash === sourceHash
      )
        return;
      if (!canLeave()) event.preventDefault();
    }
    function guardTraversal(event: Event) {
      if (isRecordTaskNavigation(event)) return;
      if (window.location.hash === sourceHash) {
        restoring = false;
        return;
      }
      if (!restoring && canLeave()) return;
      event.stopImmediatePropagation();
      if (restoring) return;
      const index = navigation?.currentEntry?.index;
      if (
        index !== undefined &&
        sourceIndex !== undefined &&
        sourceIndex !== index
      ) {
        restoring = true;
        window.history.go(sourceIndex - index);
      } else {
        window.history.replaceState(window.history.state, "", sourceHash);
      }
    }
    navigation?.addEventListener("navigate", nativeNavigation);
    window.addEventListener("popstate", guardTraversal, true);
    window.addEventListener("hashchange", guardTraversal, true);
    return () => {
      unregister();
      clearFormChanged();
      navigation?.removeEventListener("navigate", nativeNavigation);
      window.removeEventListener("popstate", guardTraversal, true);
      window.removeEventListener("hashchange", guardTraversal, true);
    };
  }, [canLeave, clearFormChanged, registerFormDeparture]);

  const [hasInput, setHasInput] = useState(false);
  const pending = passwordChange?.pending ?? false;
  useEffect(() => {
    if (!hasInput && !pending) return;
    function beforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", beforeUnload);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
    };
  }, [hasInput, pending]);

  useEffect(() => {
    if (!error) return;
    if (error.field === "current") currentInput.current?.focus();
    else if (error.field === "new") newInput.current?.focus();
    else if (error.field === "confirm") confirmInput.current?.focus();
    else notice.current?.focus();
  }, [error]);

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    if (!passwordChange || submitting.current || pending) return;
    const current = currentInput.current?.value ?? "";
    const next = newInput.current?.value ?? "";
    const currentLength = Array.from(current).length;
    if (currentLength < 1 || currentLength > 1024) {
      setError({ field: "current", message: "Enter your current password." });
      return;
    }
    const newLength = Array.from(next).length;
    if (newLength < 12 || newLength > 1024) {
      setError({ field: "new", message: "Use 12 to 1024 characters." });
      return;
    }
    if (next !== confirmInput.current?.value) {
      setError({
        field: "confirm",
        message: "The new passwords do not match.",
      });
      return;
    }
    submitting.current = true;
    event.currentTarget.reset();
    dirty.current = false;
    setHasInput(false);
    clearFormChanged();
    setError(undefined);
    setSuccess(false);
    try {
      setSuccess(
        await passwordChange.submit({
          current_password: current,
          new_password: next,
        }),
      );
    } catch (failure: unknown) {
      setError(changeError(failure));
    } finally {
      submitting.current = false;
    }
  }

  return (
    <Page className="settings-workspace" titleId="account-heading">
      <PageHeader
        title="Account"
        titleId="account-heading"
        eyebrow="Settings"
      />
      <div className="settings-content">
        {state.status === "authenticated" && state.session.owner && (
          <section
            className="settings-panel"
            aria-labelledby="change-password-heading"
          >
            <h3 id="change-password-heading">Change password</h3>
            <p>Other browser sessions will need to sign in again.</p>
            <form
              aria-labelledby="change-password-heading"
              aria-busy={pending}
              noValidate
              onSubmit={(event) => void submit(event)}
              onChange={() => {
                dirty.current = [currentInput, newInput, confirmInput].some(
                  (input) => Boolean(input.current?.value),
                );
                setHasInput(dirty.current);
              }}
            >
              {(
                [
                  [
                    "current",
                    "Current password",
                    currentInput,
                    "current-password",
                  ],
                  ["new", "New password", newInput, "new-password"],
                  [
                    "confirm",
                    "Confirm new password",
                    confirmInput,
                    "new-password",
                  ],
                ] as const
              ).map(([field, label, ref, autoComplete]) => (
                <div className="field" key={field}>
                  <FieldLabel required htmlFor={`account-password-${field}`}>
                    {label}
                  </FieldLabel>
                  <input
                    id={`account-password-${field}`}
                    ref={ref}
                    name={`account-password-${field}`}
                    type="password"
                    autoComplete={autoComplete}
                    disabled={pending}
                    required
                    aria-invalid={error?.field === field || undefined}
                    aria-describedby={
                      [
                        field === "new" ? "account-password-policy" : "",
                        error?.field === field ? "account-password-error" : "",
                      ]
                        .filter(Boolean)
                        .join(" ") || undefined
                    }
                  />
                  {field === "new" && (
                    <p id="account-password-policy">12 to 1024 characters.</p>
                  )}
                </div>
              ))}
              {error && (
                <p
                  id="account-password-error"
                  className="notice notice--error"
                  role="alert"
                  ref={notice}
                  tabIndex={-1}
                >
                  {error.message}
                </p>
              )}
              {success && <p role="status">Password changed.</p>}
              <button type="submit" disabled={pending}>
                {pending ? "Changing password…" : "Change password"}
              </button>
            </form>
          </section>
        )}
      </div>
    </Page>
  );
}
