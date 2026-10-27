import { useEffect, useRef, useState } from "react";
import { PhotoDialog } from "../photos/PhotosSection";
import { ApiError } from "../auth/api";
import { useAuth } from "../auth/context";
import {
  getMedia,
  saveLocalCopy,
  type MediaAsset,
  type MediaDetail,
} from "./api";
import { MediaPreview } from "./MediaPreview";
import { mediaError } from "./helpers";
import { mediaDetailHash, navigateMedia } from "./navigation";
import { mediaTargets } from "./targets";

/** An explicit inspection loads one original and its real relationship graph. */
export function MediaQuickPreview({
  asset,
  onClose,
  onSaved,
}: {
  asset: MediaAsset;
  onClose: () => void;
  onSaved: () => void;
}) {
  const auth = useAuth();
  const [detail, setDetail] = useState<MediaDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedLocally, setSavedLocally] = useState(false);
  const saveInFlight = useRef(false);
  const saveStatus = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    void getMedia(asset.id, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setDetail(value);
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        if (failure instanceof ApiError && failure.status === 401)
          auth.sessionExpired();
        else setError(mediaError(failure));
      });
    return () => {
      controller.abort();
    };
  }, [asset.id, attempt, auth]);
  useEffect(() => {
    if (savedLocally) saveStatus.current?.focus();
  }, [savedLocally]);
  async function saveCopy() {
    if (!detail || saveInFlight.current) return;
    saveInFlight.current = true;
    setSaving(true);
    setSaveError(null);
    try {
      const token =
        auth.state.status === "authenticated" ? auth.state.csrfToken : "";
      const saved = await saveLocalCopy(detail.id, token);
      setDetail((current) => (current ? { ...current, ...saved } : current));
      setSavedLocally(true);
      onSaved();
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401)
        auth.sessionExpired();
      else setSaveError(mediaError(failure));
    } finally {
      saveInFlight.current = false;
      setSaving(false);
    }
  }
  return (
    <PhotoDialog
      title="Quick Preview"
      className="media-preview-dialog"
      onClose={onClose}
    >
      <div className="media-preview-actions actions">
        <button type="button" className="button--secondary" onClick={onClose}>
          Close preview
        </button>
        <a
          className="button-link"
          href={mediaDetailHash(asset.id)}
          onClick={(event) => {
            if (
              event.button ||
              event.metaKey ||
              event.ctrlKey ||
              event.shiftKey ||
              event.altKey
            )
              return;
            event.preventDefault();
            onClose();
            navigateMedia(mediaDetailHash(asset.id));
          }}
        >
          Open media details
        </a>
      </div>
      <h4>
        {asset.title ?? asset.original_filename ?? "External image reference"}
      </h4>
      {error ? (
        <div role="alert" className="notice notice--error">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => {
              setError(null);
              setAttempt((value) => value + 1);
            }}
          >
            Retry preview
          </button>
        </div>
      ) : !detail ? (
        <p role="status">Loading preview…</p>
      ) : (
        <div className="media-preview-layout">
          <MediaPreview asset={detail} full allowExternal />
          <div>
            <p>
              {detail.kind === "local"
                ? "Local image"
                : detail.content_url
                  ? "External reference · local copy saved"
                  : "External reference · not stored locally"}
            </p>
            {detail.kind === "external" && !detail.content_url && (
              <section aria-label="Save a protected local copy">
                <p>
                  Saving contacts the external source and stores a protected
                  local copy in Florabase.
                </p>
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => {
                    void saveCopy();
                  }}
                >
                  {saving ? "Saving local copy…" : "Save local copy"}
                </button>
                {saveError && <p role="alert">{saveError}</p>}
              </section>
            )}
            {savedLocally &&
              detail.kind === "external" &&
              detail.content_url && (
                <p ref={saveStatus} role="status" tabIndex={-1}>
                  Protected local copy saved.
                </p>
              )}
            {detail.width && detail.height && (
              <p>
                {detail.width} × {detail.height} px
              </p>
            )}
            {detail.attribution && (
              <p className="media-preview-credit">{detail.attribution}</p>
            )}
            {detail.licence_label && (
              <p>
                {detail.licence_url ? (
                  <a href={detail.licence_url} target="_blank" rel="noreferrer">
                    {detail.licence_label}
                  </a>
                ) : (
                  detail.licence_label
                )}
              </p>
            )}
            <h4>Linked records ({detail.links.length})</h4>
            {detail.links.length ? (
              <ul className="media-preview-links">
                {detail.links.map((link) => (
                  <li key={link.id}>
                    <a href={link.target_url}>{link.target_label}</a>
                    <p>
                      {
                        mediaTargets.find(
                          (type) => type.id === link.target_type,
                        )?.label
                      }
                      {link.is_primary && " · Primary image for this record"}
                    </p>
                    {link.caption && <p>{link.caption}</p>}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No record links. The asset stays available in Media.</p>
            )}
            <h4>Botanical Identity covers ({detail.covers.length})</h4>
            {detail.covers.length ? (
              <ul>
                {detail.covers.map((cover) => (
                  <li key={cover.id}>
                    <a href={cover.url}>{cover.label}</a> · Current cover
                  </li>
                ))}
              </ul>
            ) : (
              <p>No cover references.</p>
            )}
          </div>
        </div>
      )}
    </PhotoDialog>
  );
}
