import { IdentityCoverMetadata } from "../botanical-identities/IdentityCoverMetadata";
import { FieldLabel } from "../components/FieldLabel";
import { useEffect, useRef, useState, type SyntheticEvent } from "react";

import { ApiError, isExpectedAuthCancellation } from "../auth/api";
import { useAuth } from "../auth/context";
import { FormActions, FormSection } from "../components/ReferenceUI";
import { InfoDisclosure } from "../components/ContextualHelp";
import {
  deleteBotanicalIdentityCover,
  getBotanicalIdentityCover,
  setExternalBotanicalIdentityCover,
  setLocalBotanicalIdentityCover,
  type BotanicalIdentityCover as Cover,
} from "../botanical-identities/api";
import { ExternalCopyChoice } from "../media/ExternalCopyChoice";
import { saveLocalCopy } from "../media/api";
import { PhotoDialog } from "./PhotosSection";
import { useProtectedImage } from "./useProtectedImage";

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
    return "The cover changed or its media is unavailable. Refresh and retry the change.";
  return "Florabase could not save this cover image.";
}

export function BotanicalIdentityCover({
  identityId,
  identityLabel,
  csrfToken,
  integrated = false,
  showAssetMetadata = false,
  featured = false,
  onEditStateChange,
}: {
  integrated?: boolean;
  featured?: boolean;
  showAssetMetadata?: boolean;
  onEditStateChange?: (dirty: boolean, pending: boolean) => void;
  identityId: string;
  identityLabel: string;
  csrfToken: string;
}) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const fileInput = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<CoverState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [editor, setEditor] = useState<"local" | "external" | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [broken, setBroken] = useState(false);
  const [coverDirty, setCoverDirty] = useState(false);
  useEffect(() => {
    onEditStateChange?.(editor !== null && coverDirty, pending);
  }, [editor, coverDirty, pending, onEditStateChange]);
  function dismissEditor() {
    if (
      pending ||
      (coverDirty && !window.confirm("Discard unsaved cover changes?"))
    )
      return;
    setCoverDirty(false);
    setEditor(null);
  }
  function chooseSource(kind: "local" | "external") {
    if (pending || editor === kind) return;
    if (coverDirty && !window.confirm("Discard unsaved cover changes?")) return;
    setCoverDirty(false);
    setEditor(kind);
    setError(null);
  }

  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    void getBotanicalIdentityCover(identityId, capability, controller.signal)
      .then((cover) => {
        setState({ status: "ready", cover });
        setBroken(false);
      })
      .catch((loadFailure: unknown) => {
        if (
          controller.signal.aborted ||
          isExpectedAuthCancellation(loadFailure)
        )
          return;
        if (loadFailure instanceof ApiError && loadFailure.status === 401) {
          sessionExpired();
          return;
        }
        setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, authorized, capability, identityId, sessionExpired]);

  const cover = state.status === "ready" ? state.cover : null;
  const rawCoverUrl =
    cover && !(cover.kind === "local" && cover.deletion_pending)
      ? (cover.content_url ??
        (cover.kind === "external" ? cover.image_url : null))
      : null;
  const [mediaTarget, media] = useProtectedImage({
    rawUrl: rawCoverUrl,
    onError: () => {
      setBroken(true);
    },
  });

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
          capability,
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
          capability,
        );
      }
      setState({ status: "ready", cover: saved });
      setBroken(false);
      setEditor(null);
      setCoverDirty(false);
      setNotice("Cover image was saved.");
      if (
        editor === "external" &&
        form.get("save_local_copy") === "on" &&
        saved.media_asset_id
      ) {
        await copyCover(saved.media_asset_id);
      }
    } catch (saveFailure: unknown) {
      if (isExpectedAuthCancellation(saveFailure)) return;
      if (saveFailure instanceof ApiError && saveFailure.status === 401) {
        sessionExpired();
        return;
      }
      setError(saveError(saveFailure));
      if (saveFailure instanceof ApiError && saveFailure.status >= 409) {
        setAttempt((value) => value + 1);
      }
    } finally {
      setPending(false);
    }
  }

  /** Store the external cover in Florabase; the cover itself is already saved. */
  async function copyCover(mediaAssetId: string) {
    setPending(true);
    try {
      await saveLocalCopy(mediaAssetId, csrfToken, capability);
      setNotice("Cover image was saved with a local copy.");
      setAttempt((value) => value + 1);
    } catch (copyFailure: unknown) {
      if (isExpectedAuthCancellation(copyFailure)) return;
      if (copyFailure instanceof ApiError && copyFailure.status === 401) {
        sessionExpired();
        return;
      }
      setNotice(null);
      setError(
        "The cover was saved as an external reference, but Florabase could not save a local copy. Retry with Save local copy.",
      );
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      await deleteBotanicalIdentityCover(identityId, csrfToken, capability);
      setState({ status: "ready", cover: null });
      setConfirmRemove(false);
      setBroken(false);
      setNotice(
        "Cover reference removed. Media asset retained in the Gallery.",
      );
    } catch (removeFailure: unknown) {
      setError(
        removeFailure instanceof ApiError && removeFailure.status === 409
          ? "The cover reference changed or could not be removed. Refresh and retry."
          : "Florabase could not remove this cover image. Retry removal.",
      );
      setConfirmRemove(false);
      setAttempt((value) => value + 1);
    } finally {
      setPending(false);
    }
  }

  const dialogs = (
    <>
      {editor && (
        <PhotoDialog
          className="identity-cover-dialog"
          title={cover ? "Change identity cover" : "Set identity cover"}
          onClose={dismissEditor}
        >
          <div className="segmented-control" aria-label="Cover source">
            <button
              aria-pressed={editor === "local"}
              disabled={pending}
              type="button"
              onClick={() => {
                chooseSource("local");
              }}
            >
              Upload local image
            </button>
            <button
              aria-pressed={editor === "external"}
              disabled={pending}
              type="button"
              onClick={() => {
                chooseSource("external");
              }}
            >
              Use external image
            </button>
          </div>
          <form
            onChange={() => {
              setCoverDirty(true);
            }}
            onSubmit={(event) => void submit(event)}
          >
            <FormSection
              title={editor === "local" ? "Upload image" : "Source and credit"}
            >
              {editor === "local" ? (
                <div className="field">
                  <FieldLabel required htmlFor="identity-cover-file">
                    Image file
                  </FieldLabel>
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
                    <FieldLabel required htmlFor="identity-cover-image-url">
                      Image URL
                    </FieldLabel>
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
                    <FieldLabel required htmlFor="identity-cover-source-url">
                      Source/page URL
                    </FieldLabel>
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
                    <FieldLabel required htmlFor="identity-cover-attribution">
                      Attribution
                    </FieldLabel>
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
                      Licence label
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
                      Licence URL
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
                  <ExternalCopyChoice disabled={pending} />
                  <label className="checkbox-field privacy-confirmation">
                    <input
                      name="privacy_acknowledged"
                      required
                      type="checkbox"
                    />
                    <FieldLabel as="span" required>
                      Using an external image as this identity’s cover will
                      cause your browser to contact that image host when the
                      cover is displayed. The host can see normal network
                      information such as your IP address.
                    </FieldLabel>
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
                onClick={dismissEditor}
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
            This removes only the BotanicalIdentity cover reference. The media
            asset, its stored image and any collection links remain in the
            Gallery.
            {cover.kind === "external" &&
              " No request is sent to the external host."}
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
    </>
  );

  if (featured) {
    const unsaved =
      cover?.kind === "external" && !cover.content_url && cover.media_asset_id;
    return (
      <section
        className="identity-cover identity-cover-feature"
        aria-label="Representative image"
      >
        <div ref={mediaTarget} className="identity-cover-feature__image">
          {state.status === "loading" && (
            <p role="status">Loading identity cover…</p>
          )}
          {state.status === "ready" && !cover && <p>No cover image yet.</p>}
          {cover?.kind === "local" && cover.deletion_pending ? (
            <p>Local media deletion is pending; replace this cover.</p>
          ) : cover && (broken || media.failed) ? (
            <p role="status">The cover image could not be displayed.</p>
          ) : cover && media.src ? (
            <img
              alt={`Representative image for ${identityLabel}`}
              decoding="async"
              loading="lazy"
              referrerPolicy={media.referrerPolicy}
              src={media.src}
              onError={() => {
                setBroken(true);
              }}
            />
          ) : null}
        </div>
        <div className="identity-cover-feature__aside">
          <p className="eyebrow">Cover</p>
          {cover?.kind === "external" && (
            <p className="identity-cover-feature__caption">
              {displayAttribution(cover.attribution)}
              {cover.licence_label && (
                <>
                  {" · "}
                  {cover.licence_url ? (
                    <a
                      href={cover.licence_url}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      {cover.licence_label}
                    </a>
                  ) : (
                    cover.licence_label
                  )}
                </>
              )}
              {" · "}
              <a
                href={cover.source_url}
                rel="noopener noreferrer"
                target="_blank"
              >
                Source
              </a>
            </p>
          )}
          {cover?.media_asset_id &&
            cover.kind === "local" &&
            showAssetMetadata && (
              <IdentityCoverMetadata
                key={cover.media_asset_id}
                id={cover.media_asset_id}
              />
            )}
          {unsaved && (
            <p className="identity-cover-feature__badge">Not saved locally</p>
          )}
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
          {state.status === "error" && (
            <div className="notice notice--error" role="alert">
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
          {state.status === "ready" && (
            <div className="identity-cover-feature__actions">
              {unsaved && (
                <button
                  disabled={pending}
                  type="button"
                  onClick={() => void copyCover(unsaved)}
                >
                  {pending ? "Saving local copy…" : "Save local copy"}
                </button>
              )}
              <button
                className={unsaved ? "button--secondary" : undefined}
                disabled={pending}
                type="button"
                onClick={() => {
                  setError(null);
                  setCoverDirty(false);
                  setEditor(cover?.kind ?? "local");
                }}
              >
                {cover ? "Change cover" : "Set cover image"}
              </button>
              {cover?.media_asset_id && (
                <a
                  className="button-link button--secondary"
                  href={`#/media/${cover.media_asset_id}`}
                >
                  Open media record
                </a>
              )}
              {cover && (
                <button
                  className="button--danger"
                  disabled={pending}
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
          )}
        </div>
        {dialogs}
      </section>
    );
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
                  setCoverDirty(false);
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
          <div ref={mediaTarget} className="identity-cover__image-frame">
            {cover.kind === "local" && cover.deletion_pending ? (
              <div className="notice notice--error">
                Local media deletion is pending. Its protected content is not
                displayed. Remove or replace this cover reference; asset cleanup
                is a separate action in Media.
              </div>
            ) : broken || media.failed ? (
              <div className="notice notice--error" role="alert">
                The {cover.kind === "local" ? "uploaded" : "external"} cover
                image is unavailable.
              </div>
            ) : media.src ? (
              <img
                alt={`Representative image for ${identityLabel}`}
                decoding="async"
                loading="lazy"
                referrerPolicy={media.referrerPolicy}
                src={media.src}
                onError={() => {
                  setBroken(true);
                }}
              />
            ) : null}
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

      {cover?.media_asset_id && cover.kind === "local" && showAssetMetadata && (
        <IdentityCoverMetadata
          key={cover.media_asset_id}
          id={cover.media_asset_id}
        />
      )}
      {cover?.media_asset_id && !integrated && (
        <a href={`#/media/${cover.media_asset_id}`}>Open cover media record</a>
      )}

      {dialogs}
    </section>
  );
}
