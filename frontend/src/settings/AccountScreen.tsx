import {
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";

import {
  activeCsrfToken,
  ApiError,
  isExpectedAuthCancellation,
  listDeviceSessions,
  revokeAllDeviceSessions,
  revokeDeviceSession,
  type DeviceSessionItem,
} from "../auth/api";
import { PasswordChangeContext, useAuth } from "../auth/context";
import { isNativeBearerTransport } from "../auth/transport";
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

function formatDeviceTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AccountScreen({
  registerFormDeparture,
  clearFormChanged,
}: {
  registerFormDeparture: (guard: () => boolean) => () => void;
  clearFormChanged: () => void;
}) {
  const { state, capability, sessionExpired } = useAuth();
  const nativeMode = isNativeBearerTransport();
  const passwordChange = useContext(PasswordChangeContext);
  const currentInput = useRef<HTMLInputElement>(null);
  const newInput = useRef<HTMLInputElement>(null);
  const confirmInput = useRef<HTMLInputElement>(null);
  const notice = useRef<HTMLParagraphElement>(null);
  const dirty = useRef(false);
  const submitting = useRef(false);
  const [error, setError] = useState<FormError>();
  const [success, setSuccess] = useState(false);
  const [devices, setDevices] = useState<DeviceSessionItem[]>([]);
  const [devicesLoadedKey, setDevicesLoadedKey] = useState<number | null>(null);
  const [devicesError, setDevicesError] = useState<string | null>(null);
  const [devicesStatus, setDevicesStatus] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [revokingAll, setRevokingAll] = useState(false);
  const [devicesReload, setDevicesReload] = useState(0);

  const authenticatedOwner =
    state.status === "authenticated" && state.session.owner;
  const devicesLoading =
    authenticatedOwner && devicesLoadedKey !== devicesReload;

  useEffect(() => {
    if (!authenticatedOwner || !capability.isAuthorized()) return;
    const controller = new AbortController();
    const requestKey = devicesReload;
    void listDeviceSessions(capability, controller.signal)
      .then((response: unknown) => {
        if (controller.signal.aborted) return;
        const record =
          typeof response === "object" && response !== null
            ? (response as { items?: unknown })
            : null;
        const items = Array.isArray(record?.items)
          ? (record.items as DeviceSessionItem[])
          : [];
        setDevices(items);
        setDevicesError(null);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(caught)) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 401) {
          sessionExpired();
          return;
        }
        setDevicesError("Could not load connected devices.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setDevicesLoadedKey(requestKey);
      });
    return () => {
      controller.abort();
    };
  }, [authenticatedOwner, capability, devicesReload, sessionExpired]);
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
      const changed = await passwordChange.submit({
        current_password: current,
        new_password: next,
      });
      setSuccess(changed);
      if (changed) {
        setDevicesReload((count) => count + 1);
      }
    } catch (failure: unknown) {
      setError(changeError(failure));
    } finally {
      submitting.current = false;
    }
  }

  async function handleRevokeDevice(item: DeviceSessionItem) {
    if (revokingId !== null || revokingAll || !capability.isAuthorized()) {
      return;
    }
    setRevokingId(item.id);
    setDevicesError(null);
    setDevicesStatus(null);
    try {
      await revokeDeviceSession(item.id, activeCsrfToken(state), capability);
      if (item.current) {
        sessionExpired();
        return;
      }
      setDevices((current) => current.filter((entry) => entry.id !== item.id));
      setDevicesStatus(`Revoked "${item.device_label}".`);
    } catch (caught: unknown) {
      if (isExpectedAuthCancellation(caught)) return;
      if (caught instanceof ApiError && caught.status === 401) {
        sessionExpired();
        return;
      }
      setDevicesError("Could not revoke that device. Try again.");
    } finally {
      setRevokingId(null);
    }
  }

  async function handleRevokeAllDevices() {
    if (revokingId !== null || revokingAll || !capability.isAuthorized()) {
      return;
    }
    if (
      !window.confirm(
        "Revoke all connected mobile devices? They will need to sign in again.",
      )
    ) {
      return;
    }
    const includesCurrent = devices.some((item) => item.current);
    setRevokingAll(true);
    setDevicesError(null);
    setDevicesStatus(null);
    try {
      await revokeAllDeviceSessions(activeCsrfToken(state), capability);
      if (includesCurrent) {
        sessionExpired();
        return;
      }
      setDevices([]);
      setDevicesStatus("All connected devices were revoked.");
    } catch (caught: unknown) {
      if (isExpectedAuthCancellation(caught)) return;
      if (caught instanceof ApiError && caught.status === 401) {
        sessionExpired();
        return;
      }
      setDevicesError("Could not revoke connected devices. Try again.");
    } finally {
      setRevokingAll(false);
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
        {authenticatedOwner && (
          <>
            <section
              className="settings-panel"
              aria-labelledby="change-password-heading"
            >
              <h3 id="change-password-heading">Change password</h3>
              {nativeMode ? (
                <p>Change your password in the web app.</p>
              ) : (
                <>
                  <p>
                    Other browser sessions and connected devices will need to
                    sign in again.
                  </p>
                  <form
                    aria-labelledby="change-password-heading"
                    aria-busy={pending}
                    noValidate
                    onSubmit={(event) => void submit(event)}
                    onChange={() => {
                      dirty.current = [
                        currentInput,
                        newInput,
                        confirmInput,
                      ].some((input) => Boolean(input.current?.value));
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
                        <FieldLabel
                          required
                          htmlFor={`account-password-${field}`}
                        >
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
                              error?.field === field
                                ? "account-password-error"
                                : "",
                            ]
                              .filter(Boolean)
                              .join(" ") || undefined
                          }
                        />
                        {field === "new" && (
                          <p id="account-password-policy">
                            12 to 1024 characters.
                          </p>
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
                </>
              )}
            </section>

            <section
              className="settings-panel"
              aria-labelledby="connected-devices-heading"
            >
              <div className="device-sessions-header">
                <h3 id="connected-devices-heading">Connected devices</h3>
                {devices.length > 0 && (
                  <button
                    type="button"
                    className="button--secondary"
                    disabled={revokingAll || revokingId !== null}
                    onClick={() => {
                      void handleRevokeAllDevices();
                    }}
                  >
                    {revokingAll ? "Revoking…" : "Revoke all devices"}
                  </button>
                )}
              </div>
              <p>
                Signed-in Android app sessions. Revoking a device signs it out
                immediately.
              </p>
              {devicesError && (
                <p className="notice notice--error" role="alert">
                  {devicesError}
                </p>
              )}
              {devicesStatus && <p role="status">{devicesStatus}</p>}
              {devicesLoading ? (
                <p aria-live="polite">Loading connected devices…</p>
              ) : devices.length === 0 ? (
                <p className="device-sessions-empty">
                  No mobile devices are currently signed in.
                </p>
              ) : (
                <ul className="device-sessions-list">
                  {devices.map((item) => (
                    <li key={item.id} className="device-sessions-item">
                      <div className="device-sessions-meta">
                        <div className="device-sessions-title">
                          <strong>{item.device_label}</strong>
                          {item.current && (
                            <span className="device-sessions-badge">
                              This device
                            </span>
                          )}
                        </div>
                        <span className="device-sessions-dates">
                          Signed in {formatDeviceTimestamp(item.created_at)} ·
                          Last seen {formatDeviceTimestamp(item.last_seen_at)}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="button--secondary"
                        disabled={revokingAll || revokingId !== null}
                        aria-label={`Revoke ${item.device_label}`}
                        onClick={() => {
                          void handleRevokeDevice(item);
                        }}
                      >
                        {revokingId === item.id ? "Revoking…" : "Revoke"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </Page>
  );
}
