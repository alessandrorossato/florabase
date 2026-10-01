import { useState } from "react";

import type { PrimaryPhoto } from "./api";

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
  const broken = brokenPhotoId === photo?.photo_id;
  const neutral = (
    <span className="primary-photo-placeholder" aria-hidden="true" />
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
  return (
    <img
      className={`primary-photo-thumb${compact ? " primary-photo-thumb--compact" : ""}`}
      src={photo.thumbnail_url}
      alt={`Primary photo for ${label}`}
      loading="lazy"
      decoding="async"
      onError={() => {
        setBrokenPhotoId(photo.photo_id);
      }}
    />
  );
}
