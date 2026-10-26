import { useState } from "react";
import { ActionButton } from "../components/Action";
import { BotanicalName } from "../components/ReferenceUI";
import { TaxonomyCover } from "./TaxonomyCover";
import type { Identity } from "./api";
import {
  representation,
  taxonomyIdentityHash,
  type TaxonomyState,
} from "./state";

export function IdentityList({
  identities,
  state,
}: {
  identities: Identity[];
  state: TaxonomyState;
}) {
  const [limit, setLimit] = useState(24);
  const visible = identities.slice(0, limit);
  return (
    <>
      <ul className="taxonomy-identities">
        {visible.map((identity) => (
          <li key={identity.id}>
            <TaxonomyCover identity={identity} />
            <a href={taxonomyIdentityHash(identity.id, state)}>
              <BotanicalName
                label={identity.display_label}
                scientificName={identity.scientific_name}
              />
            </a>
            <span className="taxonomy-meta">
              {identity.common_name ? `${identity.common_name} · ` : ""}
              {representation[identity.representation]}
            </span>
            {identity.synonym_of && (
              <p className="taxonomy-synonym">
                WFO treats the linked source name as a synonym of{" "}
                <i>{identity.synonym_of}</i>. The local name is unchanged.
              </p>
            )}
            {identity.unresolved_reason && <p>{identity.unresolved_reason}</p>}
            {identity.cover && (
              <p className="taxonomy-cover-credit">
                {identity.cover.attribution ?? "Attribution not recorded"} ·{" "}
                <a href={`#/media/${identity.cover.asset_id}`}>Cover media</a>
                {identity.cover.source_url && (
                  <a
                    href={identity.cover.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Source
                  </a>
                )}
                {identity.cover.licence_label &&
                  (identity.cover.licence_url ? (
                    <a
                      href={identity.cover.licence_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {identity.cover.licence_label}
                    </a>
                  ) : (
                    identity.cover.licence_label
                  ))}
              </p>
            )}
          </li>
        ))}
      </ul>
      {visible.length < identities.length && (
        <ActionButton
          variant="secondary"
          onClick={() => {
            setLimit((n) => n + 24);
          }}
        >
          Show more identities ({visible.length} of {identities.length})
        </ActionButton>
      )}
    </>
  );
}
