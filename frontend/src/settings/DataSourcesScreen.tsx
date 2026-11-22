import { PageHeader } from "../components/ReferenceUI";
import { Page } from "../components/WorkspaceUI";
import "./settings.css";

const sources = [
  {
    name: "World Flora Online (WFO)",
    use: "Taxonomy: accepted names and classification",
    access:
      "Local reviewed snapshot installed by the operator; never fetched at run time",
    licence: "CC0",
    where: "#/taxonomy",
  },
  {
    name: "Kew WCVP",
    use: "Reviewable native-range proposals",
    access: "Local sealed index installed by the operator",
    licence: "CC BY",
    where: "#/native-ranges",
  },
  {
    name: "GBIF",
    use: "Occurrence evidence for one identity at a time",
    access: "Online request only when you press Load on a confirmed link",
    licence: "Per dataset",
    where: "#/species-distribution",
  },
  {
    name: "Natural Earth",
    use: "Map boundaries for overview maps",
    access: "Bundled with Florabase, works offline",
    licence: "Public domain",
    where: "#/map",
  },
  {
    name: "OpenStreetMap tiles",
    use: "Optional street-level basemap",
    access: "Off unless the operator enables it in runtime-config.js",
    licence: "ODbL, provider policy applies",
    where: "#/map",
  },
  {
    name: "Your own data (CSV)",
    use: "Bulk import and export of collection records",
    access: "Guided import with preview; nothing is written before you confirm",
    licence: "Yours",
    where: "#/import-export",
  },
] as const;

/** Settings → Data sources: what external data Florabase uses and the rules for adding more. */
export function DataSourcesScreen() {
  return (
    <Page className="settings-workspace" titleId="data-sources-heading">
      <PageHeader
        title="Data sources"
        titleId="data-sources-heading"
        eyebrow="Settings"
        description="External references Florabase uses, how they are reached, and how new sources will be added."
      />
      <div className="settings-content">
        <section className="settings-panel" aria-labelledby="sources-current">
          <h3 id="sources-current">Sources in use</h3>
          <div className="data-sources-table">
            <table>
              <thead>
                <tr>
                  <th scope="col">Source</th>
                  <th scope="col">Used for</th>
                  <th scope="col">How it is reached</th>
                  <th scope="col">Licence</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((source) => (
                  <tr key={source.name}>
                    <th scope="row">
                      <a href={source.where}>{source.name}</a>
                    </th>
                    <td>{source.use}</td>
                    <td>{source.access}</td>
                    <td>{source.licence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="settings-panel" aria-labelledby="sources-standard">
          <h3 id="sources-standard">Integration standard (planned)</h3>
          <p>
            New references and bulk input from private datasets will follow the
            same rules as the sources above. Managing integrations from this
            page is a future increment.
          </p>
          <ul>
            <li>
              Local first: a reviewed snapshot with version, retrieval date and
              checksum, so Florabase keeps working offline.
            </li>
            <li>
              Provenance on every value: which source, which release, and when
              it was confirmed.
            </li>
            <li>
              Explicit confirmation: a source proposes, you confirm; nothing
              overwrites your own records silently.
            </li>
            <li>
              Reversible bulk input: preview, validate and report before
              writing, as the CSV import already does.
            </li>
          </ul>
        </section>
      </div>
    </Page>
  );
}
