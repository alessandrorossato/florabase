import { identityDirectory } from "./identityNavigation";
import { IdentityTaskLink } from "./IdentityTaskLink";
import type { BotanicalIdentityCollectionResponse } from "../collection/api";
import { IdentitySourceAction } from "./IdentitySourceAction";

export function IdentityCollectionHub({
  value,
}: {
  value: BotanicalIdentityCollectionResponse;
}) {
  const id = value.identity.id;
  const sections = [
    {
      key: "seeds" as const,
      name: "Seed lots",
      records: value.seed_lots.map((r) => ({
        id: r.id,
        label: r.label ?? "Unlabelled seed lot",
        detail: r.lifecycle,
        href: `#/seeds/${r.id}`,
      })),
      action: (
        <IdentityTaskLink
          className="button-link button--secondary"
          href={`#/seeds?action=create&identity=${id}`}
        >
          Add seed lot
        </IdentityTaskLink>
      ),
    },
    {
      key: "sowings" as const,
      name: "Sowings",
      records: value.sowings.map((r) => ({
        id: r.id,
        label: r.label ?? "Unlabelled sowing",
        detail: (
          <>
            {r.lifecycle} · Source:{" "}
            <a href={`#/seeds/${r.seed_lot.id}`}>
              {r.seed_lot.label ?? "Unlabelled seed lot"}
            </a>
            {r.lifecycle === "active" && (
              <span className="actions">
                <IdentityTaskLink
                  href={`#/plants?action=from-sowing&sowing=${r.id}&kind=plant`}
                >
                  Create plant from this sowing
                </IdentityTaskLink>
                <IdentityTaskLink
                  href={`#/plants?action=from-sowing&sowing=${r.id}&kind=group`}
                >
                  Create plant group from this sowing
                </IdentityTaskLink>
              </span>
            )}
          </>
        ),
        href: `#/sowings/${r.id}`,
      })),
      action: <IdentitySourceAction identityId={id} kind="sowing" />,
    },
    {
      key: "plants" as const,
      name: "Plants",
      records: value.plants.map((r) => ({
        id: r.id,
        label: r.label ?? r.botanical_identity.display_label,
        detail: r.lifecycle,
        href: `#/plants/${r.id}`,
      })),
      action: (
        <IdentityTaskLink
          className="button-link button--secondary"
          href={`#/plants?action=create&identity=${id}&kind=plant`}
        >
          Add plant
        </IdentityTaskLink>
      ),
    },
    {
      key: "groups" as const,
      name: "Plant groups",
      records: value.plant_groups.map((r) => ({
        id: r.id,
        label: r.label ?? r.botanical_identity.display_label,
        detail: r.lifecycle,
        href: `#/plant-groups/${r.id}`,
      })),
      action: (
        <IdentityTaskLink
          className="button-link button--secondary"
          href={`#/plants?action=create&identity=${id}&kind=group`}
        >
          Add plant group
        </IdentityTaskLink>
      ),
    },
    {
      key: "harvests" as const,
      name: "Harvests",
      records: value.harvests.map((r) => ({
        id: r.id,
        label: r.display_title,
        detail: `${String(r.items.length)} material lines`,
        href: `#/harvests/${r.id}`,
      })),
      action: <IdentitySourceAction identityId={id} kind="harvest" />,
    },
  ];
  return (
    <div className="identity-hub-grid">
      {sections.map((section) => (
        <section
          id={`identity-${section.key}`}
          tabIndex={-1}
          key={section.key}
          className="identity-hub-section"
          aria-label={section.name}
        >
          <header>
            <h3>
              {section.name}{" "}
              <span className="identity-section-count">
                {section.records.length} recorded
              </span>
            </h3>
            {section.action}
          </header>
          {section.records.length ? (
            <ul className="identity-related-list">
              {section.records.slice(0, 4).map((record) => (
                <li key={record.id}>
                  <a href={record.href}>{record.label}</a>
                  <small>{record.detail}</small>
                </li>
              ))}
            </ul>
          ) : (
            <p>No {section.name.toLowerCase()} recorded.</p>
          )}
          <a href={identityDirectory(section.key, id)}>
            View all {section.name} for this identity
          </a>
        </section>
      ))}
    </div>
  );
}
