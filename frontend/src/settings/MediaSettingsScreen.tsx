import { useEffect, useState, type SyntheticEvent } from "react";
import {
  activeCsrfToken,
  ApiError,
  isExpectedAuthCancellation,
} from "../auth/api";
import { useAuth } from "../auth/context";
import { PageHeader } from "../components/ReferenceUI";
import { ErrorState, LoadingState, Page } from "../components/WorkspaceUI";
import { formText } from "../media/helpers";
import {
  getApplicationSettings,
  saveApplicationSettings,
  type ApplicationSettings,
} from "./api";
import "./settings.css";

type Load =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; settings: ApplicationSettings };

/** Settings → Media: installation-wide defaults for new media. */
export function MediaSettingsScreen() {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    getApplicationSettings(capability, controller.signal)
      .then((settings) => {
        setLoad({ status: "ready", settings });
      })
      .catch((failure: unknown) => {
        if (isExpectedAuthCancellation(failure)) return;
        if (failure instanceof ApiError && failure.status === 401)
          sessionExpired();
        else setLoad({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, capability, sessionExpired]);

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = activeCsrfToken(auth.state);
    if (!token || saving) return;
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setMessage("");
    setError("");
    try {
      // Preserve the latest QR and label preferences edited elsewhere.
      const latest = await getApplicationSettings(capability);
      const saved = await saveApplicationSettings(
        {
          ...latest,
          media_save_local_copy_default: form.get("save_local_copy") === "on",
          media_default_attribution: formText(form, "attribution") || null,
          media_default_licence_label: formText(form, "licence_label") || null,
          media_default_licence_url: formText(form, "licence_url") || null,
        },
        token,
        capability,
      );
      setLoad({ status: "ready", settings: saved });
      setMessage("Media settings saved.");
    } catch (failure) {
      if (isExpectedAuthCancellation(failure)) return;
      if (failure instanceof ApiError && failure.status === 401)
        sessionExpired();
      else
        setError(
          failure instanceof ApiError && failure.status === 422
            ? "Check the defaults. The licence URL must be an absolute HTTPS URL."
            : "Could not save media settings. Your changes are retained. Try again.",
        );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Page className="settings-workspace" titleId="media-settings-heading">
      <PageHeader
        title="Media"
        titleId="media-settings-heading"
        eyebrow="Settings"
        description="Defaults for new photos and media, for everyone using this Florabase."
      />
      <div className="settings-content">
        {load.status === "loading" ? (
          <LoadingState>Loading media settings…</LoadingState>
        ) : load.status === "error" ? (
          <ErrorState
            onRetry={() => {
              setLoad({ status: "loading" });
              setAttempt((value) => value + 1);
            }}
          >
            Could not load media settings.
          </ErrorState>
        ) : (
          <form
            key={JSON.stringify(load.settings)}
            onSubmit={(event) => {
              void submit(event);
            }}
            className="settings-content"
          >
            <section
              className="settings-panel"
              aria-labelledby="media-settings-copy"
            >
              <h3 id="media-settings-copy">External images</h3>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  name="save_local_copy"
                  defaultChecked={load.settings.media_save_local_copy_default}
                  disabled={saving}
                />
                Pre-select “Save a local copy” for new external images
              </label>
              <p className="field-help">
                This only sets the initial choice in the form. Florabase
                downloads an external image only when you save that image with
                the option selected; it never fetches remote images on its own.
              </p>
            </section>
            <section
              className="settings-panel"
              aria-labelledby="media-settings-credit"
            >
              <h3 id="media-settings-credit">Your uploads</h3>
              <p className="field-help">
                Prefilled when you upload your own photos in Media or a record’s
                Photos. You can change them for each upload. External images
                keep their author’s attribution and are never prefilled.
              </p>
              <label htmlFor="media-settings-attribution">
                Default attribution
              </label>
              <textarea
                id="media-settings-attribution"
                name="attribution"
                maxLength={2000}
                defaultValue={load.settings.media_default_attribution ?? ""}
                disabled={saving}
              />
              <label htmlFor="media-settings-licence">
                Default licence label
              </label>
              <input
                id="media-settings-licence"
                name="licence_label"
                maxLength={2000}
                defaultValue={load.settings.media_default_licence_label ?? ""}
                disabled={saving}
              />
              <label htmlFor="media-settings-licence-url">
                Default licence URL
              </label>
              <input
                id="media-settings-licence-url"
                name="licence_url"
                type="url"
                inputMode="url"
                maxLength={2048}
                defaultValue={load.settings.media_default_licence_url ?? ""}
                disabled={saving}
              />
            </section>
            {error && (
              <p role="alert" className="notice notice--error">
                {error}
              </p>
            )}
            {message && (
              <p role="status" className="notice notice--success">
                {message}
              </p>
            )}
            <div className="actions">
              <button type="submit" disabled={saving}>
                {saving ? "Saving…" : "Save media settings"}
              </button>
            </div>
          </form>
        )}
      </div>
    </Page>
  );
}
