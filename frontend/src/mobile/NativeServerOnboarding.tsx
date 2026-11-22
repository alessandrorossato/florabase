import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { FieldLabel } from "../components/FieldLabel";
import {
  probeFlorabaseHealth,
  type HealthProbeErrorKind,
  type HttpGetFn,
} from "./healthProbe";
import { createServerUrlStore, type ServerUrlStore } from "./preferences";
import { isNativeDebugBuild } from "./runtime";
import { validateServerUrl } from "./serverUrl";
import "./native-onboarding.css";

interface ConnectedServerState {
  serverUrl: string;
  httpStatus: number;
  status: "ok";
  serverVersion: string | null;
  serverRevision: string | null;
}

interface OnboardingError {
  category: "invalid-url" | HealthProbeErrorKind;
  heading: string;
  message: string;
}

function errorHeading(category: OnboardingError["category"]): string {
  switch (category) {
    case "invalid-url":
      return "Invalid server URL";
    case "tls":
      return "Certificate not trusted";
    case "cleartext":
      return "HTTPS required";
    case "unreachable":
      return "Server unreachable";
    case "http-error":
      return "Server error";
    case "non-florabase":
      return "Not a Florabase server";
  }
}

export interface NativeServerOnboardingProps {
  allowDebugHttp?: boolean;
  store?: ServerUrlStore;
  httpGet?: HttpGetFn;
}

export function NativeServerOnboarding({
  allowDebugHttp = isNativeDebugBuild(),
  store,
  httpGet,
}: NativeServerOnboardingProps) {
  const storeRef = useRef<ServerUrlStore>(store ?? createServerUrlStore());
  const errorRef = useRef<HTMLDivElement>(null);

  const [serverUrlInput, setServerUrlInput] = useState("");
  const [savedUrl, setSavedUrl] = useState<string | null>(null);
  const [loadingSaved, setLoadingSaved] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<OnboardingError | null>(null);
  const [connected, setConnected] = useState<ConnectedServerState | null>(null);

  useEffect(() => {
    let active = true;
    void storeRef.current
      .load()
      .then((persisted) => {
        if (!active) return;
        if (persisted !== null) {
          setSavedUrl(persisted);
          setServerUrlInput(persisted);
        }
      })
      .finally(() => {
        if (active) setLoadingSaved(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (error !== null) {
      errorRef.current?.focus();
    }
  }, [error]);

  async function handleSubmit(
    event: SyntheticEvent<HTMLFormElement, SubmitEvent>,
  ) {
    event.preventDefault();
    setError(null);

    const validation = validateServerUrl(serverUrlInput, { allowDebugHttp });
    if (!validation.ok) {
      setConnected(null);
      setError({
        category: "invalid-url",
        heading: errorHeading("invalid-url"),
        message: validation.error,
      });
      return;
    }

    setChecking(true);
    try {
      const probe = await probeFlorabaseHealth(validation.normalizedUrl, {
        httpGet,
        allowDebugHttp,
      });
      if (!probe.ok) {
        setConnected(null);
        setError({
          category: probe.kind,
          heading: errorHeading(probe.kind),
          message: probe.message,
        });
        return;
      }

      await storeRef.current.save(probe.serverUrl);
      setSavedUrl(probe.serverUrl);
      setServerUrlInput(probe.serverUrl);
      setConnected({
        serverUrl: probe.serverUrl,
        httpStatus: probe.httpStatus,
        status: probe.status,
        serverVersion: probe.serverVersion,
        serverRevision: probe.serverRevision,
      });
    } finally {
      setChecking(false);
    }
  }

  async function handleForgetSaved() {
    await storeRef.current.clear();
    setSavedUrl(null);
    setConnected(null);
    setError(null);
    setServerUrlInput("");
  }

  const versionDisplay =
    connected?.serverVersion !== null && connected?.serverVersion !== undefined
      ? connected.serverRevision !== null
        ? `${connected.serverVersion} (${connected.serverRevision})`
        : connected.serverVersion
      : "Not reported by /api/v1/health";

  return (
    <main className="mobile-onboarding">
      <section aria-labelledby="mobile-onboarding-title" className="card">
        <p className="eyebrow">Florabase Android (MOBILE-001 spike)</p>
        <h1 id="mobile-onboarding-title">Connect to your server</h1>
        <p className="intro">
          Enter the URL of your self-hosted Florabase server to verify
          connectivity.
        </p>

        <form
          aria-busy={checking}
          noValidate
          onSubmit={(event) => {
            void handleSubmit(event);
          }}
        >
          <div className="field">
            <FieldLabel required htmlFor="mobile-server-url">
              Server URL
            </FieldLabel>
            <input
              id="mobile-server-url"
              name="server_url"
              type="url"
              inputMode="url"
              autoCapitalize="none"
              autoCorrect="off"
              autoComplete="url"
              spellCheck={false}
              required
              disabled={checking || loadingSaved}
              placeholder={
                allowDebugHttp
                  ? "https://florabase.example.com or http://10.0.2.2:5173"
                  : "https://florabase.example.com"
              }
              value={serverUrlInput}
              onChange={(event) => {
                setServerUrlInput(event.currentTarget.value);
              }}
            />
            <p className="mobile-onboarding__hint">
              {allowDebugHttp
                ? "Debug build: https:// URLs and local http:// addresses (such as http://10.0.2.2:5173) are permitted."
                : "Requires an https:// URL. Private CA certificates installed in Android Settings are trusted."}
            </p>
          </div>

          {error !== null && (
            <div
              className="notice notice--error"
              role="alert"
              ref={errorRef}
              tabIndex={-1}
              data-error-category={error.category}
            >
              <strong>{error.heading}:</strong> {error.message}
            </div>
          )}

          <div className="mobile-onboarding__actions">
            <button type="submit" disabled={checking || loadingSaved}>
              {checking ? "Checking server…" : "Check server"}
            </button>
            {savedUrl !== null && (
              <button
                type="button"
                disabled={checking}
                onClick={() => {
                  void handleForgetSaved();
                }}
              >
                Forget saved URL
              </button>
            )}
          </div>
        </form>

        {savedUrl !== null && connected === null && !checking && (
          <p className="mobile-onboarding__hint" role="status">
            Saved server URL: {savedUrl}
          </p>
        )}

        {connected !== null && (
          <section
            aria-label="Server connection result"
            className="mobile-onboarding__result"
            role="status"
          >
            <h2>Server reachable</h2>
            <dl className="mobile-onboarding__meta">
              <div className="mobile-onboarding__meta-row">
                <dt>Server URL</dt>
                <dd>{connected.serverUrl}</dd>
              </div>
              <div className="mobile-onboarding__meta-row">
                <dt>Health check (/api/v1/health)</dt>
                <dd>
                  {connected.status} (HTTP {connected.httpStatus})
                </dd>
              </div>
              <div className="mobile-onboarding__meta-row">
                <dt>Server version</dt>
                <dd>{versionDisplay}</dd>
              </div>
              <div className="mobile-onboarding__meta-row">
                <dt>Saved on device</dt>
                <dd>Yes (Capacitor Preferences)</dd>
              </div>
            </dl>
            <p className="mobile-onboarding__next">
              Sign-in for the app arrives in MOBILE-002.
            </p>
          </section>
        )}
      </section>
    </main>
  );
}
