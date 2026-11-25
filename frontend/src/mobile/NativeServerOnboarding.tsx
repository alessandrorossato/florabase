import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { FieldLabel } from "../components/FieldLabel";
import type { HttpGetFn } from "./healthProbe";
import { createServerUrlStore, type ServerUrlStore } from "./preferences";
import { isNativeDebugBuild } from "./runtime";
import { validateServerUrl } from "./serverUrl";
import {
  checkServerCompatibility,
  onboardingErrorHeading,
  type OnboardingError,
  type SystemInfo,
} from "./systemInfo";
import "./native-onboarding.css";

interface ConnectedServerState {
  serverUrl: string;
  info: SystemInfo;
}

export interface NativeServerOnboardingProps {
  allowDebugHttp?: boolean;
  store?: ServerUrlStore;
  httpGet?: HttpGetFn;
  appVersion?: string;
  initialServerUrl?: string | null;
  initialError?: OnboardingError | null;
  onConnected?: (serverUrl: string, info: SystemInfo) => void;
}

export function NativeServerOnboarding({
  allowDebugHttp = isNativeDebugBuild(),
  store,
  httpGet,
  appVersion,
  initialServerUrl = null,
  initialError = null,
  onConnected,
}: NativeServerOnboardingProps) {
  const storeRef = useRef<ServerUrlStore>(store ?? createServerUrlStore());
  const errorRef = useRef<HTMLDivElement>(null);

  const [serverUrlInput, setServerUrlInput] = useState(initialServerUrl ?? "");
  const [savedUrl, setSavedUrl] = useState<string | null>(initialServerUrl);
  const [loadingSaved, setLoadingSaved] = useState(initialServerUrl === null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<OnboardingError | null>(initialError);
  const [connected, setConnected] = useState<ConnectedServerState | null>(null);

  useEffect(() => {
    if (initialServerUrl !== null) return;
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
  }, [initialServerUrl]);

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
        heading: onboardingErrorHeading("invalid-url"),
        message: validation.error,
      });
      return;
    }

    setChecking(true);
    try {
      const result = await checkServerCompatibility(validation.normalizedUrl, {
        httpGet,
        allowDebugHttp,
        appVersion,
      });
      if (!result.ok) {
        setConnected(null);
        setError({
          category: result.kind,
          heading: onboardingErrorHeading(result.kind),
          message: result.message,
        });
        return;
      }

      await storeRef.current.save(result.serverUrl);
      setSavedUrl(result.serverUrl);
      setServerUrlInput(result.serverUrl);
      setConnected({
        serverUrl: result.serverUrl,
        info: result.info,
      });
      onConnected?.(result.serverUrl, result.info);
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

  return (
    <main className="mobile-onboarding">
      <section aria-labelledby="mobile-onboarding-title" className="card">
        <p className="eyebrow">Florabase Android</p>
        <h1 id="mobile-onboarding-title">Connect to your server</h1>
        <p className="intro">
          Enter the URL of your self-hosted Florabase server to verify
          compatibility and sign in.
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
              {checking ? "Checking server…" : "Connect"}
            </button>
            {savedUrl !== null && (
              <button
                type="button"
                className="button--secondary"
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

        {connected !== null && onConnected === undefined && (
          <section
            aria-label="Server connection result"
            className="mobile-onboarding__result"
            role="status"
          >
            <h2>Server compatible</h2>
            <dl className="mobile-onboarding__meta">
              <div className="mobile-onboarding__meta-row">
                <dt>Server URL</dt>
                <dd>{connected.serverUrl}</dd>
              </div>
              <div className="mobile-onboarding__meta-row">
                <dt>Server version</dt>
                <dd>{connected.info.serverVersion}</dd>
              </div>
              <div className="mobile-onboarding__meta-row">
                <dt>API version</dt>
                <dd>{connected.info.apiVersion}</dd>
              </div>
            </dl>
          </section>
        )}
      </section>
    </main>
  );
}
