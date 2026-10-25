import { useMemo } from "react";
import {
  IdentityRecordMedia,
  type IdentityMediaRecord,
} from "./IdentityRecordMedia";
import { BotanicalIdentityCover } from "../photos/BotanicalIdentityCover";
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
      <header>
        <h3>Identity media</h3>
        <p>
          The featured image represents this identity. Collection images below
          stay with their own records.
        </p>
      </header>
      <div className="identity-media-gallery">
        <BotanicalIdentityCover
          featured
          showAssetMetadata
          identityId={identity.id}
          identityLabel={identity.display_label}
          csrfToken={csrfToken}
        />
      </div>
      <section aria-label="Collection record media">
        <h3>Images on collection records</h3>
        <p>
          Actual images attached to linked packets, Sowings, Plants, Plant
          groups and Harvests. These remain collection-record media, not
          identity covers.
        </p>
        {collection && <IdentityRecordMedia records={records} />}
        <details className="identity-media-owner-links">
          <summary>Open linked record photo sections</summary>
          {records.length ? (
            <ul className="identity-media-records">
              {records.slice(0, 12).map((r) => (
                <li key={`${r.kind}:${r.id}`}>
                  <a href={r.href}>{r.label}</a>
                  <small>{r.kind}</small>
                </li>
              ))}
            </ul>
          ) : (
            collection && <p>No linked collection records.</p>
          )}
          {records.length > 12 && (
            <p>
              Showing 12 record links. Use the collection footprint on Overview
              for complete filtered directories.
            </p>
          )}
        </details>
        <p className="field-help">
          The current identity-level media contract supports one cover, not
          arbitrary direct attachments.
        </p>
      </section>
    </div>
  );
}
