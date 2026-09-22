import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { ApiError } from "../auth/api";
import { FormActions, FormSection } from "../components/ReferenceUI";
import { InfoDisclosure } from "../components/ContextualHelp";
import {
  deleteBotanicalIdentityCover,
  getBotanicalIdentityCover,
  setExternalBotanicalIdentityCover,
  setLocalBotanicalIdentityCover,
  type BotanicalIdentityCover as Cover,
} from "../botanical-identities/api";
import { PhotoDialog } from "./PhotosSection";

type CoverState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; cover: Cover | null };

function displayAttribution(value: string): string {
  try {
    const url = new URL(value);
    if (url.protocol === "https:" || url.protocol === "http:")
      return url.hostname.replace(/^www\./, "");
  } catch {
    // Attribution is ordinary text rather than a URL.
  }
  return value;
}

function saveError(error: unknown): string {
  if (error instanceof ApiError && error.status === 422)
    return "Check the cover details. External links need public HTTPS hosts and attribution is required.";
  if (error instanceof ApiError && error.status === 409)
    return "The former local cover needs cleanup. Retry the change or remove the cover first.";
  return "Florabase could not save this cover image.";
}

export function BotanicalIdentityCover({
  identityId,
  identityLabel,
  csrfToken,
  integrated = false,
}: {
  integrated?: boolean;
  identityId: string;
  identityLabel: string;
  csrfToken: string;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<CoverState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [editor, setEditor] = useState<"local" | "external" | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [broken, setBroken] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void getBotanicalIdentityCover(identityId, controller.signal)
      .then((cover) => {
        setState({ status: "ready", cover });
        setBroken(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, identityId]);

  const cover = state.status === "ready" ? state.cover : null;

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor || pending) return;
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      let saved: Cover;
      if (editor === "local") {
        const file = fileInput.current?.files?.[0];
        if (!file) {
          setError("Choose a JPEG, PNG, or WebP image.");
          return;
        }
        saved = await setLocalBotanicalIdentityCover(
          identityId,
          file,
          csrfToken,
        );
      } else {
        if (form.get("privacy_acknowledged") !== "on") {
          setError("Confirm the external-image privacy notice before saving.");
          return;
        }
        const field = (name: string) => {
          const value = form.get(name);
          return typeof value === "string" ? value : "";
        };
        saved = await setExternalBotanicalIdentityCover(
          identityId,
          {
            image_url: field("image_url"),
            source_url: field("source_url"),
            attribution: field("attribution"),
            licence_label: field("licence_label") || null,
            licence_url: field("licence_url") || null,
            privacy_acknowledged: true,
          },
          csrfToken,
        );
      }
      setState({ status: "ready", cover: saved });
      setBroken(false);
      setEditor(null);
      setNotice("Cover image was saved.");
    } catch (saveFailure: unknown) {
      setError(saveError(saveFailure));
      if (saveFailure instanceof ApiError && saveFailure.status >= 409) {
        setAttempt((value) => value + 1);
      }
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      await deleteBotanicalIdentityCover(identityId, csrfToken);
      setState({ status: "ready", cover: null });
      setConfirmRemove(false);
      setBroken(false);
      setNotice("Cover image was removed.");
    } catch (removeFailure: unknown) {
      setError(
        removeFailure instanceof ApiError && removeFailure.status === 409
          ? "The local cover cleanup is pending. Retry removal."
          : "Florabase could not remove this cover image. Retry removal.",
      );
      setConfirmRemove(false);
      setAttempt((value) => value + 1);
    } finally {
      setPending(false);
    }
  }

  return (
    <section
      className={
        integrated ? "identity-cover identity-cover--hero" : "identity-cover"
      }
      aria-label="Representative image"
    >
      <div className="identity-cover__heading">
        {!integrated && (
          <div>
            <p className="eyebrow">Representative image</p>
            <h3>Identity cover</h3>
          </div>
        )}
        {state.status === "ready" && (
          <details
            className="cover-actions"
            open={integrated ? undefined : true}
          >
            <summary>{cover ? "Manage cover" : "Add cover"}</summary>
            <div className="actions">
              <button
                className="button--secondary"
                type="button"
                onClick={() => {
                  setError(null);
                  setEditor(cover?.kind ?? "local");
                }}
              >
                {cover ? "Change cover" : "Set cover image"}
              </button>
              {cover && (
                <button
                  className="button--danger"
                  type="button"
                  onClick={() => {
                    setConfirmRemove(true);
                  }}
                >
                  {cover.kind === "local" && cover.deletion_pending
                    ? "Retry removal"
                    : "Remove cover"}
                </button>
              )}
            </div>
          </details>
        )}
      </div>

      {notice && (
        <p className="notice notice--success" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}
      {state.status === "loading" && (
        <p role="status">Loading identity cover…</p>
      )}
      {state.status === "error" && (
        <div className="notice notice--error">
          <p>Florabase could not load this identity’s cover.</p>
          <button
            type="button"
            onClick={() => {
              setAttempt((value) => value + 1);
            }}
          >
            Retry
          </button>
        </div>
      )}
      {state.status === "ready" && !cover && (
        <div className="identity-cover__placeholder">
          <svg viewBox="0 0 120 120" fill="none" aria-hidden="true">
            <path
              d="M40 102C57 80 61 49 78 18M58 70C30 74 25 54 26 43C45 42 62 53 58 70ZM67 48C89 53 100 37 102 24C83 23 71 32 67 48Z"
              stroke="currentColor"
              strokeWidth="2"
            />
          </svg>
          <p className={integrated ? "sr-only" : undefined}>
            No representative cover image is set.
          </p>
          <small>
            Collection photos remain attached to their specific collection
            records.
          </small>
        </div>
      )}
      {state.status === "ready" && cover && (
        <div className="identity-cover__content">
          <div className="identity-cover__image-frame">
            {cover.kind === "local" && cover.deletion_pending ? (
              <div className="notice notice--error">
                Local cover deletion is pending. Its protected content is no
                longer displayed; retry removal or replacement.
              </div>
            ) : broken ? (
              <div className="notice notice--error" role="alert">
                The {cover.kind === "local" ? "uploaded" : "external"} cover
                image is unavailable.
              </div>
            ) : (
              <img
                alt={`Representative image for ${identityLabel}`}
                decoding="async"
                loading="lazy"
                referrerPolicy={
                  cover.kind === "external" ? "no-referrer" : undefined
                }
                src={
                  cover.kind === "local"
                    ? (cover.content_url ?? "")
                    : cover.image_url
                }
                onError={() => {
                  setBroken(true);
                }}
              />
            )}
          </div>
          <div className="identity-cover__metadata">
            {cover.kind === "local" && <strong>Locally managed cover</strong>}
            {cover.kind === "external" && (
              <>
                <p>
                  <strong>Photo:</strong>{" "}
                  {displayAttribution(cover.attribution)}
                </p>
                <a
                  href={cover.source_url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  Source
                </a>
                {cover.licence_label && !cover.licence_url && (
                  <p>Licence: {cover.licence_label}</p>
                )}
                {cover.licence_label && cover.licence_url && (
                  <a
                    href={cover.licence_url}
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    Licence: {cover.licence_label}
                  </a>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {editor && (
        <PhotoDialog
          className="identity-cover-dialog"
          title={cover ? "Change identity cover" : "Set identity cover"}
          onClose={() => {
            if (!pending) setEditor(null);
          }}
        >
          <div className="segmented-control" aria-label="Cover source">
            <button
              aria-pressed={editor === "local"}
              type="button"
              onClick={() => {
                setEditor("local");
                setError(null);
              }}
            >
              Upload local image
            </button>
            <button
              aria-pressed={editor === "external"}
              type="button"
              onClick={() => {
                setEditor("external");
                setError(null);
              }}
            >
              Use external image
            </button>
          </div>
          <form onSubmit={(event) => void submit(event)}>
            <FormSection
              title={editor === "local" ? "Upload image" : "Source and credit"}
            >
              {editor === "local" ? (
                <div className="field">
                  <label htmlFor="identity-cover-file">Image file</label>
                  <input
                    accept="image/jpeg,image/png,image/webp"
                    id="identity-cover-file"
                    ref={fileInput}
                    required
                    type="file"
                  />
                  <small>JPEG, PNG, or WebP; maximum 25 MiB.</small>
                </div>
              ) : (
                <>
                  <div className="field">
                    <label htmlFor="identity-cover-image-url">Image URL</label>
                    <input
                      defaultValue={
                        cover?.kind === "external" ? cover.image_url : ""
                      }
                      id="identity-cover-image-url"
                      maxLength={2048}
                      name="image_url"
                      required
                      type="url"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="identity-cover-source-url">
                      Source/page URL
                    </label>
                    <input
                      defaultValue={
                        cover?.kind === "external" ? cover.source_url : ""
                      }
                      id="identity-cover-source-url"
                      maxLength={2048}
                      name="source_url"
                      required
                      type="url"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="identity-cover-attribution">
                      Attribution
                    </label>
                    <textarea
                      defaultValue={
                        cover?.kind === "external" ? cover.attribution : ""
                      }
                      id="identity-cover-attribution"
                      maxLength={2000}
                      name="attribution"
                      required
                      rows={2}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="identity-cover-licence-label">
                      Licence label (optional)
                    </label>
                    <input
                      defaultValue={
                        cover?.kind === "external"
                          ? (cover.licence_label ?? "")
                          : ""
                      }
                      id="identity-cover-licence-label"
                      maxLength={2000}
                      name="licence_label"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="identity-cover-licence-url">
                      Licence URL (optional)
                    </label>
                    <input
                      defaultValue={
                        cover?.kind === "external"
                          ? (cover.licence_url ?? "")
                          : ""
                      }
                      id="identity-cover-licence-url"
                      maxLength={2048}
                      name="licence_url"
                      type="url"
                    />
                  </div>
                  <InfoDisclosure label="More information about image credit and licence">
                    <p>
                      Use the image URL for the image itself and the source/page
                      URL for the page where you found it. Copy the creator or
                      source credit into Attribution, and record the licence
                      label and link when the source provides them.
                    </p>
                  </InfoDisclosure>
                  <label className="checkbox-field privacy-confirmation">
                    <input
                      name="privacy_acknowledged"
                      required
                      type="checkbox"
                    />
                    <span>
                      Using an external image as this identity’s cover will
                      cause your browser to contact that image host when the
                      cover is displayed. The host can see normal network
                      information such as your IP address.
                    </span>
                  </label>
                </>
              )}
            </FormSection>
            {error && (
              <p className="notice notice--error" role="alert">
                {error}
              </p>
            )}
            <FormActions>
              <button
                className="button--secondary"
                disabled={pending}
                type="button"
                onClick={() => {
                  setEditor(null);
                }}
              >
                Cancel
              </button>
              <button disabled={pending} type="submit">
                {pending ? "Saving…" : "Save cover"}
              </button>
            </FormActions>
          </form>
        </PhotoDialog>
      )}

      {confirmRemove && cover && (
        <PhotoDialog
          title="Remove identity cover?"
          onClose={() => {
            if (!pending) setConfirmRemove(false);
          }}
        >
          <p>
            {cover.kind === "local"
              ? "The locally managed image and its protected binary will be deleted."
              : "Only Florabase metadata will be removed. No request is sent to the external host."}
          </p>
          <div className="actions">
            <button
              className="button--danger"
              disabled={pending}
              type="button"
              onClick={() => void remove()}
            >
              {pending ? "Removing…" : "Remove cover"}
            </button>
            <button
              className="button--secondary"
              disabled={pending}
              type="button"
              onClick={() => {
                setConfirmRemove(false);
              }}
            >
              Cancel
            </button>
          </div>
        </PhotoDialog>
      )}
    </section>
  );
}
