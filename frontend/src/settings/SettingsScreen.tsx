import { useEffect, useRef, useState, type SyntheticEvent } from "react";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import { PageHeader } from "../components/ReferenceUI";
import { Page, LoadingState, ErrorState } from "../components/WorkspaceUI";
import {
  getApplicationSettings,
  savePublicQrBaseUrl,
  publicQrValidationMessage,
  type ApplicationSettings,
} from "./api";
import "./settings.css";
import { AppearanceSettings } from "../appearance/AppearanceSettings";

export function SettingsScreen({ focusQr = false }: { focusQr?: boolean }) {
  const auth = useAuth();
  const qrInput = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState<ApplicationSettings | null>(null);
  const [saved, setSaved] = useState<ApplicationSettings | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void getApplicationSettings(controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setValue(result);
        setSaved(result);
        setLoadError(false);
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else setLoadError(true);
      });
    return () => {
      controller.abort();
    };
  }, [auth, retry]);
  const loaded = value !== null;
  useEffect(() => {
    if (focusQr && loaded) qrInput.current?.focus();
  }, [focusQr, loaded]);
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!value || !("csrfToken" in auth.state)) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const result = await savePublicQrBaseUrl(
        value.public_qr_base_url ?? "",
        auth.state.csrfToken,
      );
      setValue(result);
      setSaved(result);
      setMessage("Application settings saved.");
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else
        setError(
          failure instanceof ApiError && failure.status === 422
            ? publicQrValidationMessage
            : "Could not save settings. Your changes are retained. Try again.",
        );
    } finally {
      setSaving(false);
    }
  }
  const dirty = JSON.stringify(value) !== JSON.stringify(saved);
  return (
    <Page className="settings-workspace" titleId="settings-heading">
      <PageHeader
        title="Settings"
        titleId="settings-heading"
        eyebrow="Application"
        description="Configuration and application utilities."
      />
      <div className="settings-content">
        <AppearanceSettings />
        <section
          className="settings-panel"
          aria-labelledby="settings-general-heading"
        >
          <h3 id="settings-general-heading">General</h3>
          {loadError ? (
            <ErrorState
              onRetry={() => {
                setLoadError(false);
                setRetry((n) => n + 1);
              }}
            >
              Could not load application settings.
            </ErrorState>
          ) : !value ? (
            <LoadingState>Loading settings…</LoadingState>
          ) : (
            <form
              onSubmit={(event) => {
                void submit(event);
              }}
            >
              <label htmlFor="qr-base-url">Public / QR base URL</label>
              <input
                ref={qrInput}
                id="qr-base-url"
                type="url"
                inputMode="url"
                maxLength={200}
                value={value.public_qr_base_url ?? ""}
                aria-describedby="qr-base-help"
                onChange={(event) => {
                  setValue({
                    ...value,
                    public_qr_base_url: event.target.value,
                  });
                  setMessage("");
                  setError("");
                }}
                placeholder="https://flora.example.com"
                disabled={saving}
              />
              <p id="qr-base-help" className="field-help">
                Public address for printed QR codes. Use an HTTP(S) origin
                without credentials, path, query or fragment. A trailing slash
                is normalized; leave blank to disable printing.
              </p>
              {error && (
                <p role="alert" className="notice notice--error">
                  {error}
                </p>
              )}
              {message && <p role="status">{message}</p>}
              <div className="actions">
                <button type="submit" disabled={saving || !dirty}>
                  {saving ? "Saving…" : "Save settings"}
                </button>
              </div>
            </form>
          )}
        </section>
        <section
          className="settings-panel"
          aria-labelledby="settings-tools-heading"
        >
          <h3 id="settings-tools-heading">Tools</h3>
          <div className="settings-tools">
            <a href="#/labels" aria-label="Labels">
              <span>
                <strong>Labels</strong>
                <span>Prepare and print physical collection labels.</span>
              </span>
              <span className="settings-tool-open" aria-hidden="true">
                Open →
              </span>
            </a>
            <a href="#/import-export" aria-label="Import / Export">
              <span>
                <strong>Import / Export</strong>
                <span>Import or export collection data.</span>
              </span>
              <span className="settings-tool-open" aria-hidden="true">
                Open →
              </span>
            </a>
          </div>
        </section>
      </div>
    </Page>
  );
}
