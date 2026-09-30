import { useContext, useState } from "react";
import type { BotanicalIdentityResponse } from "../botanical-identities/api";
import { RecordIdentities } from "../components/recordPresentation";
import type { PrimaryPhoto } from "./api";

type Identity = Pick<BotanicalIdentityResponse, "id" | "display_label"> &
  Partial<BotanicalIdentityResponse>;
export type RecordVisualKind =
  "seed" | "sowing" | "plant" | "group" | "identity";
const placeholderPaths: Record<RecordVisualKind, string> = {
  seed: "M17 5C5 4 4 13 8 17s13 3 9-12ZM9 15l7-8",
  sowing:
    "M4 18h16M6 18v-5h12v5M12 13V5M12 9C6 10 5 6 6 4c4 0 6 2 6 5ZM12 11c5 0 7-3 6-6-4 0-6 3-6 6Z",
  plant:
    "M12 21V4M12 11C5 12 3 8 4 4c5 0 8 3 8 7ZM12 16c6 1 9-3 8-7-5-1-8 2-8 7Z",
  group:
    "M8 21V7M8 13C3 14 2 10 3 7c4 0 5 2 5 6ZM8 17c4 0 6-3 5-6-3 0-5 3-5 6ZM17 21V3M17 9c-4 0-5-3-4-6 3 0 4 3 4 6ZM17 14c4 0 6-3 5-6-3 0-5 3-5 6Z",
  identity:
    "M6 21C12 16 12 7 17 3M11 14C5 15 3 10 4 7c5 0 8 3 7 7ZM14 9c5 1 8-3 8-6-4-1-7 2-8 6Z",
};
export function RecordVisual({
  photo,
  identity: summary,
  kind,
  label,
  compact = false,
  allowExternalCover = false,
  className = "",
}: {
  photo?: PrimaryPhoto | null;
  identity?: Identity;
  kind: RecordVisualKind;
  label: string;
  compact?: boolean;
  // Botanical directory's persisted compact-cover policy permits external covers.
  // Collection/activity never opt in merely because an identity has an external cover.
  allowExternalCover?: boolean;
  className?: string;
}) {
  const identities = useContext(RecordIdentities);
  const identity = summary
    ? "scientific_name" in summary
      ? summary
      : (identities.get(summary.id) ?? summary)
    : undefined;
  const [broken, setBroken] = useState<ReadonlySet<string>>(new Set());
  const direct = photo?.kind === "local" ? photo.thumbnail_url : null;
  const cover =
    identity?.compact_cover_kind === "local"
      ? `/api/v1/botanical-identities/${identity.id}/cover-image/thumbnail`
      : allowExternalCover && identity?.compact_cover_kind === "external"
        ? identity.compact_external_cover_url
        : null;
  const source = [direct, cover].find((src) => src && !broken.has(src));
  const primary = source === direct;
  return (
    <span
      className={`record-visual record-visual--${kind}${compact ? " record-visual--compact" : ""} ${className}`}
    >
      {source ? (
        <img
          src={source}
          alt={`${primary ? "Primary photo" : "Cover"} for ${label}`}
          loading="lazy"
          decoding="async"
          referrerPolicy={
            !primary && identity?.compact_cover_kind === "external"
              ? "no-referrer"
              : undefined
          }
          onError={() => {
            setBroken((current) => new Set([...current, source]));
          }}
        />
      ) : (
        <>
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d={placeholderPaths[kind]}
              stroke="currentColor"
              strokeWidth="1.25"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="sr-only">
            {kind === "identity"
              ? source === undefined && (direct || cover)
                ? "Cover unavailable"
                : identity?.compact_cover_kind === "external"
                  ? "External image"
                  : "No cover image"
              : `${kind === "group" ? "Plant group" : kind[0].toUpperCase() + kind.slice(1)} image placeholder`}
          </span>
        </>
      )}
    </span>
  );
}
