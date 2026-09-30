import { RecordVisual } from "../photos/RecordVisual";
import { StatStrip } from "../components/ReferenceUI";
import type { BotanicalIdentityResponse } from "./api";

export function IdentityImage({
  identity,
}: {
  identity: BotanicalIdentityResponse;
}) {
  return (
    <RecordVisual
      identity={identity}
      kind="identity"
      label={identity.display_label}
      allowExternalCover
      className={`identity-image identity-image--${identity.compact_cover_kind ?? "none"}`}
    />
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
