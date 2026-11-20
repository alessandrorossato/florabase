import { useState } from "react";
import { useProtectedImage } from "../photos/useProtectedImage";
import type { MediaAsset } from "./api";

export function MediaPreview({
  asset,
  full = false,
  allowExternal = false,
}: {
  asset: MediaAsset;
  full?: boolean;
  allowExternal?: boolean;
}) {
  const [loadExternal, setLoadExternal] = useState(false);
  const [broken, setBroken] = useState(false);
  const alt = asset.title ?? asset.original_filename ?? "Media image";
  const rawSrc = asset.deletion_pending
    ? null
    : asset.content_url != null
      ? full
        ? asset.content_url
        : asset.thumbnail_url
      : loadExternal
        ? asset.image_url
        : null;
  const [mediaTarget, media] = useProtectedImage({
    rawUrl: rawSrc,
    onError: () => {
      setBroken(true);
    },
  });
  if (broken || media.failed)
    return (
      <div className="media-image media-placeholder" role="status">
        Image unavailable
      </div>
    );
  if (rawSrc && media.src && !asset.deletion_pending)
    return (
      <img
        ref={mediaTarget}
        className="media-image"
        src={media.src}
        alt={alt}
        loading="lazy"
        decoding="async"
        referrerPolicy={media.referrerPolicy ?? "no-referrer"}
        onError={() => {
          setBroken(true);
        }}
      />
    );
  return (
    <div ref={mediaTarget} className="media-image media-placeholder">
      <span aria-hidden="true">▧</span>
      <span>
        {asset.deletion_pending
          ? "Deletion pending"
          : asset.kind === "external"
            ? "Not stored locally"
            : "Image unavailable"}
      </span>
      {allowExternal &&
        asset.kind === "external" &&
        asset.image_url &&
        !asset.deletion_pending && (
          <>
            <p>
              Loading contacts {new URL(asset.image_url).hostname} and shares
              normal network information, including your IP address.
            </p>
            <button
              type="button"
              className="button--secondary"
              onClick={() => {
                setLoadExternal(true);
              }}
            >
              Preview once
            </button>
          </>
        )}
    </div>
  );
}
