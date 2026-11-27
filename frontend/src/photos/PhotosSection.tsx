import { ActionButton } from "../components/Action";
import "./compact-gallery.css";
import { DetailEmptyState } from "../components/DetailEmptyState";
import { FieldLabel } from "../components/FieldLabel";
import {
  Fragment,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type SyntheticEvent,
} from "react";

import {
  ApiError,
  activeCsrfToken,
  isExpectedAuthCancellation,
  isPresentationRetainedState,
} from "../auth/api";
import { OverflowMenu } from "../components/ReferenceUI";
import { saveLocalCopy } from "../media/api";
import { ExternalCopyChoice } from "../media/ExternalCopyChoice";
import { useMediaDefaults } from "../media/useMediaDefaults";
import { MediaPicker } from "../media/MediaPicker";
import { useAuth } from "../auth/context";
import { useProtectedImage } from "./useProtectedImage";
import {
  clearPrimaryPhoto,
  createExternalImage,
  getPrimaryPhoto,
  listPhotos,
  removePhoto,
  setPrimaryPhoto,
  updateExternalImage,
  updateLocalPhoto,
  uploadPhoto,
  type CollectionPhoto,
  type ExternalImage,
  type PhotoTarget,
  type PrimaryPhoto,
} from "./api";

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; photos: CollectionPhoto[] };
type Editor = "local" | "external" | CollectionPhoto | null;

