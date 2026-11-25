import { FieldLabel } from "../components/FieldLabel";
import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { useAuth } from "./context";
import {
  canChangeServer,
  getConfiguredServerUrl,
  isNativeBearerTransport,
  loadDefaultDeviceLabel,
  triggerChangeServer,
} from "./transport";

export function LoginForm() {
  const auth = useAuth();
  const nativeMode = isNativeBearerTransport();
  const serverUrl = getConfiguredServerUrl();
  const [password, setPassword] = useState("");
  const [deviceLabel, setDeviceLabel] = useState("");
  const errorRef = useRef<HTMLParagraphElement>(null);
  const submitting = auth.state.status === "submitting-login";
  const message =
    auth.state.status === "unauthenticated" ? auth.state.message : undefined;

  useEffect(() => {
    if (!nativeMode) return;
    let active = true;
    void loadDefaultDeviceLabel().then((label) => {
      if (active) setDeviceLabel((current) => (current ? current : label));
    });
    return () => {
      active = false;
    };
  }, [nativeMode]);

  useEffect(() => {
    if (message) errorRef.current?.focus();
  }, [message]);

  async function submit(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const loginNameValue = form.get("login_name");
    const loginName = typeof loginNameValue === "string" ? loginNameValue : "";
    const submittedPassword = password;
    setPassword("");
    if (nativeMode) {
      const trimmedLabel = deviceLabel.trim().slice(0, 120);
      await auth.logIn({
        login_name: loginName,
        password: submittedPassword,
        device_label: trimmedLabel || undefined,
      });
      return;
    }
    await auth.logIn({ login_name: loginName, password: submittedPassword });
  }

  return (
    <form
      aria-busy={submitting}
      onSubmit={(event) => {
        void submit(event);
      }}
    >
      {nativeMode && serverUrl && (
        <p className="intro">
          Server: <strong>{serverUrl}</strong>
        </p>
      )}
      <div className="field">
        <FieldLabel required htmlFor="login-name">
          Login name
        </FieldLabel>
        <input
          id="login-name"
          name="login_name"
          autoComplete="username"
          required
          disabled={submitting}
        />
      </div>
      <div className="field">
        <FieldLabel required htmlFor="password">
          Password
        </FieldLabel>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          disabled={submitting}
          value={password}
          onChange={(event) => {
            setPassword(event.currentTarget.value);
          }}
        />
      </div>
      {nativeMode && (
        <div className="field">
          <FieldLabel required htmlFor="device-label">
            Device name
          </FieldLabel>
          <input
            id="device-label"
            name="device_label"
            maxLength={120}
            required
            disabled={submitting}
            value={deviceLabel}
            onChange={(event) => {
              setDeviceLabel(event.currentTarget.value);
            }}
          />
        </div>
      )}
      {message && (
        <p
          className="notice notice--error"
          role="alert"
          ref={errorRef}
          tabIndex={-1}
        >
          {message}
        </p>
      )}
      <div className="actions">
        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
        {nativeMode && canChangeServer() && (
          <button
            type="button"
            className="button--secondary"
            disabled={submitting}
            onClick={() => {
              triggerChangeServer();
            }}
          >
            Change server
          </button>
        )}
      </div>
    </form>
  );
}
