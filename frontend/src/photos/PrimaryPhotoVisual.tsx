import { useState } from "react";

import type { PrimaryPhoto } from "./api";
import { useProtectedImage } from "./useProtectedImage";

export function PrimaryPhotoVisual({
  photo,
  label,
  compact = false,
  fallback = "label",
}: {
  photo: PrimaryPhoto | null;
  label: string;
  compact?: boolean;
  fallback?: "label" | "omit" | "neutral";
}) {
  const [brokenPhotoId, setBrokenPhotoId] = useState<string | null>(null);
  const [mediaTarget, media] = useProtectedImage({
    rawUrl: photo?.thumbnail_url ?? null,
    onError: () => {
      if (photo) setBrokenPhotoId(photo.photo_id);
    },
  });
  const broken = brokenPhotoId === photo?.photo_id || media.failed;
  const neutral = (
    <span
      ref={mediaTarget}
      className="primary-photo-placeholder"
      aria-hidden="true"
    />
  );
  if (!photo) return fallback === "neutral" ? neutral : null;
  if (photo.kind === "external" && !photo.thumbnail_url)
    return fallback === "neutral" ? (
      neutral
    ) : fallback === "omit" ? null : (
      <span className="primary-photo-fallback">External primary photo</span>
    );
  if (broken || !photo.thumbnail_url)
    return fallback === "neutral" ? (
      neutral
    ) : fallback === "omit" ? null : (
      <span className="primary-photo-fallback">Primary photo unavailable</span>
    );
  if (!media.src) {
    return (
      <span
        ref={mediaTarget}
        className="primary-photo-placeholder"
        aria-hidden="true"
      />
    );
  }
  return (
    <img
      ref={mediaTarget}
      className={`primary-photo-thumb${compact ? " primary-photo-thumb--compact" : ""}`}
      src={media.src}
      alt={`Primary photo for ${label}`}
      loading="lazy"
      decoding="async"
      referrerPolicy={media.referrerPolicy}
      onError={() => {
        setBrokenPhotoId(photo.photo_id);
      }}
    />
  );
}