export function PhotoDialog({
  title,
  className = "",
  onClose,
  children,
}: {
  title: string;
  className?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const titleId = useId();
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previousFocus =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    dialog.current
      ?.querySelector<HTMLElement>(
        "input:not([type=hidden]), textarea, select, button, a[href]",
      )
      ?.focus();
    return () => {
      previousFocus?.focus();
    };
  }, []);
  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className={`context-dialog ${className}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        ref={dialog}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            onClose();
            return;
          }
          if (event.key !== "Tab" || !dialog.current) return;
          const focusable = Array.from(
            dialog.current.querySelectorAll<HTMLElement>(
              "button:not([disabled]), input:not([disabled]):not([type=hidden]), textarea:not([disabled]), select:not([disabled]), a[href]",
            ),
          );
          const first = focusable.at(0);
          const last = focusable.at(-1);
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last?.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first?.focus();
          }
        }}
      >
        <h3 id={titleId}>{title}</h3>
        {children}
      </div>
    </div>
  );
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError && error.status === 422)
    return "Check the photo details. External links must be absolute HTTPS URLs and attribution is required.";
  if (error instanceof ApiError && error.status === 409)
    return "The photo changed or is already pending deletion. Refresh the Photos section and try again.";
  return "Florabase could not save this photo. Check the connection and try again.";
}

function ProtectedSectionImage({
  rawUrl,
  alt,
  className,
  onLoad,
  onBroken,
  wrapper = false,
  detailsHref,
}: {
  rawUrl: string;
  alt: string;
  className?: string;
  onLoad?: () => void;
  onBroken: () => void;
  wrapper?: boolean;
  detailsHref?: string;
}) {
  const [mediaTarget, media] = useProtectedImage({
    rawUrl,
    onError: () => {
      onBroken();
    },
  });
  const imageNode = media.src ? (
    <img
      alt={alt}
      className={className}
      decoding="async"
      loading="lazy"
      referrerPolicy={media.referrerPolicy}
      src={media.src}
      onLoad={onLoad}
      onError={onBroken}
    />
  ) : null;
  if (detailsHref) {
    return (
      <a
        ref={mediaTarget}
        href={detailsHref}
        aria-label={`Open media details for ${alt}`}
        className="gallery-image-link"
      >
        {imageNode}
        <span className="gallery-open-label" aria-hidden="true">
          Open
        </span>
      </a>
    );
  }
  if (wrapper) {
    return <div ref={mediaTarget}>{imageNode}</div>;
  }
  return <span ref={mediaTarget}>{imageNode}</span>;
}

function ExternalPreview({
  photo,
  alt,
  compact = false,
  detailsHref,
}: {
  photo: ExternalImage;
  alt: string;
  compact?: boolean;
  detailsHref?: string;
}) {
  const [state, setState] = useState<"hidden" | "loading" | "loaded" | "error">(
    "hidden",
  );
  if (photo.thumbnail_url && state === "error")
    return <p role="status">The saved local image is unavailable.</p>;
  if (photo.thumbnail_url)
    return (
      <ProtectedSectionImage
        rawUrl={photo.thumbnail_url}
        alt={alt}
        className="collection-photo-image"
        detailsHref={detailsHref}
        onBroken={() => {
          setState("error");
        }}
      />
    );
  if (state === "hidden")
    return (
      <div className="external-preview-disclosure">
        {compact ? (
          <>
            <strong>External image</strong>
            <span>{new URL(photo.image_url).hostname}</span>
            <p className="field-help">
              Preview contacts this host and shares your IP address.
            </p>
          </>
        ) : (
          <p>
            Loading this image contacts {new URL(photo.image_url).hostname} and
            exposes normal network information, including your IP address, to
            that host.
          </p>
        )}
        <button
          type="button"
          onClick={() => {
            setState("loading");
          }}
        >
          Preview once
        </button>
      </div>
    );
  if (state === "error")
    return (
      <div className="notice notice--error" role="alert">
        <p>The external image is unavailable or could not be loaded.</p>
        <button
          type="button"
          onClick={() => {
            setState("hidden");
          }}
        >
          Dismiss
        </button>
      </div>
    );
  return (
    <div>
      {state === "loading" && (
        <p role="status" className={compact ? "gallery-loading" : undefined}>
          Loading external image…
        </p>
      )}
      <ProtectedSectionImage
        rawUrl={photo.image_url}
        alt={alt}
        className="collection-photo-image"
        detailsHref={detailsHref}
        onLoad={() => {
          setState("loaded");
        }}
        onBroken={() => {
          setState("error");
        }}
      />
    </div>
  );
}

export function PhotosSection({
  target,
  targetId,
  targetLabel,
  primaryPhoto = null,
  onPrimaryChanged,
  presentation = "standard",
}: {
  target: PhotoTarget;
  targetId: string;
  targetLabel: string;
  primaryPhoto?: PrimaryPhoto | null;
  onPrimaryChanged?: (photo: PrimaryPhoto | null) => void;
  presentation?: "standard" | "compact";
}) {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const headingId = useId();
  const fileInput = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [editor, setEditor] = useState<Editor>(null);
  // Only an open upload form needs the Settings → Media defaults.
  const mediaDefaults = useMediaDefaults(editor === "local");
  const [removing, setRemoving] = useState<CollectionPhoto | null>(null);
  const [pending, setPending] = useState(false);
  const [linking, setLinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failedCopy, setFailedCopy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [brokenLocal, setBrokenLocal] = useState<Set<string>>(new Set());
  const [primaryOverride, setPrimaryOverride] = useState<
    PrimaryPhoto | null | undefined
  >(undefined);
  const currentPrimary =
    primaryOverride === undefined ? primaryPhoto : primaryOverride;
  const supportsPrimary =
    target === "seed_lot" ||
    target === "plant" ||
    target === "plant_group" ||
    target === "harvest" ||
    target === "supplier" ||
    target === "vegetative_lot" ||
    target === "propagation_attempt";

  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    void listPhotos(target, targetId, capability, controller.signal)
      .then((photos) => {
        setState({ status: "ready", photos });
      })
      .catch((loadError: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(loadError))
          return;
        if (loadError instanceof ApiError && loadError.status === 401)
          sessionExpired();
        else setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, authorized, capability, sessionExpired, target, targetId]);

  if (!isPresentationRetainedState(auth.state)) return null;
  const csrfToken = activeCsrfToken(auth.state);

  async function refresh(success: string, refreshPrimary = false) {
    const photos = await listPhotos(target, targetId, capability);
    setState({ status: "ready", photos });
    if (supportsPrimary && refreshPrimary) {
      const primary = await getPrimaryPhoto(target, targetId, capability);
      setPrimaryOverride(primary);
      onPrimaryChanged?.(primary);
    }
    setNotice(success);
  }

  async function choosePrimary(photo: CollectionPhoto | null) {
    if (!supportsPrimary || pending || !csrfToken) return;
    setPending(true);
    setError(null);
    try {
      const next = photo
        ? await setPrimaryPhoto(
            target,
            targetId,
            { kind: photo.kind, photo_id: photo.id },
            csrfToken,
            capability,
          )
        : (await clearPrimaryPhoto(target, targetId, csrfToken, capability),
          null);
      setPrimaryOverride(next);
      onPrimaryChanged?.(next);
      setNotice(
        photo
          ? "Primary photo was changed."
          : "Primary designation was removed. The photo remains in Photos.",
      );
    } catch (primaryError: unknown) {
      if (isExpectedAuthCancellation(primaryError)) return;
      if (primaryError instanceof ApiError && primaryError.status === 401) {
        auth.sessionExpired();
        return;
      }
      setError(
        "Florabase could not change the primary photo. Refresh Photos and try again.",
      );
    } finally {
      setPending(false);
    }
  }

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor || pending || !csrfToken) return;
    const data = new FormData(event.currentTarget);
    const field = (name: string): string => {
      const value = data.get(name);
      return typeof value === "string" ? value : "";
    };
    const caption = field("caption");
    const attribution = field("attribution");
    setPending(true);
    setError(null);
    try {
      if (editor === "local") {
        const file = fileInput.current?.files?.[0];
        if (!file) {
          setError("Choose a JPEG, PNG, or WebP image.");
          return;
        }
        await uploadPhoto(
          target,
          targetId,
          file,
          {
            caption,
            attribution,
            licence_label: field("licence_label"),
            licence_url: field("licence_url"),
          },
          csrfToken,
          capability,
        );
      } else if (editor === "external") {
        const reference = await createExternalImage(
          target,
          targetId,
          {
            image_url: field("image_url"),
            source_url: field("source_url"),
            attribution,
            caption: caption || null,
          },
          csrfToken,
          capability,
        );
        if (data.get("save_local_copy") === "on" && reference.media_asset_id) {
          try {
            await saveLocalCopy(
              reference.media_asset_id,
              csrfToken,
              capability,
            );
          } catch (failure) {
            setFailedCopy(reference.media_asset_id);
            setEditor(null);
            await refresh("External reference saved.");
            if (failure instanceof ApiError && failure.status === 401)
              auth.sessionExpired();
            return;
          }
        }
      } else if (editor.kind === "local") {
        await updateLocalPhoto(
          editor.id,
          {
            caption: caption || null,
            attribution: attribution || null,
            display_order: Number(field("display_order")),
          },
          csrfToken,
          capability,
        );
      } else {
        await updateExternalImage(
          editor.id,
          {
            image_url: field("image_url"),
            source_url: field("source_url"),
            attribution,
            caption: caption || null,
            display_order: Number(field("display_order")),
          },
          csrfToken,
          capability,
        );
      }
      setEditor(null);
      try {
        await refresh(
          editor === "local" || editor === "external"
            ? "Photo was added."
            : "Photo details were saved.",
        );
      } catch (failure) {
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else
          setError(
            "Photo was saved, but Photos could not refresh. Reload this record.",
          );
      }
    } catch (saveError: unknown) {
      if (saveError instanceof ApiError && saveError.status === 401) {
        auth.sessionExpired();
        return;
      }
      setError(messageFor(saveError));
    } finally {
      setPending(false);
    }
  }

  async function retryCopy() {
    if (!failedCopy || pending || !csrfToken) return;
    setPending(true);
    setError(null);
    let saved = false;
    try {
      await saveLocalCopy(failedCopy, csrfToken, capability);
      saved = true;
      setFailedCopy(null);
      await refresh("Local copy saved.", true);
    } catch (failure) {
      if (isExpectedAuthCancellation(failure)) return;
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else
        setError(
          saved
            ? "Local copy saved, but Photos could not refresh. Reload this record."
            : "Local copy could not be downloaded. The external reference remains saved.",
        );
    } finally {
      setPending(false);
    }
  }

  async function confirmRemove() {
    if (!removing || pending || !csrfToken) return;
    setPending(true);
    setError(null);
    let removed = false;
    try {
      await removePhoto(removing.kind, removing.id, csrfToken, capability);
      removed = true;
      if (
        currentPrimary?.kind === removing.kind &&
        currentPrimary.photo_id === removing.id
      ) {
        setPrimaryOverride(null);
        onPrimaryChanged?.(null);
      }
      setRemoving(null);
      await refresh(
        "Media unlinked from this record. Asset retained in the library.",
        true,
      );
    } catch (removeError: unknown) {
      if (isExpectedAuthCancellation(removeError)) return;
      if (removeError instanceof ApiError && removeError.status === 401) {
        auth.sessionExpired();
        return;
      }
      if (removed) {
        setError(
          "Media was unlinked, but Photos could not be refreshed. Reload this record to see the latest state.",
        );
        return;
      }
      setError(
        removing.kind === "local"
          ? "Florabase could not unlink this image from the record. Refresh and try again."
          : "Florabase could not remove this external image reference. Try again.",
      );
      if (supportsPrimary) {
        try {
          const primary = await getPrimaryPhoto(target, targetId, capability);
          setPrimaryOverride(primary);
          onPrimaryChanged?.(primary);
          setState({
            status: "ready",
            photos: await listPhotos(target, targetId, capability),
          });
        } catch {
          // The removal error remains visible; retry refreshes the authoritative state.
        }
      }
    } finally {
      setPending(false);
    }
  }

  const MediaContainer = presentation === "compact" ? "div" : Fragment;
  const editing =
    editor && editor !== "local" && editor !== "external" ? editor : null;
  const externalEditor = editor === "external" || editing?.kind === "external";

  return (
    <section
      className={`photos-section${presentation === "compact" ? " photos-section--compact" : ""}`}
      aria-labelledby={headingId}
    >
      <div className="photos-heading">
        <div>
          {presentation !== "compact" && (
            <p className="eyebrow">
              {target === "supplier"
                ? "Supplier imagery"
                : "Collection evidence"}
            </p>
          )}
          <h4
            id={headingId}
            className={presentation === "compact" ? "sr-only" : undefined}
          >
            Photos
          </h4>
        </div>
        <div className="actions">
          <button
            type="button"
            onClick={() => {
              setEditor("local");
              setError(null);
            }}
          >
            {presentation === "compact" ? "Add media" : "Add new media"}
          </button>
          <button
            className="button--secondary"
            type="button"
            onClick={() => {
              setLinking(true);
            }}
          >
            {presentation === "compact"
              ? "Link existing"
              : "Link existing media"}
          </button>
          <button
            className="button--secondary"
            type="button"
            onClick={() => {
              setEditor("external");
              setError(null);
            }}
          >
            {presentation === "compact" ? "External" : "Add external image"}
          </button>
        </div>
      </div>
      {presentation !== "compact" && (
        <p className="field-help">
          Uploaded photos and saved local copies stay in protected Florabase
          storage. External references need Preview once to load remotely;
          manage saved copies in media details.
        </p>
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
      {state.status === "loading" ? (
        <p role="status">Loading Photos…</p>
      ) : state.status === "error" ? (
        <div className="notice notice--error" role="alert">
          <p>Florabase could not load Photos for this record.</p>
          <button
            type="button"
            onClick={() => {
              setState({ status: "loading" });
              setAttempt((value) => value + 1);
            }}
          >
            Retry Photos
          </button>
        </div>
      ) : state.photos.length === 0 ? (
        <DetailEmptyState>No photos yet.</DetailEmptyState>
      ) : (
        <div className="photo-gallery">
          {state.photos.map((photo) => {
            const alt = photo.caption ?? `Photo for ${targetLabel}`;
            return (
              <article className="photo-card" key={`${photo.kind}:${photo.id}`}>
                {presentation !== "compact" && (
                  <>
                    <p className="card-type">
                      {photo.kind === "local"
                        ? "Uploaded photo"
                        : photo.content_url
                          ? "External reference · local copy saved"
                          : "External reference · not stored locally"}
                      {currentPrimary?.kind === photo.kind &&
                        currentPrimary.photo_id === photo.id && (
                          <span className="primary-photo-badge">Primary</span>
                        )}
                    </p>
                  </>
                )}
                <MediaContainer
                  {...(presentation === "compact"
                    ? { className: "attached-media-preview" }
                    : {})}
                >
                  {photo.kind === "local" ? (
                    photo.deletion_pending ? (
                      <div className="notice notice--error">
                        <p>
                          Deletion is pending. The protected image is no longer
                          available.
                        </p>
                      </div>
                    ) : brokenLocal.has(photo.id) ? (
                      <div className="notice notice--error" role="alert">
                        The uploaded image content is unavailable.
                      </div>
                    ) : presentation === "compact" && photo.media_asset_id ? (
                      <ProtectedSectionImage
                        rawUrl={`/api/v1/media-assets/${photo.media_asset_id}/thumbnail`}
                        alt={alt}
                        className="collection-photo-image"
                        detailsHref={`#/media/${photo.media_asset_id}`}
                        onBroken={() => {
                          setBrokenLocal((ids) => new Set(ids).add(photo.id));
                        }}
                      />
                    ) : (
                      <ProtectedSectionImage
                        rawUrl={
                          photo.media_asset_id
                            ? `/api/v1/media-assets/${photo.media_asset_id}/thumbnail`
                            : `/api/v1/collection-photos/local/${photo.id}/thumbnail`
                        }
                        alt={alt}
                        className="collection-photo-image"
                        onBroken={() => {
                          setBrokenLocal((ids) => new Set(ids).add(photo.id));
                        }}
                      />
                    )
                  ) : (
                    <ExternalPreview
                      key={photo.thumbnail_url ?? photo.image_url}
                      photo={photo}
                      alt={alt}
                      compact={presentation === "compact"}
                      detailsHref={
                        presentation === "compact" && photo.media_asset_id
                          ? `#/media/${photo.media_asset_id}`
                          : undefined
                      }
                    />
                  )}
                </MediaContainer>
                <MediaContainer
                  {...(presentation === "compact"
                    ? { className: "attached-media-body" }
                    : {})}
                >
                  {presentation === "compact" && (
                    <>
                      <p className="card-type">
                        {photo.kind === "local" ? "Uploaded" : "External"}
                        {photo.kind === "external" && photo.content_url && (
                          <span> · Local copy</span>
                        )}
                        {currentPrimary?.kind === photo.kind &&
                          currentPrimary.photo_id === photo.id && (
                            <span className="primary-photo-badge">Primary</span>
                          )}
                      </p>
                    </>
                  )}
                  {photo.caption && (
                    <p className="photo-caption">{photo.caption}</p>
                  )}
                  {presentation !== "compact" && photo.attribution && (
                    <p>
                      <strong>Attribution:</strong> {photo.attribution}
                    </p>
                  )}
                  {presentation !== "compact" && photo.kind === "external" && (
                    <p>
                      <a
                        href={photo.source_url}
                        rel="noopener noreferrer"
                        target="_blank"
                      >
                        Source: {new URL(photo.source_url).hostname}
                      </a>
                    </p>
                  )}
                  <div className="actions">
                    {presentation !== "compact" && photo.media_asset_id && (
                      <a href={`#/media/${photo.media_asset_id}`}>
                        Open media details
                      </a>
                    )}
                    {presentation === "compact" ? (
                      <OverflowMenu
                        label="⋯"
                        ariaLabel={`Actions for ${alt}`}
                        disabled={pending}
                      >
                        {photo.media_asset_id && (
                          <a href={`#/media/${photo.media_asset_id}`}>
                            Open media details
                          </a>
                        )}
                        {supportsPrimary &&
                          (currentPrimary?.kind === photo.kind &&
                          currentPrimary.photo_id === photo.id ? (
                            <button
                              className="button--secondary"
                              type="button"
                              disabled={pending}
                              aria-label={`Remove primary designation from ${photo.caption ?? `${photo.kind} photo`}`}
                              onClick={() => void choosePrimary(null)}
                            >
                              Remove primary
                            </button>
                          ) : (
                            (photo.kind === "external" ||
                              !photo.deletion_pending) && (
                              <button
                                className="button--secondary"
                                type="button"
                                disabled={pending}
                                aria-label={`Set ${photo.caption ?? `${photo.kind} photo`} as primary`}
                                onClick={() => void choosePrimary(photo)}
                              >
                                Set as primary
                              </button>
                            )
                          ))}
                        {(photo.kind === "external" ||
                          !photo.deletion_pending) && (
                          <ActionButton
                            icon="edit"
                            className="button--secondary"
                            type="button"
                            onClick={() => {
                              setEditor(photo);
                              setError(null);
                            }}
                          >
                            Edit details
                          </ActionButton>
                        )}
                        <button
                          className="button--danger"
                          type="button"
                          onClick={() => {
                            setRemoving(photo);
                            setError(null);
                          }}
                        >
                          {photo.kind === "local" && photo.deletion_pending
                            ? "Unlink unavailable media"
                            : "Unlink from this record"}
                        </button>
                      </OverflowMenu>
                    ) : (
                      <>
                        {supportsPrimary &&
                          (currentPrimary?.kind === photo.kind &&
                          currentPrimary.photo_id === photo.id ? (
                            <button
                              className="button--secondary"
                              type="button"
                              disabled={pending}
                              aria-label={`Remove primary designation from ${photo.caption ?? `${photo.kind} photo`}`}
                              onClick={() => void choosePrimary(null)}
                            >
                              Remove primary
                            </button>
                          ) : (
                            (photo.kind === "external" ||
                              !photo.deletion_pending) && (
                              <button
                                className="button--secondary"
                                type="button"
                                disabled={pending}
                                aria-label={`Set ${photo.caption ?? `${photo.kind} photo`} as primary`}
                                onClick={() => void choosePrimary(photo)}
                              >
                                Set as primary
                              </button>
                            )
                          ))}
                        {(photo.kind === "external" ||
                          !photo.deletion_pending) && (
                          <ActionButton
                            icon="edit"
                            className="button--secondary"
                            type="button"
                            onClick={() => {
                              setEditor(photo);
                              setError(null);
                            }}
                          >
                            Edit details
                          </ActionButton>
                        )}
                        <button
                          className="button--danger"
                          type="button"
                          onClick={() => {
                            setRemoving(photo);
                            setError(null);
                          }}
                        >
                          {photo.kind === "local" && photo.deletion_pending
                            ? "Unlink unavailable media"
                            : "Unlink from this record"}
                        </button>
                      </>
                    )}
                  </div>
                </MediaContainer>
              </article>
            );
          })}
        </div>
      )}
      {linking && (
        <MediaPicker
          target={target}
          targetId={targetId}
          targetLabel={targetLabel}
          onClose={() => {
            setLinking(false);
          }}
          onLinked={() => {
            setLinking(false);
            void refresh("Media linked to this record.", true).catch(() => {
              setError(
                "Media was linked, but Photos could not refresh. Reload this record.",
              );
            });
          }}
        />
      )}
      {failedCopy && (
        <div className="notice notice--error" role="alert">
          <p>External reference saved. Local copy could not be downloaded.</p>
          <button
            type="button"
            className="button--secondary"
            disabled={pending}
            onClick={() => void retryCopy()}
          >
            Retry save
          </button>
        </div>
      )}
      {editor && (
        <PhotoDialog
          className="photo-dialog"
          title={
            editor === "local"
              ? "Add new media"
              : editor === "external"
                ? "Add external image"
                : "Edit photo details"
          }
          onClose={() => {
            if (!pending) setEditor(null);
          }}
        >
          <form onSubmit={(event) => void submit(event)}>
            {editor === "local" && (
              <label>
                <FieldLabel as="span" required>
                  Image file
                </FieldLabel>
                <input
                  ref={fileInput}
                  name="file"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  required
                />
              </label>
            )}
            {externalEditor && (
              <>
                <label>
                  <FieldLabel as="span" required>
                    HTTPS image URL
                  </FieldLabel>
                  <input
                    name="image_url"
                    type="url"
                    maxLength={2048}
                    defaultValue={
                      editing?.kind === "external" ? editing.image_url : ""
                    }
                    required
                  />
                </label>
                <label>
                  <FieldLabel as="span" required>
                    HTTPS source/page URL
                  </FieldLabel>
                  <input
                    name="source_url"
                    type="url"
                    maxLength={2048}
                    defaultValue={
                      editing?.kind === "external" ? editing.source_url : ""
                    }
                    required
                  />
                </label>
              </>
            )}
            <label>
              Caption
              <textarea
                name="caption"
                maxLength={2000}
                defaultValue={editing?.caption ?? ""}
              />
            </label>
            <label>
              <FieldLabel as="span" required={externalEditor}>
                Attribution (shared media)
              </FieldLabel>
              <textarea
                key={`${externalEditor ? "external" : "local"}:${mediaDefaults ? "configured" : "built-in"}`}
                name="attribution"
                maxLength={2000}
                defaultValue={
                  editing?.attribution ??
                  (editor === "local"
                    ? mediaDefaults?.media_default_attribution
                    : null) ??
                  ""
                }
                required={externalEditor}
              />
            </label>
            {editor === "local" && (
              <>
                <label>
                  Licence label
                  <input
                    key={mediaDefaults ? "configured" : "built-in"}
                    name="licence_label"
                    maxLength={2000}
                    defaultValue={
                      mediaDefaults?.media_default_licence_label ?? ""
                    }
                  />
                </label>
                <label>
                  Licence URL
                  <input
                    key={mediaDefaults ? "configured" : "built-in"}
                    name="licence_url"
                    type="url"
                    maxLength={2048}
                    defaultValue={
                      mediaDefaults?.media_default_licence_url ?? ""
                    }
                  />
                </label>
              </>
            )}
            {editor === "external" && <ExternalCopyChoice disabled={pending} />}
            {editing && (
              <label>
                <FieldLabel as="span" required>
                  Display order for this record
                </FieldLabel>
                <input
                  name="display_order"
                  type="number"
                  min={0}
                  max={2147483647}
                  required
                  defaultValue={editing.display_order}
                />
              </label>
            )}
            {editing && (
              <p>
                Caption and order apply only to this record. Attribution and
                external source details apply everywhere this media is used.
              </p>
            )}
            {error && (
              <p className="notice notice--error" role="alert">
                {error}
              </p>
            )}
            <div className="actions">
              <button disabled={pending} type="submit">
                {pending
                  ? "Saving…"
                  : editor === "external"
                    ? "Add image"
                    : "Save"}
              </button>
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
            </div>
          </form>
        </PhotoDialog>
      )}
      {removing && (
        <PhotoDialog
          title={`Unlink ${
            removing.kind === "local"
              ? "uploaded photo"
              : "external image reference"
          }?`}
          onClose={() => {
            if (!pending) setRemoving(null);
          }}
        >
          <p>
            Remove this record's link only. Its primary designation will be
            cleared if selected. The media asset, other record links, and
            identity cover references remain in the Gallery.
          </p>
          {error && (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          )}
          <div className="actions">
            <button
              className="button--danger"
              disabled={pending}
              type="button"
              onClick={() => void confirmRemove()}
            >
              {pending ? "Unlinking…" : "Unlink from this record"}
            </button>
            <button
              className="button--secondary"
              disabled={pending}
              type="button"
              onClick={() => {
                setRemoving(null);
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
