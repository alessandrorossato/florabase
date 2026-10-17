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

import { ApiError } from "../auth/api";
import { OverflowMenu } from "../components/ReferenceUI";
import { saveLocalCopy } from "../media/api";
import { ExternalCopyChoice } from "../media/ExternalCopyChoice";
import { MediaPicker } from "../media/MediaPicker";
import { useAuth } from "../auth/context";
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
  const ImageLink = detailsHref ? "a" : Fragment;
  const imageLinkProps = detailsHref
    ? {
        href: detailsHref,
        "aria-label": `Open media details for ${alt}`,
        className: "gallery-image-link",
      }
    : {};
  if (photo.thumbnail_url)
    return (
      <ImageLink {...imageLinkProps}>
        <img
          alt={alt}
          className="collection-photo-image"
          decoding="async"
          loading="lazy"
          src={photo.thumbnail_url}
          onError={() => {
            setState("error");
          }}
        />
        {detailsHref && (
          <span className="gallery-open-label" aria-hidden="true">
            Open
          </span>
        )}
      </ImageLink>
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
      <ImageLink {...imageLinkProps}>
        <img
          alt={alt}
          className="collection-photo-image"
          decoding="async"
          loading="lazy"
          referrerPolicy="no-referrer"
          src={photo.image_url}
          onLoad={() => {
            setState("loaded");
          }}
          onError={() => {
            setState("error");
          }}
        />
        {detailsHref && (
          <span className="gallery-open-label" aria-hidden="true">
            Open
          </span>
        )}
      </ImageLink>
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
  const headingId = useId();
  const fileInput = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [editor, setEditor] = useState<Editor>(null);
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
    target === "supplier";

  useEffect(() => {
    const controller = new AbortController();
    void listPhotos(target, targetId, controller.signal)
      .then((photos) => {
        setState({ status: "ready", photos });
      })
      .catch((loadError: unknown) => {
        if (controller.signal.aborted) return;
        if (loadError instanceof ApiError && loadError.status === 401)
          auth.sessionExpired();
        else setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, auth, target, targetId]);

  if (
    auth.state.status !== "authenticated" &&
    auth.state.status !== "logging-out" &&
    auth.state.status !== "logout-failed"
  )
    return null;
  const csrfToken = auth.state.csrfToken;

  async function refresh(success: string, refreshPrimary = false) {
    const photos = await listPhotos(target, targetId);
    setState({ status: "ready", photos });
    if (supportsPrimary && refreshPrimary) {
      const primary = await getPrimaryPhoto(target, targetId);
      setPrimaryOverride(primary);
      onPrimaryChanged?.(primary);
    }
    setNotice(success);
  }

  async function choosePrimary(photo: CollectionPhoto | null) {
    if (!supportsPrimary || pending) return;
    setPending(true);
    setError(null);
    try {
      const next = photo
        ? await setPrimaryPhoto(
            target,
            targetId,
            { kind: photo.kind, photo_id: photo.id },
            csrfToken,
          )
        : (await clearPrimaryPhoto(target, targetId, csrfToken), null);
      setPrimaryOverride(next);
      onPrimaryChanged?.(next);
      setNotice(
        photo
          ? "Primary photo was changed."
          : "Primary designation was removed. The photo remains in Photos.",
      );
    } catch (primaryError: unknown) {
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
    if (!editor || pending) return;
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
          caption,
          attribution,
          csrfToken,
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
        );
        if (data.get("save_local_copy") === "on" && reference.media_asset_id) {
          try {
            await saveLocalCopy(reference.media_asset_id, csrfToken);
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
    if (!failedCopy || pending) return;
    setPending(true);
    setError(null);
    let saved = false;
    try {
      await saveLocalCopy(failedCopy, csrfToken);
      saved = true;
      setFailedCopy(null);
      await refresh("Local copy saved.", true);
    } catch (failure) {
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
    if (!removing || pending) return;
    setPending(true);
    setError(null);
    let removed = false;
    try {
      await removePhoto(removing.kind, removing.id, csrfToken);
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
          const primary = await getPrimaryPhoto(target, targetId);
          setPrimaryOverride(primary);
          onPrimaryChanged?.(primary);
          setState({
            status: "ready",
            photos: await listPhotos(target, targetId),
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
                      <a
                        href={`#/media/${photo.media_asset_id}`}
                        className="gallery-image-link"
                        aria-label={`Open media details for ${alt}`}
                      >
                        <img
                          alt={alt}
                          className="collection-photo-image"
                          decoding="async"
                          loading="lazy"
                          src={`/api/v1/media-assets/${photo.media_asset_id}/thumbnail`}
                          onError={() => {
                            setBrokenLocal((ids) => new Set(ids).add(photo.id));
                          }}
                        />
                        <span className="gallery-open-label" aria-hidden="true">
                          Open
                        </span>
                      </a>
                    ) : (
                      <img
                        alt={alt}
                        className="collection-photo-image"
                        decoding="async"
                        loading="lazy"
                        src={
                          photo.media_asset_id
                            ? `/api/v1/media-assets/${photo.media_asset_id}/thumbnail`
                            : `/api/v1/collection-photos/local/${photo.id}/thumbnail`
                        }
                        onError={() => {
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
                          <button
                            className="button--secondary"
                            type="button"
                            onClick={() => {
                              setEditor(photo);
                              setError(null);
                            }}
                          >
                            Edit details
                          </button>
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
                          <button
                            className="button--secondary"
                            type="button"
                            onClick={() => {
                              setEditor(photo);
                              setError(null);
                            }}
                          >
                            Edit details
                          </button>
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
                name="attribution"
                maxLength={2000}
                defaultValue={editing?.attribution ?? ""}
                required={externalEditor}
              />
            </label>
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
