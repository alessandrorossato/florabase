import { useMemo } from "react";
import {
  IdentityRecordMedia,
  type IdentityMediaRecord,
} from "./IdentityRecordMedia";
import { BotanicalIdentityCover } from "../photos/BotanicalIdentityCover";
import { InfoDisclosure } from "../components/ContextualHelp";
import type { BotanicalIdentityResponse } from "./api";
import type { BotanicalIdentityCollectionResponse } from "../collection/api";

export function IdentityMedia({
  identity,
  csrfToken,
  collection,
}: {
  identity: BotanicalIdentityResponse;
  csrfToken: string;
  collection: BotanicalIdentityCollectionResponse | null;
}) {
  const records = useMemo<IdentityMediaRecord[]>(
    () =>
      collection
        ? [
            ...collection.seed_lots.map((r) => ({
              id: r.id,
              label: r.label ?? "Unlabelled seed lot",
              kind: "Seed lot",
              target: "seed_lot" as const,
              href: `#/seeds/${r.id}?tab=photos`,
            })),
            ...collection.sowings.map((r) => ({
              id: r.id,
              label: r.label ?? "Unlabelled sowing",
              kind: "Sowing",
              target: "sowing" as const,
              href: `#/sowings/${r.id}?tab=photos`,
            })),
            ...collection.plants.map((r) => ({
              id: r.id,
              label: r.label ?? r.botanical_identity.display_label,
              kind: "Plant",
              target: "plant" as const,
              href: `#/plants/${r.id}?tab=photos`,
            })),
            ...collection.plant_groups.map((r) => ({
              id: r.id,
              label: r.label ?? r.botanical_identity.display_label,
              kind: "Plant group",
              target: "plant_group" as const,
              href: `#/plant-groups/${r.id}?tab=photos`,
            })),
            ...collection.harvests.map((r) => ({
              id: r.id,
              label: r.display_title,
              kind: "Harvest",
              target: "harvest" as const,
              href: `#/harvests/${r.id}`,
            })),
          ]
        : [],
    [collection],
  );
  return (
    <div className="identity-media-page">
      <h3 className="sr-only">Identity media</h3>
      <div className="identity-media-gallery">
        <BotanicalIdentityCover
          featured
          showAssetMetadata
          identityId={identity.id}
          identityLabel={identity.display_label}
          csrfToken={csrfToken}
        />
      </div>
      <section aria-labelledby="identity-record-photos">
        <div className="identity-media-heading">
          <h3 id="identity-record-photos">Collection record photos</h3>
          <InfoDisclosure label="About collection record photos">
            <p>
              Photos stay with their own seed lots, sowings, plants, groups and
              harvests. The cover above is the only identity-level image.
            </p>
          </InfoDisclosure>
        </div>
        {collection &&
          (records.length ? (
            <IdentityRecordMedia records={records} />
          ) : (
            <p className="identity-media-empty">
              No collection records use this identity yet.
            </p>
          ))}
      </section>
    </div>
  );
}
