import { useState } from "react";
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
  const src =
    asset.content_url != null
      ? full
        ? asset.content_url
        : asset.thumbnail_url
      : loadExternal
        ? asset.image_url
        : null;
  if (broken)
    return (
      <div className="media-image media-placeholder" role="status">
        Image unavailable
      </div>
    );
  if (src && !asset.deletion_pending)
    return (
      <img
        className="media-image"
        src={src}
        alt={alt}
        loading="lazy"
        decoding="async"
        referrerPolicy="no-referrer"
        onError={() => {
          setBroken(true);
        }}
      />
    );
  return (
    <div className="media-image media-placeholder">
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
