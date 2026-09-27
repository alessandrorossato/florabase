import { useState } from "react";

import type { PrimaryPhoto } from "./api";

export function PrimaryPhotoVisual({
  photo,
  label,
  compact = false,
}: {
  photo: PrimaryPhoto | null;
  label: string;
  compact?: boolean;
}) {
  const [brokenPhotoId, setBrokenPhotoId] = useState<string | null>(null);
  const broken = brokenPhotoId === photo?.photo_id;
  if (!photo) return null;
  if (photo.kind === "external")
    return (
      <span className="primary-photo-fallback">External primary photo</span>
    );
  if (broken || !photo.thumbnail_url)
    return (
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
