import { useState } from "react";
import { StatStrip } from "../components/ReferenceUI";
import type { BotanicalIdentityResponse } from "./api";

function IdentityImageFallback({ label }: { label: string }) {
  return (
    <>
      <svg viewBox="0 0 120 120" fill="none" aria-hidden="true">
        <path
          d="M40 102C57 80 61 49 78 18M58 70C30 74 25 54 26 43C45 42 62 53 58 70ZM67 48C89 53 100 37 102 24C83 23 71 32 67 48ZM48 87C28 91 18 79 17 66C34 62 47 71 48 87Z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      </svg>
      <span className="sr-only">{label}</span>
    </>
  );
}

export function IdentityImage({
  identity,
}: {
  identity: BotanicalIdentityResponse;
}) {
  const sourceKey = `${identity.id}:${identity.compact_cover_kind ?? "none"}:${identity.compact_external_cover_url ?? ""}`;
  const [brokenSource, setBrokenSource] = useState<string | null>(null);
  const imageSource =
    identity.compact_cover_kind === "local"
      ? `/api/v1/botanical-identities/${identity.id}/cover-image/thumbnail`
      : identity.compact_cover_kind === "external"
        ? identity.compact_external_cover_url
        : null;
  return (
    <span
      className={`identity-image identity-image--${identity.compact_cover_kind ?? "none"}`}
    >
      {imageSource && brokenSource !== sourceKey ? (
        <img
          alt={`Cover for ${identity.display_label}`}
          loading="lazy"
          decoding="async"
          referrerPolicy={
            identity.compact_cover_kind === "external"
              ? "no-referrer"
              : undefined
          }
          src={imageSource}
          onError={() => {
            setBrokenSource(sourceKey);
          }}
        />
      ) : (
        <IdentityImageFallback
          label={
            brokenSource === sourceKey
              ? "Cover unavailable"
              : identity.compact_cover_kind === "external"
                ? "External image"
                : "No cover image"
          }
        />
      )}
    </span>
  );
}

export function IdentityName({
  identity,
}: {
  identity: BotanicalIdentityResponse;
}) {
  return (
    <span className="identity-name">
      <i className="identity-scientific-name">{identity.scientific_name}</i>
      {identity.cultivar_name && (
        <>
          {" "}
          <span className="identity-cultivar">‘{identity.cultivar_name}’</span>
        </>
      )}
    </span>
  );
}

export function IdentityStats({
  identity,
}: {
  identity: BotanicalIdentityResponse;
}) {
  const counts = identity.collection_counts;
  if (!counts) return null;
  return (
    <StatStrip
      items={[
        { label: "Seed lots", value: counts.seed_lots },
        { label: "Sowings", value: counts.sowings },
        { label: "Plants", value: counts.plants },
        { label: "Plant groups", value: counts.plant_groups },
      ]}
    />
  );
}

export function IdentityCardContext({
  identity,
}: {
  identity: BotanicalIdentityResponse;
}) {
  const counts = identity.collection_counts;
  if (!counts) return null;
  const items = [
    [counts.seed_lots, "seed lot", "seed lots"],
    [counts.plants, "plant", "plants"],
    [counts.plant_groups, "plant group", "plant groups"],
    [counts.sowings, "sowing", "sowings"],
  ] as const;
  const text = items
    .filter(([n]) => n > 0)
    .slice(0, 2)
    .map(([n, one, many]) => `${String(n)} ${n === 1 ? one : many}`)
    .join(" · ");
  return (
    <small className="identity-card-context">
      {text || "No active records"}
    </small>
  );
}
