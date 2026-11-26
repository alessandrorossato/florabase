import { useEffect, useMemo, useState } from "react";

import { ActionButton } from "../components/Action";
import { shareNativeBlob, type NativeImageViewerRequest } from "./fileActions";

export interface NativeImageViewerProps {
  request: NativeImageViewerRequest;
  onClose: () => void;
}

/**
 * Native-only full-screen viewer for protected original photos.
 * Revokes the object URL on close, auth capability invalidation, and unmount.
 * Reuses the already-fetched Blob bytes when sharing/saving (no duplicate fetch).
 */
export function NativeImageViewer({
  request,
  onClose,
}: NativeImageViewerProps) {
  const objectUrl = useMemo(
    () => URL.createObjectURL(request.blob),
    [request.blob],
  );
  const [sharing, setSharing] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);

  useEffect(() => {
    let revoked = false;
    const revoke = () => {
      if (revoked) return;
      revoked = true;
      URL.revokeObjectURL(objectUrl);
    };
    const unsubscribe = request.capability.subscribeInvalidation(() => {
      if (!request.capability.isAuthorized()) {
        revoke();
        onClose();
      }
    });
    return () => {
      unsubscribe();
      revoke();
    };
  }, [objectUrl, request.capability, onClose]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  async function handleShare() {
    if (sharing) return;
    setSharing(true);
    setShareError(null);
    try {
      await shareNativeBlob({
        blob: request.blob,
        filename: request.filename,
        contentType: request.contentType,
      });
    } catch (caught: unknown) {
      setShareError(
        caught instanceof Error
          ? caught.message
          : "Could not share this image.",
      );
    } finally {
      setSharing(false);
    }
  }

  return (
    <div
      className="native-image-viewer"
      role="dialog"
      aria-modal="true"
      aria-label={request.filename}
    >
      <div className="native-image-viewer__bar">
        <p className="native-image-viewer__title">{request.filename}</p>
        <div className="native-image-viewer__actions">
          <ActionButton
            type="button"
            disabled={sharing}
            onClick={() => {
              void handleShare();
            }}
          >
            {sharing ? "Sharing…" : "Share / Save"}
          </ActionButton>
          <ActionButton type="button" variant="quiet" onClick={onClose}>
            Close
          </ActionButton>
        </div>
      </div>
      {shareError !== null && (
        <p className="native-image-viewer__error" role="alert">
          {shareError}
        </p>
      )}
      <div className="native-image-viewer__stage">
        <img
          src={objectUrl}
          alt={request.filename}
          className="native-image-viewer__img"
        />
      </div>
    </div>
  );
}
