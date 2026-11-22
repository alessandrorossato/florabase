import { PageHeader } from "../components/ReferenceUI";
import { Page } from "../components/WorkspaceUI";
import { workspaces } from "../shell/navigation";
import "./settings.css";

/** Settings → Help: what each workspace and page is for, built from the navigation itself. */
export function HelpScreen() {
  return (
    <Page className="settings-workspace" titleId="help-heading">
      <PageHeader
        title="Help"
        titleId="help-heading"
        eyebrow="Settings"
        description="What each part of Florabase is for and how the pages relate."
      />
      <div className="settings-content help-content">
        <section className="settings-panel" aria-labelledby="help-concepts">
          <h3 id="help-concepts">Key ideas</h3>
          <dl className="help-concepts">
            <dt>Botanical identity</dt>
            <dd>
              The name a plant is known by in your collection. It holds
              reference knowledge (taxonomy, native range, profile) but no
              physical material.
            </dd>
            <dt>Collection records</dt>
            <dd>
              Seed lots, Sowings, Plants and groups, Cuttings and Harvests: the
              physical material you hold, each linked to one identity.
            </dd>
            <dt>Lineage</dt>
            <dd>
              Only relationships you record (sown as, grown into, taken from)
              are drawn. Sharing an identity never implies shared ancestry.
            </dd>
            <dt>Journal, History and Schedule</dt>
            <dd>
              The Journal is what you observed and did, History is every
              recorded change, and the Schedule is work planned for the future.
            </dd>
            <dt>Collection and Explore</dt>
            <dd>
              Collection pages show one record and its own tabs. Explore gives
              the cross-collection view to compare species, taxonomy, lineage
              and geography, and links back to each record.
            </dd>
          </dl>
        </section>
        {workspaces.map((workspace) => (
          <section
            key={workspace.id}
            className="settings-panel"
            aria-labelledby={`help-${workspace.id}`}
          >
            <h3 id={`help-${workspace.id}`}>{workspace.label}</h3>
            <p>{workspace.summary}</p>
            <ul className="help-links">
              {workspace.destinations.map((item) => (
                <li key={item.section}>
                  <a href={`#/${item.section}`}>{item.label}</a>
                  {item.children?.map((child) => (
                    <span key={child.href}>
                      {" · "}
                      <a href={child.href}>{child.label}</a>
                    </span>
                  ))}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </Page>
  );
}
